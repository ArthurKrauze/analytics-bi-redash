# Equipe 12 — Atrasos nas entregas

Projeto de Data Analytics e BI para identificar onde concentrar a investigação de falhas logísticas. O indicador principal é a **taxa de atraso de itens de pedido**.

```text
TPC-H dbgen (DuckDB, SF 0.01)
           | preparação inicial da origem
           v
MySQL: oito tabelas TPC-H
           | ETL Python, integração e qualidade
           v
MongoDB: tpch_bi.fato_entregas
           | Aggregation Framework
           v
Redash: indicadores, gráficos e tabela de fornecedores
```

O DuckDB gera somente a base de origem. A extração da ETL e a validação usam **MySQL**, conforme o enunciado. A versão pequena contém toda a base gerada nessa escala, sem cortar os primeiros 10 mil itens.

## Execução nesta VM, sem virtualização

Requisitos: Windows x64, Python 3.11+ (`py`), conexão à internet para os downloads iniciais e aproximadamente 3 GB livres. MySQL e MongoDB usam distribuições portáteis oficiais e não registram serviços do Windows. Os bancos escutam somente em localhost.

```powershell
cd E:\pucpr\database\analytics-bi-redash
.\scripts\run-native.ps1
```

O script configura Python e `.env`, baixa os bancos para `.runtime/`, gera TPC-H no MySQL, executa a ETL, valida e exporta as evidências. Os arquivos `.env`, `.venv/` e `.runtime/` não entram no Git.

Se a política do PowerShell impedir scripts, execute os módulos individualmente:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/configure.py
.\.venv\Scripts\python.exe -m etl.native start
.\.venv\Scripts\python.exe -m etl.seed
.\.venv\Scripts\python.exe -m etl.migrate
.\.venv\Scripts\python.exe -m etl.validate
.\.venv\Scripts\python.exe -m etl.evidence
```

O modo nativo permite comprovar MySQL, MongoDB e os indicadores. **O Redash continua exigindo um ambiente compatível.** Nesta VM sem virtualização, a criação efetiva do dashboard Redash fica pendente. Os resultados CSV e a apresentação são apoio à demonstração, sem substituir esse requisito.

```powershell
.\.venv\Scripts\python.exe -m etl.native status
# Encerramento normal dos dois bancos deste projeto:
.\.venv\Scripts\python.exe -m etl.native stop
```

Os dados ficam em `.runtime/mysql-data` e `.runtime/mongo-data`. Reexecutar o seed preserva a base existente quando o manifesto e as contagens conferem. Uma base preenchida sem manifesto não é sobrescrita.

## Execução completa em computador com Docker

Copie o projeto para um Windows com Docker Desktop e virtualização habilitada. Os downloads iniciais precisam de internet. Não execute os dois modos simultaneamente nas mesmas portas.

```powershell
.\scripts\preflight.ps1
.\scripts\run-project.ps1
```

O script inclui MySQL, MongoDB, PostgreSQL, Redis e Redash, inicializa os metadados quando necessário e cria/reutiliza as consultas e visualizações por API. A criação do administrador ocorre localmente. Login e senha ficam no `.env`, sem exibição nos logs ou evidências. A URL final fica em `artifacts/redash.json`.

Portas: MySQL `3307`, MongoDB `27017`, Redash `5000`. No Redash, o endereço do MongoDB é `mongodb://mongodb:27017`, banco `tpch_bi`. PostgreSQL armazena apenas os metadados do Redash.

As imagens conservam a compatibilidade com a referência didática: MySQL 8.0, MongoDB 6.0, Redash 10.1.0.b50633, PostgreSQL 13 e Redis 7. O modo nativo usa MySQL 8.0.44 e MongoDB 6.0.26.

As versões Python efetivamente testadas estão fixadas em `requirements-lock.txt`; o setup utiliza esse arquivo. `requirements.txt` documenta as dependências diretas.

## Indicadores e consultas

| Arquivo em queries/ | Uso |
|---|---|
| 01_resumo_atrasos.json | Total, atrasados, taxa e média entre atrasados |
| 02_atrasos_modalidade.json | Gráfico principal: taxa por modalidade (%) |
| 03_evolucao_mensal.json | Complemento: taxa por mês da data comprometida (%) |
| 04_fornecedores.json | Tabela com volume, atrasados, taxa e gravidade |
| 05_faixas_atraso.json | Distribuição em dias corridos |
| 06_atrasos_regiao_cliente.json | Comparação por região do cliente |

Todas consultam `fato_entregas`. O JSON do Redash usa lista `name/direction` no `$sort`. Para executar diretamente pelo PyMongo, `etl.analytics.mongo_pipeline` converte essa etapa para o formato nativo. As consultas também podem ser cadastradas manualmente conforme [docs/DASHBOARD.md](docs/DASHBOARD.md).

## Regras essenciais

- Grão: uma linha de `lineitem`, chave `(l_orderkey, l_linenumber)`.
- Atraso: `l_receiptdate > l_commitdate`. Recebimento no compromisso é pontual.
- Dias de atraso: `max(recebimento - compromisso, 0)`, em dias corridos.
- Taxa: itens atrasados / total de itens × 100. Não é uma taxa por pedido nem ponderada por unidades.
- Média: soma dos dias / número de itens atrasados. Sem atrasados, média nula, exibida como não aplicável.
- Mês: data comprometida, que representa a coorte de compromissos a avaliar.
- Embedding: atributos dimensionais dentro de cada documento, sem necessidade de `$lookup` nas consultas principais.

## Reexecução e qualidade

A ETL lê um snapshot consistente do MySQL. Cada carga monta uma coleção temporária, verifica a quantidade e cria índices. Somente então substitui atomicamente `fato_entregas`. Uma carga inválida preserva a coleção publicada. A operação substitui o recorte analítico completo e evita resíduos de limites anteriores. Não execute seed, ETL ou validação simultaneamente.

`ETL_LIMIT=0` usa todos os itens da base. Um valor positivo seleciona os primeiros itens em ordem de pedido/item. Esse recorte é determinístico e não representa uma amostra aleatória. ETL e validação usam a mesma seleção. Para a entrega, recomenda-se conservar o valor zero na escala pequena.

A validação confere chaves e **todos os atributos transformados**, além de contagens e medidas gerais, por modalidade e por mês. Ela reprova base vazia, documentos ausentes/excedentes, diferenças de dimensão e medidas incorretas. As regras de qualidade rejeitam datas inválidas, recebimento anterior ao envio, quantidade inválida e relacionamentos órfãos. Uma data comprometida anterior ao envio pode existir no TPC-H e não é descartada automaticamente.

```powershell
.\.venv\Scripts\python.exe scripts/validate-files.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Exige os dois bancos em execução:
.\.venv\Scripts\python.exe -m etl.validate
```

## Evidências e apresentação

Execução verificada em 17/11/2026: **60.175 itens**, **37.897 atrasados**, taxa de **62,98%** e média de **41,59 dias entre atrasados**, com zero divergências entre os bancos. Consulte [os resultados completos](docs/RESULTADOS.md).

Abra `artifacts/PAINEL_OFFLINE.html` no navegador para apresentar os gráficos sem depender de serviços web. O material editável fica em `apresentacao/Equipe12-Atrasos.pptx`. O painel é apoio offline e não substitui o dashboard Redash pendente.

| Arquivo gerado | Conteúdo |
|---|---|
| artifacts/origem.json | Gerador, escala e contagens da origem |
| artifacts/etl.json | Execução e quantidade publicada |
| artifacts/validacao.json | Correspondência exata entre MySQL e MongoDB |
| artifacts/resultados.json e *.csv | Saídas reais dos pipelines |
| artifacts/documento_exemplo.json | Exemplo real da representação documental |
| artifacts/ANALISE_GERENCIAL.md | Interpretação gerada com os dados processados |
| artifacts/PAINEL_OFFLINE.html | Gráficos offline com resultados processados |
| artifacts/redash.json | URL do dashboard, somente após execução no Redash |

Materiais: [problema e métricas](docs/PROJETO.md), [modelo dimensional](docs/MODELO.md), [dashboard](docs/DASHBOARD.md), [roteiro de 10 minutos](docs/APRESENTACAO.md) e [estado da entrega](docs/ENTREGA.md).

## Preservar o ambiente Docker

```powershell
docker compose stop
docker compose start
# Remove somente contêineres, preservando volumes:
docker compose down
```

Não use `docker compose down -v` para uma pausa: esse comando apaga os volumes. Para trocar de ambiente, gere `.env` novamente com setup.ps1 ou conserve o arquivo local correspondente ao banco. Não troque senhas de uma instância já inicializada apenas editando o `.env`.

## Referências

- [Laboratório de referência](https://devlabs.escdodev.com.br/labs/tpch-mongodb-bi)
- [TPC-H, especificação oficial](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v2.17.2.pdf), definição de itens recebidos após a data comprometida
- [DuckDB, extensão TPC-H](https://duckdb.org/docs/stable/core_extensions/tpch), geração com dbgen
- [MySQL, distribuição ZIP para Windows](https://dev.mysql.com/doc/refman/8.0/en/windows-install-archive.html)
- [MongoDB, instalação ZIP para Windows](https://www.mongodb.com/docs/v6.0/tutorial/install-mongodb-on-windows-zip/)
- [Redash, consultas MongoDB](https://redash.io/help/data-sources/querying/mongodb/)
