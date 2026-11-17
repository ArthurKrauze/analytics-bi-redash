# Roteiro de apresentação — 10 minutos

Equipe 12, Desafio 12: atrasos nas entregas. Conforme o cronograma fornecido, o horário é 17/11/2026, 22h10–22h20.

| Tempo | Slide | Conteúdo e demonstração |
|---|---|---|
| 0:00–0:45 | 1 | Problema gerencial, escopo e decisão |
| 0:45–1:30 | 2 | Definição dos indicadores e do denominador |
| 1:30–2:30 | 3 | Modelo estrela e embedding |
| 2:30–3:45 | 4 | ETL, qualidade e publicação atômica |
| 3:45–4:45 | 5 | Validação real MySQL × MongoDB |
| 4:45–6:15 | 6 | Gráfico principal por modalidade |
| 6:15–7:15 | 7 | Complemento temporal e leitura das coortes |
| 7:15–8:30 | 8 | Gravidade dos atrasos e concentração nos fornecedores |
| 8:30–10:00 | 9 | Encaminhamento gerencial e limitações |


## Fala de abertura

“Nosso desafio é analisar atrasos nas entregas. A decisão que apoiamos é onde começar uma investigação logística. Medimos a proporção de itens recebidos depois da data comprometida e a gravidade desses atrasos.”

## Explicação técnica

“O grão é um item de pedido, identificado pelo pedido e pelo número do item. Um pedido com vários itens pode contribuir várias vezes para o indicador, por isso chamamos a medida de taxa de atraso de itens. Integramos dimensões do TPC-H no MySQL e incorporamos seus atributos aos documentos no MongoDB.”

“Recebimento depois do compromisso significa atraso. Recebimento no mesmo dia é pontual. A média considera apenas os atrasados. Para consolidar grupos, somamos numeradores e denominadores antes de calcular a taxa.”

“A carga usa uma coleção temporária. Somente depois da transformação e das conferências ela substitui a coleção publicada. Isso evita misturar dados de execuções diferentes. A validação calcula as medidas independentemente no SQL e confere chaves, atributos e agrupamentos.”

## Demonstração

Abra os arquivos e páginas antes de começar. Não gaste o tempo baixando pacotes ou inicializando serviços. Mostre uma linha real da origem, um documento real, o resumo da validação e os gráficos. Reserve a maior parte do tempo para interpretar resultados.

Use os números de **artifacts/ANALISE_GERENCIAL.md** e **docs/RESULTADOS.md**, quando gerados. Explique a diferença entre percentual de atraso e número de itens atrasados. Compare fornecedores com seus volumes. Apresente ações como hipóteses de investigação, sem afirmar causalidade.

## Se o Redash estiver indisponível

Informe a restrição de virtualização da VM. Demonstre MySQL, MongoDB, os pipelines e as evidências disponíveis. Mostre a apresentação e os CSVs como apoio e declare que o dashboard Redash requer execução em outro ambiente. Essa alternativa demonstra parte do trabalho, mas deixa o requisito específico do Redash pendente.

## Perguntas esperadas

- Por que embedding? Simplifica as consultas do recorte e dispensa lookup, ao custo de repetir atributos e exigir recarga quando mudam.
- Por que MySQL se o gerador usa DuckDB? DuckDB fornece dbgen para preparar a origem. A ETL lê e valida o TPC-H persistido no MySQL.
- A taxa é por pedido? Não, é por item. Uma taxa por pedido exigiria outra agregação e definição de pedido atrasado.
- A modalidade causa o atraso? Os dados mostram associação. Rotas, mix e compromissos podem influenciar os resultados.
- A base pequena representa vendas reais? É uma base sintética de demonstração, sem inferência sobre uma empresa real.
- Todos os itens foram conferidos? Mostre o status e a contagem efetivamente registrados na validação, sem afirmar execução ainda não realizada.
