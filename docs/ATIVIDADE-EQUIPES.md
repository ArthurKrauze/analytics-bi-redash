# Atividade após a demonstração

Cada equipe recebe uma **pergunta analítica diferente**, sem receber a query
resolvida. Entregáveis: questão de negócio, modelo conceitual, justificativa
de embedding/referencing, ETL reprodutível, validação contra MySQL, queries
e dashboard no Redash.

Possíveis temas: desempenho regional; evolução temporal; mix de marcas;
fornecedores; segmentos; faixas de desconto; concentração; fluxo entre
região de cliente e fornecedor; pedidos distintos; tipos de produto.

**Cuidados de avaliação:**
- Explicar o grão (item, pedido, cliente etc.).
- Demonstrar a origem de cada atributo no TPC-H.
- Validar totais com a mesma amostra e mesma regra de negócio.
- Diferenciar região do cliente e do fornecedor.
- Distinguir contagem de itens de contagem de pedidos distintos.
- Não generalizar conclusões a partir dos primeiros 10 mil itens.

O professor distribui temas e valida cada consulta antes da atividade.
