import pytest

from stock.ledger import Invalid, Ledger


def test_below_cost_and_zero_price_sales_report_losses(tmp_path):
    ledger = Ledger(tmp_path / "cost.sqlite3")
    pid = ledger.save_product(dict(sku="LOSS", name="Loss leader", price="0.00", minimum=0))
    for i, (kind, qty, price) in enumerate([("purchase", 3, "10.00"), ("sale", 1, "5.00"), ("sale", 1, "0.00")]):
        ledger.move(dict(product_id=pid,kind=kind,quantity=qty,unit_price=price,request_key=str(i)))
    p = ledger.snapshot("0001-01-01", "9999-12-31")["products"][0]
    assert (p["profit"], p["margin"], p["value_cents"]) == (-1500, -300, 1000)


def test_duplicate_sku_and_invalid_period_do_not_change_data(tmp_path):
    ledger = Ledger(tmp_path / "validation.sqlite3")
    ledger.save_product(dict(sku="ABC",name="One",price="1.00",minimum=0))
    with pytest.raises(Invalid, match="duplicate_sku"):
        ledger.save_product(dict(sku="abc",name="Two",price="1.00",minimum=0))
    with pytest.raises(Invalid, match="dates"):
        ledger.snapshot("2026-11-09", "2026-11-08")
    assert len(ledger.snapshot("0001-01-01", "9999-12-31")["products"]) == 1
