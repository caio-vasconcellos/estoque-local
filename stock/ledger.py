"""Inventory accounting. Money is stored in cents, never binary floats."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import sqlite3


class Invalid(ValueError):
    pass


def integer(value, *, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise Invalid("invalid_quantity")
    return value


def money(value):
    # The HTTP contract uses decimal strings (dot separator).
    if not isinstance(value, str):
        raise Invalid("money")
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0 or amount > 10_000_000:
            raise Invalid("money")
        if amount != amount.quantize(Decimal(".01")):
            raise Invalid("money")
        return int(amount * 100)
    except (InvalidOperation, ValueError):
        raise Invalid("money") from None


def share(total, part, whole):
    return int((Decimal(total) * part / whole).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def clean(value, maximum, required=False):
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise Invalid("text")
    value = value.strip()
    if required and not value:
        raise Invalid("required")
    return value


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection(write=True) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    supplier TEXT NOT NULL DEFAULT '',
                    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                    minimum INTEGER NOT NULL CHECK(minimum >= 0),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK(typeof(quantity)='integer' AND quantity >= 0),
                    value_cents INTEGER NOT NULL DEFAULT 0 CHECK(typeof(value_cents)='integer' AND value_cents >= 0),
                    CHECK(quantity > 0 OR value_cents=0)
                );
                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    kind TEXT NOT NULL CHECK(kind IN ('purchase','sale','return','loss','gain')),
                    quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity > 0),
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
                CREATE INDEX IF NOT EXISTS movements_product ON movements(product_id, id);
                CREATE INDEX IF NOT EXISTS movements_date ON movements(occurred_on);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            if db.in_transaction:
                db.commit()
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    def save_product(self, payload, product_id=None):
        values = (
            clean(payload.get("sku"), 40, True), clean(payload.get("name"), 120, True),
            clean(payload.get("category", ""), 60), clean(payload.get("supplier", ""), 120),
            money(payload.get("price")), integer(payload.get("minimum")),
        )
        active = payload.get("active", True)
        if type(active) is not bool:
            raise Invalid("text")
        try:
            with self.connection(write=True) as db:
                if product_id is None:
                    return db.execute("INSERT INTO products(sku,name,category,supplier,price_cents,minimum) VALUES(?,?,?,?,?,?)", values).lastrowid
                product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
                if not product:
                    raise Invalid("missing")
                if not active and product["quantity"]:
                    raise Invalid("archive_stock")
                db.execute("UPDATE products SET sku=?,name=?,category=?,supplier=?,price_cents=?,minimum=?,active=? WHERE id=?", (*values, int(active), product_id))
                return product_id
        except sqlite3.IntegrityError as exc:
            if "products.sku" in str(exc):
                raise Invalid("duplicate_sku") from None
            raise

    def move(self, payload):
        with self.connection(write=True) as db:
            return self._move(db, payload, date.today().isoformat())

    def _move(self, db, payload, occurred_on):
        key = clean(payload.get("request_key"), 80, True)
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        previous = db.execute("SELECT id,payload_hash FROM movements WHERE request_key=?", (key,)).fetchone()
        if previous:
            if previous["payload_hash"] != fingerprint:
                raise Invalid("request_conflict")
            return previous["id"]
        kind = payload.get("kind")
        if kind not in {"purchase", "sale", "return", "loss", "gain"}:
            raise Invalid("kind")
        qty = integer(payload.get("quantity"), minimum=1)
        product_id = integer(payload.get("product_id"), minimum=1)
        note = clean(payload.get("note", ""), 300, kind in {"loss", "gain"})
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not product or not product["active"]:
            raise Invalid("missing")
        revenue = spend = unit = 0
        original_id = None
        if kind in {"purchase", "gain"}:
            unit = money(payload.get("unit_price"))
            cost = unit * qty
            delta = qty
            spend = cost if kind == "purchase" else 0
        elif kind in {"sale", "loss"}:
            if qty > product["quantity"]:
                raise Invalid("insufficient")
            cost = -share(product["value_cents"], qty, product["quantity"])
            delta = -qty
            if kind == "sale":
                unit = money(payload.get("unit_price"))
                revenue = unit * qty
        else:
            original_id = integer(payload.get("original_id"), minimum=1, maximum=2**53-1)
            sale = db.execute("SELECT * FROM movements WHERE id=? AND kind='sale' AND product_id=?", (original_id, product_id)).fetchone()
            if not sale:
                raise Invalid("sale_missing")
            returned = db.execute("SELECT COALESCE(SUM(quantity),0) FROM movements WHERE original_id=?", (original_id,)).fetchone()[0]
            if qty + returned > sale["quantity"]:
                raise Invalid("return_exceeded")
            # Cumulative allocation means partial returns restore exactly the original cost.
            cost = share(-sale["cost_delta"], returned + qty, sale["quantity"]) - share(-sale["cost_delta"], returned, sale["quantity"])
            unit = sale["unit_cents"]
            revenue = -unit * qty
            delta = qty
        db.execute("UPDATE products SET quantity=quantity+?,value_cents=value_cents+? WHERE id=?", (delta, cost, product_id))
        return db.execute("""INSERT INTO movements(product_id,kind,quantity,stock_delta,cost_delta,revenue_delta,spend_cents,unit_cents,note,original_id,occurred_on,created_at,request_key,payload_hash)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (product_id, kind, qty, delta, cost, revenue, spend, unit, note, original_id, occurred_on, datetime.now(timezone.utc).isoformat(), key, fingerprint)).lastrowid

    def snapshot(self, start, end):
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if first > last:
                raise ValueError()
        except (TypeError, ValueError):
            raise Invalid("dates") from None
        start, end = first.isoformat(), last.isoformat()
        with self.connection() as db:
            products = [dict(r) for r in db.execute("SELECT * FROM products ORDER BY name COLLATE NOCASE")]
            # This read transaction gives balance, history and reports a single consistent snapshot.
            movements = [dict(r) for r in db.execute("""SELECT m.*,p.name,p.sku,
                CASE WHEN m.kind='sale' THEN m.quantity-COALESCE((SELECT SUM(r.quantity) FROM movements r WHERE r.original_id=m.id),0) END AS returnable
                FROM movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC""")]
            demo = db.execute("SELECT value FROM settings WHERE key='demo'").fetchone() is not None
        totals = dict(revenue=0, cogs=0, profit=0, purchases=0, sold=0, losses=0, returns=0)
        by_product = {p["id"]: dict(p, sold=0, revenue=0, cogs=0, profit=0, purchases=0, last_sale=None) for p in products}
        daily = {}
        for m in movements:
            p = by_product[m["product_id"]]
            if m["kind"] == "sale" and p["last_sale"] is None:
                p["last_sale"] = m["occurred_on"]
            if not start <= m["occurred_on"] <= end:
                continue
            if m["kind"] in {"sale", "return"}:
                units = -m["stock_delta"]
                cogs = -m["cost_delta"]
                profit = m["revenue_delta"] - cogs
                for entry in (totals, p):
                    entry["sold"] += units
                    entry["revenue"] += m["revenue_delta"]
                    entry["cogs"] += cogs
                    entry["profit"] += profit
                day = daily.setdefault(m["occurred_on"], dict(revenue=0, profit=0))
                day["revenue"] += m["revenue_delta"]
                day["profit"] += profit
                if m["kind"] == "return":
                    totals["returns"] += m["quantity"]
            totals["purchases"] += m["spend_cents"]
            p["purchases"] += m["spend_cents"]
            if m["kind"] == "loss":
                totals["losses"] -= m["cost_delta"]
        rows = list(by_product.values())
        for p in rows:
            p["average_cents"] = share(p["value_cents"], 1, p["quantity"]) if p["quantity"] else None
            p["margin"] = round(p["profit"] / p["revenue"] * 100, 2) if p["revenue"] > 0 else None
        totals.update(stock_value=sum(p["value_cents"] for p in rows),
                      stock_units=sum(p["quantity"] for p in rows),
                      low_stock=sum(p["active"] and p["quantity"] <= p["minimum"] for p in rows),
                      margin=round(totals["profit"] / totals["revenue"] * 100, 2) if totals["revenue"] > 0 else None)
        return dict(products=rows, movements=[m for m in movements if start <= m["occurred_on"] <= end],
                    returnable=[m for m in movements if m["kind"] == "sale" and m["returnable"] > 0], totals=totals,
                    daily=[dict(day=k, **daily[k]) for k in sorted(daily)], demo=demo, start=start, end=end)

    def seed_demo(self):
        # Seeding is one transaction and cannot overwrite an existing catalogue.
        with self.connection(write=True) as db:
            if db.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
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
            for index, (sku, name, category, price, minimum, cost, qty, sold) in enumerate(catalogue):
                pid = db.execute("INSERT INTO products(sku,name,category,supplier,price_cents,minimum) VALUES(?,?,?,?,?,?)", (sku,name,category,"Fornecedor exemplo",price,minimum)).lastrowid
                self._move(db, dict(request_key=f"demo-buy-{index}", product_id=pid, kind="purchase", quantity=qty, unit_price=f"{cost / 100:.2f}", note="Demonstração / Demo"), (today-timedelta(days=25)).isoformat())
                if sold:
                    for batch, amount in enumerate((sold // 3, sold // 3, sold - 2*(sold // 3))):
                        self._move(db, dict(request_key=f"demo-sale-{index}-{batch}", product_id=pid, kind="sale", quantity=amount, unit_price=f"{price / 100:.2f}", note="Demonstração / Demo"), (today-timedelta(days=18-batch*8)).isoformat())
            db.execute("INSERT INTO settings VALUES('demo','1')")
