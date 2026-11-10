from concurrent.futures import ThreadPoolExecutor
from datetime import date
import sqlite3
import uuid

import pytest

from stock.ledger import Invalid, Ledger, money


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "inventory.sqlite3")


def product(ledger, name="Coffee", **overrides):
    return ledger.save_product(dict(sku=name, name=name, price="10.00", minimum=2, **overrides))


def move(ledger, pid, kind, qty, price="10.00", **extra):
    return ledger.move(dict(product_id=pid, kind=kind, quantity=qty, unit_price=price, request_key=uuid.uuid4().hex, **extra))


def snapshot(ledger):
    return ledger.snapshot("0001-01-01", "9999-12-31")


def test_weighted_cost_preserves_historical_sale_after_new_purchase(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 10, "10.00")
    move(ledger, pid, "purchase", 10, "20.00")
    sale_id = move(ledger, pid, "sale", 5, "25.00")
    move(ledger, pid, "purchase", 5, "30.00")
    s = snapshot(ledger)
    p = s["products"][0]
    sale = next(m for m in s["movements"] if m["id"] == sale_id)
    assert (p["quantity"], p["value_cents"], p["average_cents"]) == (20, 37500, 1875)
    assert (sale["cost_delta"], p["revenue"], p["profit"]) == (-7500, 12500, 5000)
    assert s["totals"]["purchases"] == 45000


def test_fractional_average_and_partial_returns_conserve_every_cent(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 2, "0.01")
    move(ledger, pid, "purchase", 1, "0.02")
    sale = move(ledger, pid, "sale", 3, "1.00")
    assert snapshot(ledger)["products"][0]["value_cents"] == 0
    for _ in range(3):
        move(ledger, pid, "return", 1, original_id=sale)
    s = snapshot(ledger)
    assert (s["products"][0]["quantity"], s["products"][0]["value_cents"]) == (3, 4)
    assert (s["totals"]["profit"], s["totals"]["revenue"], s["totals"]["sold"]) == (0, 0, 0)
    with pytest.raises(Invalid, match="return_exceeded"):
        move(ledger, pid, "return", 1, original_id=sale)


def test_popular_product_can_contribute_less_profit_than_slow_seller(ledger):
    fast, slow, idle = [product(ledger, name) for name in ("Fast", "Slow", "Idle")]
    move(ledger, fast, "purchase", 20, "9.00")
    move(ledger, fast, "sale", 10, "10.00")
    move(ledger, slow, "purchase", 10, "2.00")
    move(ledger, slow, "sale", 2, "10.00")
    products = {p["id"]: p for p in snapshot(ledger)["products"]}
    assert products[fast]["sold"] > products[slow]["sold"]
    assert products[fast]["profit"] < products[slow]["profit"]
    assert products[fast]["margin"] == 10
    assert products[slow]["margin"] == 80
    assert products[idle]["sold"] == 0 and products[idle]["margin"] is None


def test_overdraw_is_atomic_and_concurrent_withdrawals_cannot_oversell(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 3)
    def withdraw(_):
        try:
            move(ledger, pid, "sale", 2)
            return "ok"
        except Invalid:
            return "blocked"
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(withdraw, range(2))) == ["blocked", "ok"]
    s = snapshot(ledger)
    assert s["products"][0]["quantity"] == 1
    assert len(s["movements"]) == 2


def test_history_failure_rolls_back_stock_update(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 4)
    with ledger.connection(write=True) as db:
        db.execute("CREATE TRIGGER fail_history BEFORE INSERT ON movements BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="test failure"):
        move(ledger, pid, "sale", 1)
    assert snapshot(ledger)["products"][0]["quantity"] == 4
    assert len(snapshot(ledger)["movements"]) == 1


def test_retried_movement_is_idempotent_but_conflicting_payload_is_rejected(ledger):
    pid = product(ledger)
    payload = dict(product_id=pid, kind="purchase", quantity=2, unit_price="1.00", request_key="retry-key")
    first = ledger.move(payload)
    assert ledger.move(payload) == first
    with pytest.raises(Invalid, match="request_conflict"):
        ledger.move(dict(payload, quantity=3))
    assert snapshot(ledger)["products"][0]["quantity"] == 2


def test_return_uses_original_cost_not_current_average(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 4, "1.00")
    sale = move(ledger, pid, "sale", 2, "5.00")
    move(ledger, pid, "purchase", 2, "9.00")
    move(ledger, pid, "return", 1, original_id=sale)
    p = snapshot(ledger)["products"][0]
    assert (p["quantity"], p["value_cents"], p["profit"]) == (5, 2100, 400)


def test_period_returns_and_current_stock_are_distinct(ledger):
    pid = product(ledger)
    with ledger.connection(write=True) as db:
        ledger._move(db, dict(product_id=pid,kind="purchase",quantity=10,unit_price="1.00",request_key="old-buy"), "2025-01-01")
        sale = ledger._move(db, dict(product_id=pid,kind="sale",quantity=5,unit_price="3.00",request_key="old-sale"), "2025-01-02")
        ledger._move(db, dict(product_id=pid,kind="return",quantity=1,original_id=sale,request_key="later-return"), "2025-02-01")
    january = ledger.snapshot("2025-01-02", "2025-01-02")
    february = ledger.snapshot("2025-02-01", "2025-02-01")
    assert january["totals"]["profit"] == 1000
    assert february["totals"]["profit"] == -200
    assert february["totals"]["sold"] == -1
    assert february["totals"]["margin"] is None
    assert january["totals"]["stock_units"] == february["totals"]["stock_units"] == 6
    assert january["returnable"][0]["returnable"] == 4


def test_loss_and_gain_are_not_sales_or_purchases(ledger):
    pid = product(ledger)
    move(ledger, pid, "gain", 4, "2.00", note="Opening count")
    move(ledger, pid, "loss", 1, note="Damaged")
    totals = snapshot(ledger)["totals"]
    assert totals["profit"] == totals["purchases"] == totals["revenue"] == 0
    assert totals["stock_value"] == 600 and totals["losses"] == 200


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.001", "10000001", 10, None])
def test_money_rejects_invalid_values(value):
    with pytest.raises(Invalid):
        money(value)


@pytest.mark.parametrize("qty", [-1, 0, True, 1.5, "2", 1_000_001])
def test_invalid_quantity_does_not_write(ledger, qty):
    pid = product(ledger)
    with pytest.raises(Invalid):
        move(ledger, pid, "purchase", qty)
    assert not snapshot(ledger)["movements"]


def test_product_archive_cannot_hide_existing_stock(ledger):
    pid = product(ledger)
    move(ledger, pid, "purchase", 1)
    payload = dict(sku="Coffee",name="Coffee",price="10.00",minimum=2,active=False)
    with pytest.raises(Invalid, match="archive_stock"):
        ledger.save_product(payload, pid)
    move(ledger, pid, "loss", 1, note="Count correction")
    ledger.save_product(payload, pid)
    with pytest.raises(Invalid, match="missing"):
        move(ledger, pid, "sale", 1)


def test_demo_is_atomic_and_cannot_replace_real_data(ledger):
    ledger.seed_demo()
    s = snapshot(ledger)
    assert len(s["products"]) == 6 and s["demo"]
    with pytest.raises(Invalid, match="demo_not_empty"):
        ledger.seed_demo()
    assert len(snapshot(ledger)["products"]) == 6
