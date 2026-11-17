"""Carga integral do recorte em staging e publicação atômica no MongoDB."""
import json
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4

from etl.config import (COLLECTION, artifacts_dir, integer, mongo_client,
                        mongo_database, mysql_connection, scope)
from etl.model import make_document, to_datetime
from etl.source import extraction_sql, sampled_lineitems


def load_snapshot(conn, database, limit, batch):
    run_id = uuid4().hex
    staging_name = f"_carga_entregas_{run_id}"
    staging = database[staging_name]
    published = False
    started = datetime.now(timezone.utc)
    try:
        database.create_collection(staging_name)
        sample, params = sampled_lineitems(limit)
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM ({sample}) AS recorte", params)
            expected = int(cursor.fetchone()["total"])
        if not expected:
            raise ValueError("Origem vazia: a coleção publicada foi preservada.")
        sql, params = extraction_sql(limit)
        total = 0
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            while rows := cursor.fetchmany(batch):
                staging.insert_many([make_document(row) for row in rows], ordered=True)
                total += len(rows)
                print(f"Itens preparados: {total}", flush=True)
        if total != expected or staging.count_documents({}) != expected:
            raise ValueError("Quantidade extraída diverge do recorte de origem.")
        staging.create_index("datas.comprometida")
        staging.create_index("entrega.modalidade")
        staging.create_index("fornecedor.id")
        staging.create_index("cliente.regiao")
        # A troca na mesma base é atômica e substitui somente a fato deste projeto.
        staging.rename(COLLECTION, dropTarget=True)
        published = True
        report = {
            "execucao": run_id, "inicio_utc": started.isoformat(),
            "fim_utc": datetime.now(timezone.utc).isoformat(),
            "colecao": COLLECTION, "itens": total, "escopo": scope(),
            "estrategia": "staging e troca atômica da coleção",
        }
        database.etl_execucoes.insert_one(dict(report))
        return report
    finally:
        if not published:
            database.drop_collection(staging_name)


def main():
    recorte = scope()
    batch = integer("ETL_BATCH", 1000, 1, 10000)
    with closing(mysql_connection(stream=True)) as conn, mongo_client() as client:
        client.admin.command("ping")
        with conn.cursor() as cursor:
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        report = load_snapshot(conn, mongo_database(client), recorte["limite"], batch)
    path = artifacts_dir() / "etl.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ETL concluída: {report['itens']} itens. Evidência: {path}")


if __name__ == "__main__":
    main()
