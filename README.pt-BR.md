# Estoque Local

[English](README.md)

Controle de estoque para uma pequena loja, feito com Python, FastAPI e SQLite.
Registre compras e vendas, veja o que precisa de reposição e compare os produtos
que mais saem com os que deixam mais lucro bruto.

Inclui devoluções parciais, ajustes de estoque, filtros por período, sete
rankings, exportação CSV e interface em português e inglês. Roda no seu
computador, sem conta ou serviço externo. As quantidades são inteiras e os
valores são em reais.

## Executar

Use Python 3.11 ou superior. No Windows, abra um terminal nesta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Acesse [127.0.0.1:8765](http://127.0.0.1:8765). Mantenha o terminal aberto
enquanto usa o aplicativo; Ctrl+C encerra o servidor. Depois de instalar,
`start.cmd` também abre o sistema. O atalho `./start.ps1 -Setup` cria o ambiente
e instala as dependências para você.

Em Linux/macOS, use `.venv/bin/python` no lugar de `.venv\Scripts\python.exe`.
Se o Python não incluir `venv`, instale `virtualenv` e crie o ambiente com
`python -m virtualenv .venv`.

## Primeiro uso

Cadastre um produto com código, preço de venda e estoque mínimo. Registre uma
compra com quantidade e custo por unidade. Depois lance as vendas conforme
acontecem; cada movimentação atualiza o saldo.

**Explorar com dados de exemplo** carrega uma loja fictícia no catálogo vazio.
Esses registros ficam no mesmo banco dos lançamentos que você fizer depois.
Para começar com um banco limpo separado, pare o servidor e escolha outro
caminho antes de abrir:

```powershell
$env:ESTOQUE_DB = "data/minha-loja.sqlite3"
.\.venv\Scripts\python.exe run.py
```

O banco anterior continua no lugar. Movimentações não podem ser apagadas nem
lançadas com data passada. Para corrigir uma venda, registre uma devolução.
Para perdas e diferenças de contagem, use um ajuste com motivo.

## Backup

O banco padrão é `data/stock.sqlite3`. **Baixar backup** cria uma cópia
consistente com o sistema aberto. Guarde cópias fora deste computador.

Para restaurar: pare o servidor, preserve o banco atual, copie o backup para o
caminho configurado e abra o aplicativo novamente. Não há botão de restauração
destrutiva. Os CSVs são relatórios, não backups do banco; as colunas monetárias
usam centavos inteiros.

## Sobre as contas

O SQLite guarda este sistema local, de uma pessoa, em um arquivo. Saldo e
histórico são gravados juntos. O dinheiro fica em centavos, e a venda mantém
seu custo histórico mesmo depois de uma compra mudar o custo médio.

[Veja as contas e um exemplo](docs/DOMAIN_RULES.md).

Lucro bruto não desconta aluguel, salários, impostos sobre vendas nem taxas.
A seção **Como funciona** explica os indicadores. Não exponha o aplicativo
diretamente à internet: ele não tem login.

## Mexer no código

Instale `requirements-dev.txt` e execute `python -m pytest -q` no ambiente
virtual. Node só é necessário para conferir a sintaxe JavaScript, não para
usar o aplicativo. Os comandos estão no [guia de contribuição](CONTRIBUTING.md).

As regras de estoque ficam em `stock/ledger.py`, a API em `stock/web.py` e a
interface em `stock/static/`. Bancos locais e ambientes virtuais ficam fora do
Git.
