# Resultados verificados da entrega

Execução em 17/11/2026, em Windows dentro de VM sem virtualização, com MySQL 8.0.44 e MongoDB 6.0.26 portáteis.

| Medida | MySQL | MongoDB |
|---|---:|---:|
| Itens | 60.175 | 60.175 |
| Itens atrasados | 37.897 | 37.897 |
| Soma dos dias de atraso | 1.576.087 | 1.576.087 |

Validação integral: **OK**, com zero itens divergentes. Conferência por chave, todos os atributos transformados e totais por modalidade/mês. Os seis pipelines foram executados no MongoDB.

O teste de reexecução em uma base temporária separada publicou 101 e depois 51 documentos. As duas validações passaram e a fato principal permaneceu com 60.175 documentos.

## Análise dos resultados

O recorte contém 60.175 itens de pedido, dos quais 37.897 chegaram após a data comprometida.

A taxa de atraso é 62,98%. Cada item tem o mesmo peso, independentemente da quantidade de unidades.

Entre os itens atrasados, o atraso médio é 41,59 dias corridos.

Entre modalidades com pelo menos 100 itens, FOB tem a maior taxa (63,46%, 8.641 itens) e REG AIR a menor (62,33%, 8.616 itens). A diferença descritiva é 1,13 pontos percentuais.

A diferença entre modalidades ficou abaixo de 2 pontos percentuais. Esse limite é um critério exploratório da equipe, sem teste de significância. O resultado pede investigar atrasos compartilhados antes de propor troca de modalidade.

Supplier#000000038 reúne o maior número de itens atrasados (433, 1,14% dos atrasados), com taxa de 64,82% em 668 itens. O volume orienta uma auditoria inicial, sem atribuir a causa ao fornecedor.

Os dez fornecedores com mais ocorrências acumulam 4.184 itens atrasados, 11,04% do total de atrasados. Esse indicador complementa o ranking individual para avaliar concentração.

A faixa acima de 14 dias reúne 31.122 itens, 82,12% dos atrasados. O acompanhamento deve combinar redução da frequência com tratamento dos atrasos longos.

Na evolução mensal, confira o volume de cada coorte. Os meses de borda do período gerado têm composições e volumes diferentes e não comprovam melhoria ou piora operacional. O gráfico usa o mês do compromisso, mantendo a mesma definição do denominador.

Ações propostas: conferir compromissos de entrega, investigar modalidades/rotas com taxa elevada e volume suficiente e acompanhar taxa e gravidade mensalmente. O TPC-H é sintético e sustenta uma demonstração do método, sem evidenciar ganhos em uma empresa real.

Fonte: MySQL TPC-H, ETL para MongoDB, consultas em queries/. Evidências: validacao.json e resultados.json.


## Pendência

O Redash não foi executado nesta VM. A virtualização está desativada, conforme informado pelo usuário. A importação por API e a conferência visual do dashboard continuam pendentes em ambiente compatível. O painel offline apresenta as saídas reais do MongoDB e está identificado como apoio à apresentação.
