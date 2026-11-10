# Estoque Local — núcleo de estoque

[English](README.md)

Parte 1 de 3: núcleo de estoque em Python e SQLite. Inclui produtos, compras,
vendas, devoluções parciais, ajustes, custo médio e validações de saldo.
Valores monetários são centavos inteiros. Saldo e histórico são gravados juntos,
com proteção contra repetição de uma mesma movimentação.

## Executar os testes do núcleo

Python 3.11 ou superior:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Em Linux/macOS, use `.venv/bin/python`. São 26 testes das regras de negócio,
incluindo vendas concorrentes, rollback de falhas e rateio de devoluções parciais.
O núcleo pode ser importado com `from stock.ledger import Ledger`.

A interface web e a API chegam na parte 2. A documentação completa, as capturas
de tela e o GitHub Actions chegam na parte 3. São pontos do trabalho já
desenvolvido localmente, preparados para publicação gradual.
