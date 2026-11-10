# Estoque Local

[Português](README.pt-BR.md)

Stage 2 of 3: the local web application, built on the inventory core.

Manage products, purchases, sales, partial returns and stock adjustments.
Compare seven product rankings, revenue, historical cost, gross profit and margin.
Includes Portuguese and English, date filters, searches, CSV exports and backups.

## Run

Python 3.11 or later. On Windows:

```powershell
.\start.ps1 -Setup
```

Open http://127.0.0.1:8765. After setup, double-click `start.cmd` or run `start.ps1`.
On Linux/macOS, create a virtual environment, install `requirements.txt` and use
`.venv/bin/python run.py`.

The database is `data/stock.sqlite3`. This is a local, single-user application;
do not expose it directly to the internet. Gross profit excludes operating
expenses, sales taxes and fees. The interface explains the accounting rules
under How it works. Runtime data and the virtual environment are excluded from Git.

## Tests

Install `requirements-dev.txt`, then run `python -m pytest -q` (28 tests).
Use `node --check stock/static/app.js` to check JavaScript syntax.

Stage 3 adds complete bilingual documentation, screenshots and GitHub Actions.
