# Estoque Local — inventory core

[Português](README.pt-BR.md)

Stage 1 of 3: the Python and SQLite inventory core. Includes products, purchases,
sales, partial returns, adjustments, weighted-average costs and stock validation.
Money is stored as integer cents. Every stock change and its ledger record commit
together. Retried movements are protected against duplication.

## Run the core tests

Python 3.11 or later:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Use `.venv/bin/python` on Linux/macOS. This stage contains 26 business-rule tests,
including concurrent sales, failed-write rollback and partial-return rounding.
The core can be imported with `from stock.ledger import Ledger`.

The web interface and HTTP API arrive in stage 2. Full documentation, screenshots
and GitHub Actions arrive in stage 3. These are checkpoints of work already
implemented locally, prepared for sequential publication.
