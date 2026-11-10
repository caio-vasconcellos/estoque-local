# Estoque Local

[English](README.md)

Parte 2 de 3: aplicação web local sobre o núcleo de estoque.

Cadastre produtos, compras, vendas, devoluções parciais e ajustes.
Compare sete rankings, receita, custo histórico, lucro bruto e margem.
Inclui português e inglês, filtros por data, buscas, CSV e backup.

## Executar

Python 3.11 ou superior. No Windows:

```powershell
.\start.ps1 -Setup
```

Acesse http://127.0.0.1:8765. Após instalar, abra `start.cmd` ou execute `start.ps1`.
Em Linux/macOS, crie um ambiente virtual, instale `requirements.txt` e execute
`.venv/bin/python run.py`.

O banco é `data/stock.sqlite3`. O aplicativo é local, para uma pessoa;
não o exponha diretamente à internet. Lucro bruto não desconta despesas
operacionais, impostos sobre vendas ou taxas. A seção Como funciona explica
as regras dos cálculos. Dados e ambiente virtual ficam fora do Git.

## Testes

Instale `requirements-dev.txt` e execute `python -m pytest -q` (28 testes).
Confira a sintaxe JavaScript com `node --check stock/static/app.js`.

A parte 3 acrescenta documentação completa nos dois idiomas, capturas e GitHub Actions.
