const paragraph = (...sentences) => sentences.join(" ");

export const guideArticles = {
  pt: [
    [
      "Comece pelo que entrou",
      paragraph(
        "Cadastre nome, código, categoria, fornecedor, preço de venda e estoque mínimo.",
        "Depois registre uma compra com quantidade e custo unitário.",
        "O estoque inicial também deve ser registrado como entrada, nunca digitado por cima do saldo.",
      ),
    ],
    [
      "Custo médio, sem reescrever o passado",
      paragraph(
        "Cada entrada soma seu custo ao valor que já está no estoque.",
        "Uma saída recebe sua proporção desse valor, arredondada ao centavo.",
        "A última unidade leva os centavos restantes.",
        "Esse custo fica gravado na venda; uma compra futura não altera o resultado de vendas anteriores.",
        'O método segue a ideia de custo médio ponderado citada no <a href="https://www.cpc.org.br/CPC/Documentos-emitidos/Pronunciamentos/Pronunciamento?Id=47" target="_blank" rel="noreferrer">CPC 16</a>.',
        "O aplicativo é um controle gerencial e não implementa todos os requisitos contábeis da norma.",
      ),
    ],
    [
      "O que os rankings respondem",
      paragraph(
        "Mais e menos vendidos usam quantidade líquida, incluindo devoluções registradas no período.",
        "Produtos ativos sem vendas entram no ranking de menos vendidos.",
        "Lucro bruto é receita menos custo histórico das unidades vendidas.",
        "Margem é lucro bruto dividido pela receita; sem receita positiva, a margem fica em branco.",
        "O custo médio e o valor do saldo mostram a situação atual.",
        "Gasto em compras considera o período selecionado.",
        "Empates são ordenados pelo nome do produto.",
        "Os rankings mostram até cinco produtos; o CSV traz o catálogo completo.",
      ),
    ],
    [
      "Compra, venda e lucro não são a mesma coisa",
      paragraph(
        "Comprar R$ 1.000 em mercadoria não significa ter R$ 1.000 de custo de vendas naquele dia.",
        "Parte pode continuar em estoque.",
        "O lucro bruto mostrado não desconta aluguel, salários, taxas ou impostos sobre vendas.",
        "Perdas são baixas de estoque e aparecem separadamente.",
        "Custo de entrada deve representar o custo que você deseja atribuir à unidade, incluindo frete rateado quando aplicável.",
        "Não há rateio automático.",
      ),
    ],
    [
      "Devoluções e correções",
      paragraph(
        "Uma devolução referencia a venda original, devolve as unidades ao estoque e estorna o preço e o custo daquela venda.",
        "Devoluções parciais são permitidas até a quantidade vendida.",
        "Para corrigir uma venda errada, devolva e registre novamente.",
        "Para perdas ou diferenças de contagem, use os ajustes com motivo obrigatório.",
        "Compras e ajustes não podem ser apagados ou editados; corrija o saldo por um ajuste identificado.",
        "Isso não reescreve gasto histórico em compras.",
        "Se precisar corrigir o histórico financeiro, este projeto ainda não oferece estorno de compra.",
      ),
    ],
    [
      "Datas e arquivos",
      paragraph(
        "Movimentos usam a data local do computador que roda o servidor.",
        "Não há lançamento retroativo, pois isso exigiria recalcular os custos posteriores.",
        "O período inclui as datas inicial e final; devoluções contam na data em que foram registradas, mesmo que a venda seja de outro período.",
        "O CSV usa cabeçalhos estáveis em inglês e valores em centavos.",
        "Textos que poderiam virar fórmulas em planilhas recebem um apóstrofo.",
      ),
    ],
    [
      "Seus dados ficam aqui",
      paragraph(
        "O banco fica em <code>data/stock.sqlite3</code>.",
        "Baixar backup gera uma cópia consistente; guarde-a fora deste computador.",
        "Para restaurar, pare o servidor, preserve o banco atual e copie o backup para esse caminho.",
        "Os dados de demonstração só entram com catálogo vazio e permanecem identificados.",
        "Não há botão que apague o histórico.",
        "Este aplicativo foi feito para uso local, por uma pessoa, sem login e sem serviço externo.",
        "Não o exponha diretamente à internet.",
      ),
    ],
  ],
  en: [
    [
      "Start with incoming stock",
      paragraph(
        "Add a name, code, category, supplier, selling price and minimum quantity.",
        "Then record a purchase with its quantity and unit cost.",
        "Opening stock must also be recorded as an incoming movement, never typed over the balance.",
      ),
    ],
    [
      "Average cost, with a lasting history",
      paragraph(
        "Each receipt adds its cost to existing inventory value.",
        "An outgoing movement receives its proportion of that value, rounded to a cent.",
        "The last unit receives the remaining cents.",
        "This cost is saved with the sale; later purchases never change earlier sales results.",
        'The method uses the weighted-average concept described in <a href="https://www.cpc.org.br/CPC/Documentos-emitidos/Pronunciamentos/Pronunciamento?Id=47" target="_blank" rel="noreferrer">CPC 16</a>.',
        "This is a management tool and does not implement every accounting requirement of that standard.",
      ),
    ],
    [
      "What the rankings answer",
      paragraph(
        "Best and slowest sellers use net quantities, including returns recorded in the period.",
        "Active products with no sales are included in the slowest-seller ranking.",
        "Gross profit is revenue less historical cost of units sold.",
        "Margin is gross profit divided by revenue; without positive revenue, it is left blank.",
        "Average cost and stock value show current balances.",
        "Purchase spending uses the selected period.",
        "Ties are sorted by product name.",
        "Rankings show up to five products; the CSV includes the full catalogue.",
      ),
    ],
    [
      "Purchasing, selling and earning are different",
      paragraph(
        "Buying R$1,000 of goods does not mean R$1,000 of cost of sales that day.",
        "Some goods may remain in stock.",
        "Gross profit does not deduct rent, wages, fees or sales taxes.",
        "Stock losses are reported separately.",
        "Incoming unit cost should include the costs you want assigned to each unit, including allocated freight where appropriate.",
        "There is no automatic cost allocation.",
      ),
    ],
    [
      "Returns and corrections",
      paragraph(
        "A return references the original sale, restores units to stock and reverses their original selling price and cost.",
        "Partial returns are allowed up to the quantity sold.",
        "To correct a mistaken sale, return it and record a replacement.",
        "For damage or counting differences, use adjustments with a required reason.",
        "Purchases and adjustments cannot be deleted or edited; use an identified adjustment to correct stock.",
        "That does not change historical purchase spending.",
        "Purchase reversals for financial-history corrections are not available in this version.",
      ),
    ],
    [
      "Dates and files",
      paragraph(
        "Movements use the local date of the computer running the server.",
        "Backdating is unavailable because it would require recalculating later costs.",
        "The period includes both start and end dates.",
        "Returns count on their recorded date, even if the sale was in another period.",
        "CSV files use stable English headers and monetary values in cents.",
        "Text that could become a spreadsheet formula is prefixed with an apostrophe.",
      ),
    ],
    [
      "Your data stays here",
      paragraph(
        "The database is <code>data/stock.sqlite3</code>.",
        "Download backup creates a consistent copy; keep it outside this computer.",
        "To restore, stop the server, preserve the current database and copy the backup to that path.",
        "Demo data can only be loaded into an empty catalogue and remains labelled.",
        "There is no delete-history button.",
        "This is a local, single-user application, without accounts or external services.",
        "Do not expose it directly to the internet.",
      ),
    ],
  ],
};
