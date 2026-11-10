# Regras de domínio

Este documento registra as invariantes principais do núcleo de estoque.

## Valores monetários

Valores monetários são armazenados como centavos inteiros. Essa escolha evita erros de arredondamento causados por números de ponto flutuante.

## Movimentações de estoque

O núcleo contempla compras, vendas, devoluções parciais e ajustes. Toda movimentação deve manter o saldo de estoque consistente com o respectivo lançamento no livro-razão.

## Atomicidade

A alteração do estoque e o lançamento associado devem ser confirmados juntos. Se qualquer etapa falhar, a operação inteira deve ser revertida.

## Idempotência

Uma movimentação repetida com o mesmo identificador não deve ser aplicada novamente. Essa proteção evita duplicações em tentativas reenviadas.

## Custo médio ponderado

Entradas de produtos atualizam o custo médio ponderado. Saídas utilizam o custo vigente sem recalcular o valor unitário das unidades restantes.

## Validação

Mudanças nas regras de negócio devem incluir testes automatizados. Antes de abrir um pull request, execute:

```text
python -m pytest -q
```
