# Contribuindo

Obrigado pelo interesse em contribuir com o Estoque Local.

## Preparação do ambiente

1. Use Python 3.11 ou superior.
2. Crie e ative um ambiente virtual.
3. Instale as dependências de desenvolvimento com `python -m pip install -r requirements-dev.txt`.
4. Execute `python -m pytest -q` antes de enviar alterações.

## Fluxo sugerido

1. Crie uma branch curta e descritiva a partir de `main`.
2. Faça mudanças pequenas, mantendo uma finalidade clara por commit.
3. Inclua ou atualize testes quando alterar regras de negócio.
4. Abra um pull request explicando o problema e a solução adotada.

## Qualidade

- Preserve os valores monetários como centavos inteiros.
- Mantenha o registro de estoque e o lançamento no livro-razão na mesma transação.
- Evite alterações que quebrem a proteção contra movimentos duplicados.
- Não inclua bancos locais, ambientes virtuais ou credenciais no repositório.
