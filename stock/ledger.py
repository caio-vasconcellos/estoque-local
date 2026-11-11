"""Inventory rules and persistence.

Money is stored as integer cents. Every stock change and its history entry are
written in the same SQLite transaction.
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    supplier TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
    minimum INTEGER NOT NULL CHECK(minimum >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    quantity INTEGER NOT NULL DEFAULT 0
        CHECK(typeof(quantity) = 'integer' AND quantity >= 0),
    value_cents INTEGER NOT NULL DEFAULT 0
        CHECK(typeof(value_cents) = 'integer' AND value_cents >= 0),
    CHECK(quantity > 0 OR value_cents = 0)
);

CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    kind TEXT NOT NULL
        CHECK(kind IN ('purchase', 'sale', 'return', 'loss', 'gain')),
    quantity INTEGER NOT NULL
        CHECK(typeof(quantity) = 'integer' AND quantity > 0),
    stock_delta INTEGER NOT NULL,
    cost_delta INTEGER NOT NULL,
    revenue_delta INTEGER NOT NULL DEFAULT 0,
    spend_cents INTEGER NOT NULL DEFAULT 0,
    unit_cents INTEGER NOT NULL,
    note TEXT NOT NULL,
    original_id INTEGER REFERENCES movements(id),
    occurred_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    request_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS movements_product
    ON movements(product_id, id);
CREATE INDEX IF NOT EXISTS movements_date
    ON movements(occurred_on);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

MOVEMENTS_WITH_PRODUCTS_SQL = """
SELECT
    movement.*,
    product.name,
    product.sku,
    CASE
        WHEN movement.kind = 'sale' THEN
            movement.quantity - COALESCE((
                SELECT SUM(returned.quantity)
                FROM movements AS returned
                WHERE returned.original_id = movement.id
            ), 0)
    END AS returnable
FROM movements AS movement
JOIN products AS product ON product.id = movement.product_id
ORDER BY movement.id DESC
"""

INSERT_MOVEMENT_SQL = """
INSERT INTO movements (
    product_id,
    kind,
    quantity,
    stock_delta,
    cost_delta,
    revenue_delta,
    spend_cents,
    unit_cents,
    note,
    original_id,
    occurred_on,
    created_at,
    request_key,
    payload_hash
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class Invalid(ValueError):
    """A business validation error safe to return through the local API."""


def parse_integer(value, *, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise Invalid("invalid_quantity")
    return value


def parse_money(value):
    """Convert a decimal string from the API to integer cents."""

    if not isinstance(value, str):
        raise Invalid("money")

    try:
        amount = Decimal(value)
        if not amount.is_finite() or not 0 <= amount <= 10_000_000:
            raise Invalid("money")
        if amount != amount.quantize(Decimal("0.01")):
            raise Invalid("money")
        return int(amount * 100)
    except (InvalidOperation, ValueError):
        raise Invalid("money") from None


# Kept as a small public alias because earlier code imported this name.
money = parse_money


def allocate_cents(total_cents, selected_units, total_units):
    """Allocate an integer amount proportionally, rounded to the nearest cent."""

    amount = Decimal(total_cents) * selected_units / total_units
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def clean_text(value, maximum, required=False):
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise Invalid("text")

    cleaned = value.strip()
    if required and not cleaned:
        raise Invalid("required")
    return cleaned


def cents_as_decimal(cents):
    return f"{cents // 100}.{cents % 100:02d}"


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.connection(write=True) as database:
            database.executescript(SCHEMA_SQL)

    @contextmanager
    def connection(self, write=False):
        database = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA foreign_keys = ON")
        begin_statement = "BEGIN IMMEDIATE" if write else "BEGIN"

        try:
            # IMMEDIATE lets only one writer validate and change stock at a time.
            database.execute(begin_statement)
            yield database
            if database.in_transaction:
                database.commit()
        except BaseException:
            if database.in_transaction:
                database.rollback()
            raise
        finally:
            database.close()

    def save_product(self, payload, product_id=None):
        values = (
            clean_text(payload.get("sku"), 40, required=True),
            clean_text(payload.get("name"), 120, required=True),
            clean_text(payload.get("category", ""), 60),
            clean_text(payload.get("supplier", ""), 120),
            parse_money(payload.get("price")),
            parse_integer(payload.get("minimum")),
        )
        active = payload.get("active", True)
        if type(active) is not bool:
            raise Invalid("text")

        try:
            with self.connection(write=True) as database:
                if product_id is None:
                    cursor = database.execute(
                        """
                        INSERT INTO products (
                            sku,
                            name,
                            category,
                            supplier,
                            price_cents,
                            minimum
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    return cursor.lastrowid

                product = database.execute(
                    "SELECT * FROM products WHERE id = ?",
                    (product_id,),
                ).fetchone()
                if not product:
                    raise Invalid("missing")
                if not active and product["quantity"]:
                    raise Invalid("archive_stock")

                database.execute(
                    """
                    UPDATE products
                    SET
                        sku = ?,
                        name = ?,
                        category = ?,
                        supplier = ?,
                        price_cents = ?,
                        minimum = ?,
                        active = ?
                    WHERE id = ?
                    """,
                    (*values, int(active), product_id),
                )
                return product_id
        except sqlite3.IntegrityError as error:
            if "products.sku" in str(error):
                raise Invalid("duplicate_sku") from None
            raise

    def move(self, payload):
        with self.connection(write=True) as database:
            return self._move(database, payload, date.today().isoformat())

    def _move(self, database, payload, occurred_on):
        request_key = clean_text(payload.get("request_key"), 80, required=True)
        payload_hash = self._payload_hash(payload)

        repeated = database.execute(
            """
            SELECT id, payload_hash
            FROM movements
            WHERE request_key = ?
            """,
            (request_key,),
        ).fetchone()
        if repeated:
            if repeated["payload_hash"] != payload_hash:
                raise Invalid("request_conflict")
            return repeated["id"]

        kind = payload.get("kind")
        if kind not in {"purchase", "sale", "return", "loss", "gain"}:
            raise Invalid("kind")

        quantity = parse_integer(payload.get("quantity"), minimum=1)
        product_id = parse_integer(payload.get("product_id"), minimum=1)
        note = clean_text(
            payload.get("note", ""),
            300,
            required=kind in {"loss", "gain"},
        )
        product = database.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if not product or not product["active"]:
            raise Invalid("missing")

        effect = self._movement_effect(
            database,
            payload,
            product,
            kind,
            quantity,
        )

        database.execute(
            """
            UPDATE products
            SET
                quantity = quantity + ?,
                value_cents = value_cents + ?
            WHERE id = ?
            """,
            (
                effect["stock_delta"],
                effect["cost_delta"],
                product_id,
            ),
        )

        cursor = database.execute(
            INSERT_MOVEMENT_SQL,
            (
                product_id,
                kind,
                quantity,
                effect["stock_delta"],
                effect["cost_delta"],
                effect["revenue_delta"],
                effect["spend_cents"],
                effect["unit_cents"],
                note,
                effect["original_id"],
                occurred_on,
                datetime.now(timezone.utc).isoformat(),
                request_key,
                payload_hash,
            ),
        )
        return cursor.lastrowid

    @staticmethod
    def _payload_hash(payload):
        canonical_payload = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
        return hashlib.sha256(canonical_payload).hexdigest()

    def _movement_effect(self, database, payload, product, kind, quantity):
        if kind in {"purchase", "gain"}:
            unit_cents = parse_money(payload.get("unit_price"))
            cost_delta = unit_cents * quantity
            return {
                "stock_delta": quantity,
                "cost_delta": cost_delta,
                "revenue_delta": 0,
                "spend_cents": cost_delta if kind == "purchase" else 0,
                "unit_cents": unit_cents,
                "original_id": None,
            }

        if kind in {"sale", "loss"}:
            if quantity > product["quantity"]:
                raise Invalid("insufficient")

            cost_delta = -allocate_cents(
                product["value_cents"],
                quantity,
                product["quantity"],
            )
            unit_cents = (
                parse_money(payload.get("unit_price"))
                if kind == "sale"
                else 0
            )
            return {
                "stock_delta": -quantity,
                "cost_delta": cost_delta,
                "revenue_delta": unit_cents * quantity,
                "spend_cents": 0,
                "unit_cents": unit_cents,
                "original_id": None,
            }

        return self._return_effect(database, payload, product, quantity)

    def _return_effect(self, database, payload, product, quantity):
        original_id = parse_integer(
            payload.get("original_id"),
            minimum=1,
            maximum=2**53 - 1,
        )
        sale = database.execute(
            """
            SELECT *
            FROM movements
            WHERE
                id = ?
                AND kind = 'sale'
                AND product_id = ?
            """,
            (original_id, product["id"]),
        ).fetchone()
        if not sale:
            raise Invalid("sale_missing")

        already_returned = database.execute(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM movements
            WHERE original_id = ?
            """,
            (original_id,),
        ).fetchone()[0]
        if quantity + already_returned > sale["quantity"]:
            raise Invalid("return_exceeded")

        original_cost = -sale["cost_delta"]
        returned_before = allocate_cents(
            original_cost,
            already_returned,
            sale["quantity"],
        )
        returned_after = allocate_cents(
            original_cost,
            already_returned + quantity,
            sale["quantity"],
        )
        # The cumulative difference makes partial returns restore every cent.
        restored_cost = returned_after - returned_before

        return {
            "stock_delta": quantity,
            "cost_delta": restored_cost,
            "revenue_delta": -sale["unit_cents"] * quantity,
            "spend_cents": 0,
            "unit_cents": sale["unit_cents"],
            "original_id": original_id,
        }

    def snapshot(self, start, end):
        start, end = self._validated_period(start, end)

        with self.connection() as database:
            products = [
                dict(row)
                for row in database.execute(
                    "SELECT * FROM products ORDER BY name COLLATE NOCASE"
                )
            ]
            # One read transaction keeps balances, movements and reports aligned.
            movements = [
                dict(row)
                for row in database.execute(MOVEMENTS_WITH_PRODUCTS_SQL)
            ]
            demo = (
                database.execute(
                    "SELECT value FROM settings WHERE key = 'demo'"
                ).fetchone()
                is not None
            )

        totals = {
            "revenue": 0,
            "cogs": 0,
            "profit": 0,
            "purchases": 0,
            "sold": 0,
            "losses": 0,
            "returns": 0,
        }
        product_reports = {
            product["id"]: {
                **product,
                "sold": 0,
                "revenue": 0,
                "cogs": 0,
                "profit": 0,
                "purchases": 0,
                "last_sale": None,
            }
            for product in products
        }
        daily = {}

        for movement in movements:
            product = product_reports[movement["product_id"]]
            if movement["kind"] == "sale" and product["last_sale"] is None:
                product["last_sale"] = movement["occurred_on"]

            if not start <= movement["occurred_on"] <= end:
                continue

            if movement["kind"] in {"sale", "return"}:
                units_sold = -movement["stock_delta"]
                cost_of_sale = -movement["cost_delta"]
                gross_profit = movement["revenue_delta"] - cost_of_sale

                for summary in (totals, product):
                    summary["sold"] += units_sold
                    summary["revenue"] += movement["revenue_delta"]
                    summary["cogs"] += cost_of_sale
                    summary["profit"] += gross_profit

                day = daily.setdefault(
                    movement["occurred_on"],
                    {"revenue": 0, "profit": 0},
                )
                day["revenue"] += movement["revenue_delta"]
                day["profit"] += gross_profit

                if movement["kind"] == "return":
                    totals["returns"] += movement["quantity"]

            totals["purchases"] += movement["spend_cents"]
            product["purchases"] += movement["spend_cents"]
            if movement["kind"] == "loss":
                totals["losses"] -= movement["cost_delta"]

        rows = list(product_reports.values())
        for product in rows:
            product["average_cents"] = (
                allocate_cents(
                    product["value_cents"],
                    1,
                    product["quantity"],
                )
                if product["quantity"]
                else None
            )
            product["margin"] = (
                round(product["profit"] / product["revenue"] * 100, 2)
                if product["revenue"] > 0
                else None
            )

        totals.update(
            stock_value=sum(product["value_cents"] for product in rows),
            stock_units=sum(product["quantity"] for product in rows),
            low_stock=sum(
                product["active"] and product["quantity"] <= product["minimum"]
                for product in rows
            ),
            margin=(
                round(totals["profit"] / totals["revenue"] * 100, 2)
                if totals["revenue"] > 0
                else None
            ),
        )

        return {
            "products": rows,
            "movements": [
                movement
                for movement in movements
                if start <= movement["occurred_on"] <= end
            ],
            "returnable": [
                movement
                for movement in movements
                if movement["kind"] == "sale" and movement["returnable"] > 0
            ],
            "totals": totals,
            "daily": [
                {"day": day, **daily[day]}
                for day in sorted(daily)
            ],
            "demo": demo,
            "start": start,
            "end": end,
        }

    @staticmethod
    def _validated_period(start, end):
        try:
            first = date.fromisoformat(start)
            last = date.fromisoformat(end)
            if first > last:
                raise ValueError
        except (TypeError, ValueError):
            raise Invalid("dates") from None
        return first.isoformat(), last.isoformat()

    def seed_demo(self):
        # One transaction prevents a partial demo catalogue.
        with self.connection(write=True) as database:
            product_count = database.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0]
            if product_count:
                raise Invalid("demo_not_empty")

            catalogue = [
                ("CAF-01", "Café torrado · 500 g", "Mercearia", 2490, 12, 1400, 140, 96),
                ("MEL-01", "Mel silvestre · 300 g", "Mercearia", 2890, 8, 1100, 70, 42),
                ("AZE-01", "Azeite extravirgem · 500 ml", "Mercearia", 4590, 10, 4100, 60, 51),
                ("CHA-01", "Chá de camomila · 20 un", "Mercearia", 1290, 8, 620, 90, 72),
                ("CAN-01", "Caneca de cerâmica", "Casa", 3900, 5, 1900, 30, 4),
                ("GAR-01", "Garrafa térmica · 750 ml", "Casa", 8900, 3, 5700, 20, 0),
            ]
            today = date.today()

            for index, item in enumerate(catalogue):
                (
                    sku,
                    name,
                    category,
                    price_cents,
                    minimum,
                    cost_cents,
                    quantity,
                    sold,
                ) = item
                cursor = database.execute(
                    """
                    INSERT INTO products (
                        sku,
                        name,
                        category,
                        supplier,
                        price_cents,
                        minimum
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sku,
                        name,
                        category,
                        "Fornecedor exemplo",
                        price_cents,
                        minimum,
                    ),
                )
                product_id = cursor.lastrowid

                self._move(
                    database,
                    {
                        "request_key": f"demo-buy-{index}",
                        "product_id": product_id,
                        "kind": "purchase",
                        "quantity": quantity,
                        "unit_price": cents_as_decimal(cost_cents),
                        "note": "Demonstração / Demo",
                    },
                    (today - timedelta(days=25)).isoformat(),
                )

                if sold:
                    batches = (
                        sold // 3,
                        sold // 3,
                        sold - 2 * (sold // 3),
                    )
                    for batch_index, batch_quantity in enumerate(batches):
                        self._move(
                            database,
                            {
                                "request_key": (
                                    f"demo-sale-{index}-{batch_index}"
                                ),
                                "product_id": product_id,
                                "kind": "sale",
                                "quantity": batch_quantity,
                                "unit_price": cents_as_decimal(price_cents),
                                "note": "Demonstração / Demo",
                            },
                            (
                                today
                                - timedelta(days=18 - batch_index * 8)
                            ).isoformat(),
                        )

            database.execute(
                "INSERT INTO settings VALUES ('demo', '1')"
            )
