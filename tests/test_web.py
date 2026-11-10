from fastapi.testclient import TestClient

from stock.ledger import Ledger
from stock.web import create_app


def test_http_security_csv_and_restorable_backup(tmp_path):
    app = create_app(tmp_path / "web.sqlite3")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
        assert client.post("/api/demo",json={}).status_code == 403
        token = client.get("/api/state").json()["csrf_token"]
        headers = {"x-csrf-token":token}
        assert client.post("/api/demo",json={},headers=dict(headers,origin="https://other.example")).status_code == 403
        added = client.post("/api/products",json=dict(sku="=1+1",name="@product",price="2.00",minimum=1),headers=headers)
        assert added.status_code == 200
        pid = added.json()["id"]
        payload = dict(product_id=pid,kind="purchase",quantity=5,unit_price="1.23",request_key="http-key")
        assert client.post("/api/movements",json=payload,headers=headers).status_code == 200
        exported = client.get("/api/export/products")
        assert "'=1+1" in exported.text and "'@product" in exported.text
        backup = tmp_path / "restored.sqlite3"
        backup.write_bytes(client.get("/api/backup").content)
        assert Ledger(backup).snapshot("0001-01-01","9999-12-31")["totals"]["stock_value"] == 615
        assert client.get("/api/state?start=wrong").status_code == 400
        assert client.get("/api/state",headers={"host":"untrusted.example"}).status_code == 400


def test_malformed_or_oversized_http_input_returns_controlled_error(tmp_path):
    with TestClient(create_app(tmp_path / "requests.sqlite3")) as client:
        headers = {"x-csrf-token":client.get("/api/state").json()["csrf_token"],"content-type":"application/json"}
        assert client.post("/api/products",content="{broken",headers=headers).status_code == 400
        assert client.post("/api/products",json=[],headers=headers).status_code == 400
        assert client.post("/api/products",content='"' + 'x'*33000 + '"',headers=headers).status_code == 413
        assert client.post("/api/products",content="{}",headers=dict(headers,**{"content-length":"invalid"})).status_code == 400
