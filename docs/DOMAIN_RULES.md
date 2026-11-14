# Como o estoque é calculado

[English](DOMAIN_RULES.en.md)

As contas ficam em `stock/ledger.py`. Os exemplos abaixo usam valores fictícios.

## Banco local

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

Por exemplo: comprar 10 unidades por R$ 10 e mais 10 por R$ 20 deixa 20 unidades
com custo total de R$ 300, ou R$ 15 por unidade. Vender 5 por R$ 25 gera receita
de R$ 125, custo de R$ 75 e lucro bruto de R$ 50. O saldo fica em 15 unidades,
com valor de R$ 225.

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

As datas inicial e final entram no filtro. Devoluções contam no dia em que são
registradas, mesmo quando a venda é antiga; por isso um período pode ter receita
ou quantidade líquida negativa. Não há lançamentos retroativos.

## Ler os rankings

Mais vendido é quem tem mais unidades líquidas vendidas; isso não significa
maior lucro. No catálogo de exemplo, o azeite vende 51 unidades e deixa
R$ 249,90 de lucro bruto. O mel vende 42 e deixa R$ 751,80.

Margem bruta é lucro bruto dividido pela receita líquida positiva. Ela fica em
branco quando não há receita positiva. Produtos ativos sem vendas entram no
ranking de menos vendidos. Os rankings mostram até cinco produtos; o CSV traz
o catálogo completo. Seus valores monetários são centavos inteiros.

## O que fica de fora

Gasto em compras não é custo de vendas: parte da compra pode continuar em
estoque. Perdas aparecem separadas do lucro bruto. Não há cálculo de lucro
líquido, impostos ou rateio automático de frete e despesas.

Uma devolução corrige uma venda. Ajustes corrigem o saldo, com motivo, mas não
reescrevem o gasto histórico em compras. Esta versão não tem estorno de compra.
