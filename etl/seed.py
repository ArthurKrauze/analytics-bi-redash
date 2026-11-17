"""Gera TPC-H com dbgen/DuckDB e carrega as oito tabelas no MySQL."""
import json
import os
from contextlib import closing
from decimal import Decimal
from datetime import datetime, timezone

from etl.config import ROOT, artifacts_dir, mysql_connection

TABLES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")


def main():
    import duckdb
    scale = Decimal(os.getenv("TPCH_SCALE_FACTOR", "0.01"))
    if not scale.is_finite() or not Decimal("0.01") <= scale <= Decimal("1"):
        raise ValueError("TPCH_SCALE_FACTOR deve estar entre 0.01 e 1.")
    with closing(mysql_connection()) as mysql:
        with mysql.cursor() as cursor:
            for statement in (ROOT / "sql/tpch_schema.sql").read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    cursor.execute(statement)
            counts = {}
            for table in TABLES:
                cursor.execute(f"SELECT COUNT(*) AS n FROM `{table}`")
                counts[table] = int(cursor.fetchone()["n"])
            cursor.execute("SELECT * FROM _tpch_seed WHERE id=1")
            previous = cursor.fetchone()
            if any(counts.values()):
                if previous and previous["scale_factor"] == str(scale) and json.loads(previous["counts_json"]) == counts:
                    print("TPC-H já carregado, com contagens compatíveis. Dados preservados.")
                    return
                raise ValueError("Há dados existentes/sem manifesto ou de outra escala. Use-os sem seed ou configure uma base nova, sem apagar a atual.")
        with duckdb.connect() as generated:
            generated.execute("INSTALL tpch")
            generated.execute("LOAD tpch")
            generated.execute(f"CALL dbgen(sf={scale})")
            with mysql.cursor() as cursor:
                for table in TABLES:
                    reader = generated.execute(f'SELECT * FROM "{table}"')
                    columns = [column[0] for column in reader.description]
                    column_sql = ",".join(f"`{column}`" for column in columns)
                    insert = f'INSERT INTO `{table}` ({column_sql}) VALUES ({",".join(["%s"] * len(columns))})'
                    count = 0
                    while rows := reader.fetchmany(1000):
                        cursor.executemany(insert, rows)
                        count += len(rows)
                    counts[table] = count
                    print(f"TPC-H {table}: {count}", flush=True)
                cursor.execute("INSERT INTO _tpch_seed (id,scale_factor,generator,counts_json) VALUES (1,%s,%s,%s)",
                               (str(scale), f"DuckDB {duckdb.__version__} / extensão tpch dbgen", json.dumps(counts)))
            mysql.commit()
        report = {"escala": str(scale), "gerador": f"DuckDB {duckdb.__version__}, extensão tpch/dbgen",
                  "origem_etl": "MySQL", "contagens": counts,
                  "gerado_utc": datetime.now(timezone.utc).isoformat()}
        (artifacts_dir() / "origem.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("TPC-H carregado no MySQL. Próximo passo: python -m etl.migrate")


if __name__ == "__main__":
    main()
