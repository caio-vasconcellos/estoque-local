from datetime import date, timedelta
from io import StringIO
from pathlib import Path
import csv
import os
import secrets
import sqlite3
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .ledger import Invalid, Ledger

ROOT = Path(__file__).resolve().parent


def csv_cell(value):
    text = str(value) if value is not None else ""
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def create_app(database=None):
    ledger = Ledger(database or os.environ.get("ESTOQUE_DB", str(ROOT.parent / "data" / "stock.sqlite3")))
    token = secrets.token_urlsafe(32)
    app = FastAPI(title="Estoque Local", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ledger = ledger
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    @app.middleware("http")
    async def local_security(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), token):
                return JSONResponse({"error": "csrf"}, status_code=403)
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"error": "csrf"}, status_code=403)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": "json"}, status_code=415)
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"error": "json"}, status_code=400)
            if length > 32_768:
                return JSONResponse({"error": "size"}, status_code=413)
        response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "Cache-Control": "no-store",
        })
        return response

    @app.exception_handler(Invalid)
    async def invalid(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=400)

    async def body(request):
        import json
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 32_768:
                raise Invalid("size")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise Invalid("json") from None
        if not isinstance(data, dict):
            raise Invalid("json")
        return data

    def dates(start=None, end=None):
        today = date.today()
        return start or (today - timedelta(days=29)).isoformat(), end or today.isoformat()

    @app.get("/api/state")
    def state(start: str | None = None, end: str | None = None):
        return dict(ledger.snapshot(*dates(start, end)), csrf_token=token, today=date.today().isoformat())

    @app.post("/api/products")
    async def add_product(request: Request):
        return {"id": ledger.save_product(await body(request))}

    @app.put("/api/products/{product_id}")
    async def edit_product(product_id: int, request: Request):
        return {"id": ledger.save_product(await body(request), product_id)}

    @app.post("/api/movements")
    async def movement(request: Request):
        return {"id": ledger.move(await body(request))}

    @app.post("/api/demo")
    async def demo(request: Request):
        await body(request)
        ledger.seed_demo()
        return {"ok": True}

    @app.get("/api/export/{report}")
    def export(report: str, start: str | None = None, end: str | None = None):
        snapshot = ledger.snapshot(*dates(start, end))
        if report == "products":
            rows = snapshot["products"]
            columns = ["sku", "name", "category", "supplier", "active", "quantity", "minimum", "price_cents", "average_cents", "value_cents", "sold", "revenue", "cogs", "profit", "margin", "purchases"]
        elif report == "movements":
            rows = snapshot["movements"]
            columns = ["id", "occurred_on", "sku", "name", "kind", "quantity", "stock_delta", "cost_delta", "revenue_delta", "spend_cents", "unit_cents", "original_id", "note"]
        else:
            raise Invalid("missing")
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(csv_cell(row[c]) if isinstance(row[c], str) else row[c] for c in columns)
        return Response("\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{report}-{snapshot["end"]}.csv"'})

    @app.get("/api/backup")
    def backup():
        # SQLite's backup API includes committed data consistently during live use.
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "backup.sqlite3"
            source = sqlite3.connect(ledger.path)
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            contents = target.read_bytes()
        return Response(contents, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="estoque-{date.today()}.sqlite3"'})

    app.mount("/assets", StaticFiles(directory=ROOT / "static"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app
