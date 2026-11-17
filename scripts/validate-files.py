"""Valida sintaxe e contratos do projeto sem gerar caches nem acessar bancos."""
import ast
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = {"01_resumo_atrasos.json", "02_atrasos_modalidade.json", "03_evolucao_mensal.json",
            "04_fornecedores.json", "05_faixas_atraso.json", "06_atrasos_regiao_cliente.json"}
for folder in ("etl", "scripts", "tests"):
    for path in sorted((root / folder).glob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print("PY OK:", path.relative_to(root))
paths = list((root / "queries").glob("*.json"))
if {p.name for p in paths} != required:
    raise ValueError("Consultas ausentes ou antigas na pasta queries/.")
for path in sorted(paths):
    query = json.loads(path.read_text(encoding="utf-8"))
    if query.get("collection") != "fato_entregas" or not query.get("aggregate"):
        raise ValueError(f"Consulta incompatível com o ETL: {path.name}")
    for stage in query["aggregate"]:
        if "$sort" in stage and not isinstance(stage["$sort"], list):
            raise ValueError("Redash requer lista de name/direction no $sort.")
    print("JSON OK:", path.name)
print("Validação estática OK. Execute etl.validate para comprovar os dados reais.")
