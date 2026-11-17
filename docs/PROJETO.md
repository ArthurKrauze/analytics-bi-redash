# Problema gerencial e indicadores

## Demanda

Equipe 12, Desafio 12: atrasos nas entregas. A decisão apoiada é definir onde iniciar a investigação de falhas operacionais e quais indicadores acompanhar após intervenções logísticas.

Perguntas: qual parcela dos itens chegou depois do compromisso? Quais modalidades apresentam taxas mais altas? O padrão se repete ao longo dos meses? Quais fornecedores concentram maior quantidade de itens atrasados e qual sua taxa?

## Escopo

Base TPC-H gerada com a extensão tpch/dbgen do DuckDB, escala padrão 0.01. As oito tabelas são carregadas em MySQL. O projeto analisa todos os itens dessa base por padrão. A escala pequena permite demonstração em uma VM e validação integral por chave. O recorte conserva as dimensões e relacionamentos TPC-H, mas os dados são sintéticos e não representam uma empresa real. Não se trata de execução certificada de benchmark de desempenho.

## Dicionário das medidas

| Indicador | Definição | Unidade | Interpretação |
|---|---|---|---|
| Total de itens | Contagem de documentos | itens de pedido | Denominador da taxa |
| Itens atrasados | Contagem com recebimento > compromisso | itens de pedido | Frequência absoluta |
| Taxa de atraso | 100 × atrasados / total | % | Frequência relativa |
| Dias de atraso por item | max(recebimento - compromisso, 0) | dias corridos | Gravidade por item |
| Soma de dias de atraso | Soma dos atrasos individuais | dias-item | Acúmulo de atraso, não tempo de calendário |
| Média entre atrasados | Soma dos dias / itens atrasados | dias corridos | Gravidade condicional ao atraso |
| Participação nos atrasos | Atrasados do grupo / atrasados gerais × 100 | % | Concentração de ocorrências |

Taxas e médias são medidas derivadas e não aditivas. Para consolidar grupos, some numeradores e denominadores e depois recalcule. Não faça média simples das taxas das modalidades.

Quando não existem itens atrasados, a média é nula (não aplicável). Uma base vazia reprova a validação. O recebimento no mesmo dia do compromisso conta como pontual. As datas são dias do TPC-H, armazenados à meia-noite UTC, sem conversão para horário local no agrupamento mensal.

## Decisões e limites

O ranking de fornecedores ordena quantidade de itens atrasados e mostra também taxa e volume. Uma taxa elevada em poucos itens não basta para priorização. O relatório considera pelo menos 100 itens para a comparação exploratória de modalidades. Esse corte e a diferença de 2 pontos percentuais são critérios de triagem, sem teste estatístico de significância.

Uma associação entre modalidade, fornecedor e atraso não identifica sua causa. Atrasos podem envolver rotas, tipos de produto e compromissos definidos antes do envio. O TPC-H não informa transportadora nem custo de frete efetivamente pago. O trabalho não atribui perdas financeiras, economia ou culpa a partir desses indicadores.

## Encaminhamento gerencial

1. Avaliar taxa e gravidade simultaneamente, com volume visível.
2. Investigar compromissos, rotas e perfis de carga dos grupos mais relevantes.
3. Definir responsáveis e uma meta operacional somente depois de entender as causas.
4. Acompanhar coortes mensais pela data comprometida e comparar o mesmo escopo ao longo do tempo.

Os achados numéricos finais ficam em artifacts/ANALISE_GERENCIAL.md e nas evidências verificadas da entrega.
