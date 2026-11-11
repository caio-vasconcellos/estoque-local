# Regras de domínio

Este documento resume as regras que podem ser confirmadas em
`stock/ledger.py` e nos testes automatizados.

## Persistência local

O projeto usa SQLite porque a aplicação é local e destinada a uma pessoa. O
banco inteiro fica em `data/stock.sqlite3`, sem exigir um servidor separado.

Leituras de relatório usam uma única transação para manter produtos,
movimentações e totais no mesmo estado. Escritas usam `BEGIN IMMEDIATE` para
que duas saídas concorrentes não validem o mesmo saldo ao mesmo tempo.

## Dinheiro em centavos

Preços, custos, receita e valor do estoque são inteiros em centavos. A API
recebe textos decimais, valida no máximo duas casas e converte antes de gravar.
Isso evita cálculos monetários com ponto flutuante.

## Saldo e histórico

Cada compra, venda, devolução, perda ou ajuste altera o produto e cria uma
movimentação na mesma transação. Se o histórico não puder ser gravado, a
alteração do saldo é revertida.

O banco também impede saldo e valor de estoque negativos. Um produto com saldo
não pode ser arquivado.

## Custo médio e vendas

Uma entrada soma quantidade e custo ao estoque. Uma saída recebe uma parte
proporcional do valor atual, arredondada ao centavo. Quando todo o saldo sai,
todo o valor restante também sai.

O custo fica gravado na movimentação da venda. Compras posteriores não alteram
o lucro de vendas antigas.

## Devoluções parciais

A devolução aponta para uma venda original, estorna sua receita e repõe seu
custo histórico. Em devoluções parciais, o cálculo usa a diferença entre o
custo acumulado antes e depois da nova parcela. Assim, a soma de todas as
parcelas devolve exatamente os centavos da venda original.

Não é possível devolver mais unidades do que a venda ainda possui.

## Reenvio e período

Cada movimentação possui uma chave de requisição. Repetir a mesma chave com o
mesmo conteúdo retorna o registro existente; reutilizá-la com conteúdo
diferente é rejeitado.

Relatórios aplicam o período a vendas, devoluções, compras e perdas. Saldo,
custo médio e valor em estoque sempre representam o estado atual.
