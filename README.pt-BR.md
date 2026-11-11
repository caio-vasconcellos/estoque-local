# Estoque Local

[English](README.md)

Aplicação web local para cadastrar produtos e registrar compras, vendas,
devoluções parciais, perdas e ajustes de entrada. A interface mostra saldo,
receita, custo das vendas, lucro bruto, margem e rankings por produto.

Os dados ficam no computador do usuário. O projeto não possui login nem foi
feito para ser exposto diretamente à internet.

## Executar

Requer Python 3.11 ou superior. No Windows:

```powershell
.\start.ps1 -Setup
```

Depois, acesse http://127.0.0.1:8765. Nas próximas execuções, use
`start.cmd` ou `start.ps1`.

Em Linux ou macOS, crie um ambiente virtual, instale `requirements.txt` e
execute:

```bash
python run.py
```

O banco é criado em `data/stock.sqlite3`. O botão **Baixar backup** gera uma
cópia consistente desse banco.

## Decisões principais

- **SQLite:** funciona em um único arquivo e não exige instalar um servidor de
  banco de dados para este uso local.
- **Centavos inteiros:** valores monetários não usam ponto flutuante, evitando
  diferenças de arredondamento em somas e rateios.
- **Transações:** a mudança no saldo e o registro da movimentação são
  confirmados juntos; se uma etapa falhar, ambas são revertidas.
- **Custo médio:** cada entrada atualiza o valor do estoque. A venda grava o
  custo calculado naquele momento, e uma devolução recupera o custo da venda
  original.

As regras completas e seus limites estão em
[docs/DOMAIN_RULES.md](docs/DOMAIN_RULES.md).

## Organização

- `stock/ledger.py`: banco, validações e regras de estoque;
- `stock/web.py`: API HTTP local, exportação CSV e backup;
- `stock/static/`: interface em JavaScript, HTML e CSS;
- `tests/`: cenários de negócio e fluxo HTTP.

## Testes

Instale `requirements-dev.txt` e execute:

```text
python -m pytest -q
node --check stock/static/app.js
node --check stock/static/views.js
```

A seção **Como funciona** da interface explica os indicadores exibidos. Lucro
bruto não desconta despesas operacionais, impostos sobre vendas ou taxas.
