# Dashboard Redash

Nome: **Equipe 12 - Atrasos nas entregas**.

## Ambiente e cadastro automático

Em computador com Docker, `scripts/run-project.ps1` prepara toda a solução. Para refazer apenas o cadastro após inicializar Redash e carregar os dados:

```powershell
.\.venv\Scripts\python.exe -m etl.redash_setup
```

O script cria/reutiliza o administrador configurado no `.env`, a fonte MongoDB, seis consultas, visualizações e o dashboard. A senha não é alterada quando o administrador já existe. Se um objeto for renomeado manualmente, o cadastro automático pode criar outro objeto com o nome esperado. O script não apaga dashboards de terceiros.

## Cadastro manual

1. Abra http://localhost:5000 e configure o administrador.
2. Settings / Data Sources / New / MongoDB.
3. Connection String: `mongodb://mongodb:27017`. Database Name: `tpch_bi`.
4. Teste a conexão. Em Create / Query, cole cada JSON integral de queries/ e execute.
5. Salve as consultas e as visualizações da tabela abaixo.
6. Crie o dashboard, adicione os widgets e confira títulos e unidades.

| Consulta | Visualização | X | Y / medidas |
|---|---|---|---|
| 01_resumo_atrasos | Cartões e tabela | Uma linha | total_itens, taxa_atraso_percentual, media_dias_atraso |
| 02_atrasos_modalidade | Barras | modalidade | taxa_atraso_percentual (%) |
| 03_evolucao_mensal | Linha | mes_compromisso, ordem crescente | taxa_atraso_percentual (%) |
| 04_fornecedores | Tabela | fornecedor | total_itens, itens_atrasados, taxa_atraso_percentual, media_dias_atraso |
| 05_faixas_atraso | Barras | faixa | total_itens (itens) |
| 06_atrasos_regiao_cliente | Barras | regiao_cliente | taxa_atraso_percentual (%) |

As taxas já estão em escala 0–100. Não aplique um formato que multiplique por 100 novamente. Use duas casas decimais para taxas e médias. Para cartões, indique `%` e `dias` nos títulos. Preserve valores nulos como não aplicáveis, sem transformá-los em atraso zero.

## Leitura sugerida

O gráfico principal compara taxas entre modalidades. A linha mensal permite investigar persistência ao longo do tempo. A tabela de fornecedores acrescenta volume e gravidade e evita tomar decisão com base em taxa isolada de amostras pequenas. As faixas distinguem pontualidade e atrasos longos. A região é a do cliente, não a do fornecedor.

As consultas usam todos os documentos publicados. O dashboard inicial não inclui filtros de período: todos os widgets compartilham o mesmo escopo da ETL. Se adicionar filtros, aplique-os a todas as consultas e à validação comparável.

## Restrição desta VM

Sem virtualização, Docker Desktop não executa os containers Redash. Os bancos podem funcionar em modo nativo no Windows. O projeto fornece os JSONs e o cadastro automático para um ambiente compatível, mas a existência de um dashboard Redash deve ser comprovada por execução e captura reais. Não apresente uma prévia offline como se fosse o Redash.
