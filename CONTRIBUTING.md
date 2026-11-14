# Mexer no projeto / Working on the project

Com o ambiente virtual ativo, instale as dependências e rode os testes:

With the virtual environment active, install the dependencies and run tests:

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Se alterar JavaScript, confira todos os módulos. No PowerShell:

If you change JavaScript, check all modules. In PowerShell:

```powershell
Get-ChildItem stock/static/*.js | ForEach-Object { node --check $_.FullName }
```

Em Linux/macOS / On Linux/macOS:

```sh
for file in stock/static/*.js; do node --check "$file" || exit; done
```

Abra uma branch a partir de `main` e mantenha cada mudança focada. Ao alterar
custo, devolução ou saldo, teste também arredondamento, repetição de envio e
estoque insuficiente. Não inclua bancos locais, ambientes virtuais ou segredos.

Start a branch from `main` and keep each change focused. When changing cost,
returns or balances, also check rounding, retries and insufficient stock.
Do not commit local databases, virtual environments or secrets.
