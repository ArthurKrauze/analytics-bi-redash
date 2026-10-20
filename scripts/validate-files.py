"""Valida estrutura e consultas sem precisar de Docker nem MySQL."""
import json
import pathlib
import py_compile

root = pathlib.Path(__file__).resolve().parents[1]
for name in ("etl/migrate.py", "etl/validate.py"):
    py_compile.compile(str(root / name), doraise=True)
    print("PY OK:", name)
for path in sorted((root / "queries").glob("*.json")):
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert obj["collection"] == "fato_vendas"
    assert isinstance(obj["aggregate"], list)
    for stage in obj["aggregate"]:
        if "$sort" in stage:
            assert isinstance(stage["$sort"], list), "Redash requer array no $sort"
    print("JSON OK:", path.name)
print("Arquivos validados.")
