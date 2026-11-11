# Estoque Local

[Português](README.pt-BR.md)

A local web application for products, purchases, sales, partial returns,
losses and incoming stock adjustments. The interface reports stock balances,
revenue, cost of sales, gross profit, margin and product rankings.

Data stays on the user's computer. The project has no accounts and is not
designed to be exposed directly to the internet.

## Run

Python 3.11 or later is required. On Windows:

```powershell
.\start.ps1 -Setup
```

Then open http://127.0.0.1:8765. For later runs, use `start.cmd` or
`start.ps1`.

On Linux or macOS, create a virtual environment, install `requirements.txt`
and run:

```bash
python run.py
```

The database is created at `data/stock.sqlite3`. The **Download backup**
button creates a consistent copy of that database.

## Main decisions

- **SQLite:** one file is enough for this local, single-user application and no
  database server has to be installed.
- **Integer cents:** money never uses binary floating-point values, avoiding
  rounding differences in totals and allocations.
- **Transactions:** the stock balance and its movement history are committed
  together; if either write fails, both are rolled back.
- **Weighted-average cost:** incoming stock updates inventory value. A sale
  keeps the cost calculated at that time, and a return restores the original
  sale cost.

See [docs/DOMAIN_RULES.md](docs/DOMAIN_RULES.md) for the complete rules and
limits.

## Structure

- `stock/ledger.py`: database, validation and inventory rules;
- `stock/web.py`: local HTTP API, CSV exports and backup;
- `stock/static/`: JavaScript, HTML and CSS interface;
- `tests/`: business scenarios and HTTP flow.

## Tests

Install `requirements-dev.txt`, then run:

```text
python -m pytest -q
node --check stock/static/app.js
node --check stock/static/views.js
```

The **How it works** page explains the displayed indicators. Gross profit does
not deduct operating expenses, sales taxes or fees.
