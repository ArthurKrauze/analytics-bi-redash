# DB L03 — TPC-H, MongoDB e Analytics/BI com Redash

Laboratório didático de **migração de dados e BI**, em Windows/PowerShell:

```text
 MySQL (TPC-H já existente)
   orders + lineitem + customer + part + supplier + nation + region
                    |
            Python ETL (JOIN)
                    |
                    v
     MongoDB: tpch_bi.fato_vendas
                    |
                    v
       Redash: consultas e dashboard
```

O objetivo é criar uma **amostra funcional de 10.000 itens de pedido** e três
visualizações (receita por região do cliente, receita por ano do pedido e
top 10 marcas). A quarta consulta, pedidos distintos por segmento, é um
exercício opcional.

> **Escopo:** ambiente local de ensino, não produção. O projeto não contém
> dados TPC-H nem cria um MySQL. Pressupõe que o aluno já tenha o TPC-H
> carregado em MySQL e que consiga conectá-lo pelo Windows.

## 1. Pré-requisitos

- Windows 10/11, PowerShell, Git, Docker Desktop (Linux containers).
- Python 3.11+ com `py` disponível no PowerShell.
- MySQL com o TPC-H previamente carregado (`orders`, `lineitem`, `customer`,
  `part`, `supplier`, `nation`, `region`).
- Portas **27017** (MongoDB) e **5000** (Redash) disponíveis.
- Memória livre recomendada: **4–8 GB** para o conjunto de contêineres.

Este laboratório foi preparado com Redash `10.1.0.b50633` (versão legada),
MongoDB `6.0`, PostgreSQL `13` e Redis `7`. O fluxo completo **ainda precisa
ser testado no ambiente do professor** antes de ser distribuído à turma.

## 2. Clonar o repositório

```powershell
git clone https://gitlab.com/gilbriatore/2026/database/analytics-bi-redash.git
cd analytics-bi-redash
.\scripts\preflight.ps1
```

Se a política do PowerShell impedir a execução de `.ps1`, os comandos podem
ser executados individualmente; não é necessário mudar a política global.

## 3. Configurar `.env` e Python

```powershell
Copy-Item .env.example .env
notepad .env
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No `.env`, configure o MySQL existente:

| Variável | Exemplo | Descrição |
|---|---|---|
| `MYSQL_HOST` | `127.0.0.1` | Host acessível no Windows |
| `MYSQL_PORT` | `3306` | Porta publicada do MySQL |
| `MYSQL_USER` | `root` | Usuário autorizado |
| `MYSQL_PASSWORD` | *(sua senha)* | Senha local |
| `MYSQL_DATABASE` | `tpch` | Schema com as tabelas TPC-H |
| `ETL_LIMIT` | `10000` | Itens a carregar |
| `ETL_BATCH` | `1000` | Lote de inserção |
| `MONGO_URI` | `mongodb://127.0.0.1:27017` | MongoDB acessível do Windows |

**Gere duas chaves longas diferentes** para `REDASH_COOKIE_SECRET` e
`REDASH_SECRET_KEY`. Exemplo de geração no PowerShell:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
py -c "import secrets; print(secrets.token_hex(32))"
```

Copie cada resultado para a variável correspondente no `.env`.

**Nunca versione `.env`**: o `.gitignore` já o exclui.

## 4. Inicializar MongoDB e Redash

No diretório do repositório:

```powershell
docker compose config
docker compose up -d mongodb postgres redis
docker compose ps
```

**Somente na primeira execução, com o volume de metadados do Redash novo:**

```powershell
docker compose run --rm server create_db
```

Depois:

```powershell
docker compose up -d server worker scheduler
docker compose ps
```

Abra <http://localhost:5000>, aguarde a inicialização e crie o administrador.
O PostgreSQL neste Compose **armazena somente os metadados do Redash**;
não substitui o MySQL de origem.

Se não abrir:

```powershell
docker compose logs --tail 100 server worker scheduler postgres
```

## 5. Executar ETL MySQL → MongoDB

```powershell
.\.venv\Scripts\python.exe -m etl.migrate
```

O ETL:
1. Consulta a amostra no MySQL com `JOIN`s e `ORDER BY`.
2. Define o **grão**: um item de pedido (`l_orderkey` + `l_linenumber`).
3. Calcula `receitaLiquida = l_extendedprice * (1 - l_discount)`.
4. Insere/atualiza `tpch_bi.fato_vendas` em lotes usando `upsert`.
5. Cria índices didáticos para data, região do cliente e marca.

A implementação física usa **dimensões incorporadas (embedding)**.
O modelo estrela é **conceitual**, não quatro coleções `dim_*` obrigatórias.
Veja [docs/MODELO.md](docs/MODELO.md).

**Limitação:** os primeiros 10 mil itens ordenados por pedido não formam
uma amostra representativa de toda a base. Não use o dashboard para fazer
inferências estatísticas sobre todas as vendas TPC-H.

## 6. Verificar carga

```powershell
docker compose exec mongodb mongosh tpch_bi --eval 'db.fato_vendas.countDocuments({})'
docker compose exec mongodb mongosh tpch_bi --eval 'printjson(db.fato_vendas.findOne())'
```

Resultado esperado em uma coleção vazia: **10.000 documentos**.

Execute a validação cruzada:

```powershell
.\.venv\Scripts\python.exe -m etl.validate
```

O script compara **quantidade de itens** e **soma da receita líquida** com
a mesma amostra no MySQL. Uma diferença maior que R$ 0,05 indica
divergência. Em TPC-H os valores são sintéticos; "R$" é apenas uma unidade
de apresentação escolhida para o exercício, não moeda nativa do benchmark.

**Reexecução:** o ETL atualiza os documentos com o mesmo `_id`, mas não
remove registros de uma execução anterior com limite maior. Se for
necessário recomeçar com uma coleção limpa (APAGA SOMENTE a fato do lab):

```powershell
docker compose exec mongodb mongosh tpch_bi --eval 'db.fato_vendas.drop()'
.\.venv\Scripts\python.exe -m etl.migrate
.\.venv\Scripts\python.exe -m etl.validate
```

## 7. Configurar MongoDB no Redash

1. Acesse <http://localhost:5000>.
2. Vá a **Settings → Data Sources → New Data Source → MongoDB**.
3. Nome: `TPC-H MongoDB`.
4. **Connection String:** `mongodb://mongodb:27017/tpch_bi`.
5. **DB Name:** `tpch_bi` (campo separado, quando disponível).
6. **Test Connection** e **Save**.

O hostname `mongodb` é o nome do serviço na rede Docker.
`localhost` **não** aponta para MongoDB a partir do contêiner Redash.

A sintaxe de consultas MongoDB do Redash é JSON, com chaves `collection`
e `aggregate`. O `$sort` do Redash usa **array de pares
`name`/`direction`**, diferente do pipeline `mongosh` convencional.
As consultas em `queries/` já seguem esse formato.

## 8. Consultas e visualizações

No Redash: **Create → New Query**, selecione `TPC-H MongoDB`,
cole o conteúdo **integral** do arquivo JSON correspondente, execute e salve.

| Arquivo | Visualização sugerida | Eixo X | Eixo Y |
|---|---|---|---|
| `queries/01_receita_regiao_cliente.json` | Barras | `regiao` | `receita` |
| `queries/02_receita_ano_pedido.json` | Linha | `ano` | `receita` |
| `queries/03_top_marcas.json` | Barras | `marca` | `receita` |
| `queries/04_pedidos_distintos_por_segmento.json` | Barras (opcional) | `segmento` | `pedidos` |

Para cada consulta: **New Visualization → Save**.
Depois: **Create → New Dashboard**, nome
`TPC-H — Analytics e BI`, **Add Widget** para incluir os três gráficos.

**Atenção:** a região da consulta 01 é a **região do cliente**,
não a do fornecedor. Pedidos distintos exigem desduplicar `pedidoId`
porque a fato tem uma linha por item.

## 9. Encerramento e trabalho das equipes

Perguntas para discussão:
- Qual é o grão da fato e por que isso importa?
- Por que o protótipo usa embedding e não referencing?
- Quando `$lookup` e `$unwind` seriam necessários?
- Como evitar contar um pedido várias vezes?
- Como mudar o ETL para obter uma amostra representativa?
- Quais consultas e dimensões seriam necessárias para outros KPIs?

Cada equipe deverá **pesquisar, desenhar, implementar e validar seu próprio
recorte analítico**. O protótipo não é a solução obrigatória do TDE.
Veja [docs/ATIVIDADE-EQUIPES.md](docs/ATIVIDADE-EQUIPES.md).

## 10. Encerrar sem perder os dados

```powershell
docker compose stop
docker compose start
# Remover contêineres, preservando volumes:
docker compose down
```

**Não execute `docker compose down -v`** se quiser preservar os dados do
MongoDB e os usuários/dashboards do Redash.

## Solução de problemas

| Sintoma | Verificação |
|---|---|
| `Access denied` no MySQL | Usuário, senha, privilégios, `.env` |
| `Connection refused` no MySQL | Host/porta publicada no Docker do MySQL |
| Redash não abre | `docker compose logs --tail 100 server` |
| Falha em `create_db` | Espere PostgreSQL saudável; verifique `docker compose ps` |
| Redash não acessa MongoDB | Use hostname `mongodb` e DB Name `tpch_bi` |
| Portas ocupadas | `docker ps` e mapeamentos em `compose.yaml` |
| Quantidade incorreta | Limpe somente a coleção piloto e refaça a carga |
| `ETL_LIMIT` alterado | A validação supõe coleção compatível com o limite atual |
| Dashboard vazio | Execute queries e confira documentos/intervalo temporal |

## Arquivos do repositório

```text
analytics-bi-redash/
├── README.md
├── .gitignore
├── .env.example
├── compose.yaml
├── requirements.txt
├── etl/
│   ├── __init__.py
│   ├── migrate.py
│   └── validate.py
├── queries/
│   ├── 01_receita_regiao_cliente.json
│   ├── 02_receita_ano_pedido.json
│   ├── 03_top_marcas.json
│   └── 04_pedidos_distintos_por_segmento.json
├── scripts/
│   ├── preflight.ps1
│   ├── setup.ps1
│   └── validate-files.py
└── docs/
    ├── MODELO.md
    └── ATIVIDADE-EQUIPES.md
```

## Validação estática do projeto

```powershell
py scripts/validate-files.py
docker compose config
```

A primeira valida sintaxe Python e JSON das consultas; a segunda verifica
a configuração Compose (requer `.env`). **Essas verificações não substituem
o teste integrado com MySQL, MongoDB e Redash**.

## Referências

- [Redash — MongoDB Querying](https://redash.io/help/data-sources/querying/mongodb/)
- [Redash — Open Source Setup](https://redash.io/help/open-source/setup/)
- [TPC-H — TPC Benchmark H](https://www.tpc.org/tpch/)
