# How inventory is calculated

[Português](DOMAIN_RULES.md)

The calculations are in `stock/ledger.py`. These examples use fictional values.

## Local database

SQLite keeps this single-user app in one file, `data/stock.sqlite3`, without a
separate database server. Report reads use one transaction so products,
movements and totals describe the same state. Writes use `BEGIN IMMEDIATE`
so concurrent sales cannot both rely on the same stock balance.

## Money in cents

Prices, costs, revenue and inventory value are integer cents. The API receives
decimal strings, accepts up to two decimal places and converts them before
storage. Money is not calculated with binary floating-point values.

## Balance and history

Each purchase, sale, return, loss or adjustment changes the product and records
a movement in the same transaction. If history cannot be written, the balance
change rolls back. The database also rejects negative stock and inventory
value. A product with stock cannot be archived.

## Average cost and sales

Incoming stock adds quantity and cost. Outgoing stock receives a proportional
share of current inventory value, rounded to a cent. Selling all remaining
units removes their exact remaining value. Each sale keeps its cost; later
purchases never change earlier profit.

For example: buying 10 units at R$10 and another 10 at R$20 leaves 20 units
with total cost R$300, or R$15 per unit. Selling 5 at R$25 produces R$125 in
revenue, R$75 in cost and R$50 in gross profit. The balance is 15 units worth
R$225.

## Partial returns

A return references the original sale, refunds its price and restores its
historical cost. Partial returns use the difference between the cumulative
cost before and after that return. Together, they restore the exact original
cost, including rounding cents. Returns cannot exceed the quantity still
available to return.

## Retries and dates

Each movement has a request key. Repeating the same key and contents returns
the existing record; reusing it with different contents is rejected.

The period filters sales, returns, purchases and losses. Both boundary dates
are included. Stock, average cost and inventory value always show current
balances. Returns count on their recorded date, even for an older sale, so a
period can have negative net revenue or units. Backdating is unavailable.

## Reading the rankings

Best sellers have the most net units sold, which does not necessarily mean
the highest profit. In the sample catalogue, olive oil sells 51 units for
R$249.90 gross profit; honey sells 42 for R$751.80.

Gross margin is gross profit divided by positive net revenue. It is left
blank without positive revenue. Active products without sales appear in the
slowest-seller ranking. Rankings show up to five products; the CSV includes
the full catalogue, with monetary values in integer cents.

## What is left out

Purchase spending is not cost of sales: some goods may remain in stock.
Losses are shown separately from gross profit. There is no net-profit or tax
calculation, or automatic allocation of freight and expenses.

A return corrects a sale. Reasoned adjustments correct stock but do not rewrite
historical purchase spending. Purchase reversals are not available in this
version.
