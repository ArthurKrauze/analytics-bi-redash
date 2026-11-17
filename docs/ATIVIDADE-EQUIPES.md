# Atendimento ao enunciado

Este projeto desenvolve o Desafio 12, com foco na taxa de atraso de itens e na decisão de priorizar investigações logísticas.

| Etapa | Evidência no projeto |
|---|---|
| Investigação gerencial | docs/PROJETO.md |
| Modelo dimensional | docs/MODELO.md, grão e dimensões |
| MongoDB | etl/model.py e documento_exemplo.json real |
| ETL reproduzível | scripts/run-native.ps1 ou scripts/run-project.ps1, etl/seed.py e etl/migrate.py |
| Validação | etl/validate.py e artifacts/validacao.json |
| Consultas analíticas | Seis pipelines em queries/ |
| Dashboard Redash | etl/redash_setup.py, docs/DASHBOARD.md e evidência real após cadastro |
| Análise e apresentação | artifacts/ANALISE_GERENCIAL.md, docs/APRESENTACAO.md e material da apresentação |

R1: integração, grão, dimensões, regras de qualidade, ETL e validação. R2: indicadores pertinentes, gráfico principal e visualizações complementares no Redash. R3: interpretação apoiada em números efetivamente processados, com volumes e limites explicitados.

A implantação do Redash depende de um ambiente compatível com containers. A VM atual, sem virtualização, utiliza MySQL e MongoDB nativos. Ver docs/ENTREGA.md para distinguir o que foi executado do que permanece pendente.
