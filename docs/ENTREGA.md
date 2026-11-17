# Estado da entrega

## Material implementado

- MySQL no Compose e alternativa portátil nativa para Windows sem virtualização.
- Geração reproduzível TPC-H SF 0.01, persistida em oito tabelas MySQL.
- ETL específica de atrasos, qualidade de dados e publicação atômica no MongoDB.
- Validação exata por item e conferência dos indicadores por mês/modalidade.
- Seis consultas de atrasos, cadastro automático de dashboard e instruções manuais.
- Exportação CSV, JSON e análise gerencial a partir dos resultados processados.
- Modelo, regras de negócio e roteiro de apresentação de 10 minutos.

## Evidências de execução

O registro da execução real está em docs/RESULTADOS.md: 60.175 itens conferidos, zero divergências e os seis pipelines executados no MongoDB. Os JSONs em artifacts/ são as evidências verificáveis. Arquivos ausentes indicam etapas ainda não executadas. Testes unitários e validação de sintaxe não substituem a conferência real dos bancos.

## Pendência de ambiente

O usuário informou que esta VM está com virtualização desativada. Docker Desktop não pode executar os containers Redash neste ambiente. O cadastro real, a conferência visual e a captura do dashboard Redash precisam ocorrer em outro computador com containers habilitados. A implementação e as consultas estão preparadas para essa execução. Não há declaração de dashboard Redash já validado nesta VM.


## Verificações concluídas

Nove testes de negócio e proteção de carga passaram. Os arquivos Python, JSON e PowerShell passaram pelas verificações de sintaxe aplicáveis. A configuração Compose passou por docker compose config --quiet, sem execução dos containers. O seed foi reexecutado e preservou a base. O teste real de redução de recorte passou em banco temporário separado.
