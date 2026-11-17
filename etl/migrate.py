
"""ETL TPC-H MySQL -> MongoDB para análise de atrasos nas entregas.

Grão: um documento por item de pedido (lineitem).
Execução: python -m etl.migrate
"""

import os
from datetime import date, datetime, time

from dotenv import load_dotenv
import pymysql
from pymongo import MongoClient, ReplaceOne

load_dotenv()

SQL = """

SELECT
    l.l_orderkey,
    l.l_linenumber,
    l.l_shipdate,
    l.l_commitdate,
    l.l_receiptdate,
    l.l_shipmode,
    l.l_quantity,

    l.l_suppkey,
    s.s_name AS fornecedor_nome,
    sn.n_name AS fornecedor_nacao,
    sr.r_name AS fornecedor_regiao,

    l.l_partkey,
    p.p_brand,
    p.p_type,

    o.o_custkey,
    c.c_mktsegment,
    cn.n_name AS cliente_nacao,
    cr.r_name AS cliente_regiao

FROM (
    SELECT *
    FROM lineitem
    ORDER BY l_orderkey, l_linenumber
    LIMIT %s
) AS l

JOIN orders o ON o.o_orderkey = l.l_orderkey

JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation cn ON cn.n_nationkey = c.c_nationkey
JOIN region cr ON cr.r_regionkey = cn.n_regionkey

JOIN supplier s ON s.s_suppkey = l.l_suppkey
JOIN nation sn ON sn.n_nationkey = s.s_nationkey
JOIN region sr ON sr.r_regionkey = sn.n_regionkey

JOIN part p ON p.p_partkey = l.l_partkey

ORDER BY l.l_orderkey, l.l_linenumber
"""



def to_datetime(value):
    """Converte datas do MySQL para datetime aceito pelo MongoDB."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, time.min)

    return None


def make_document(row):
    """Transforma uma linha do MySQL em um documento MongoDB."""

    data_envio = to_datetime(row["l_shipdate"])
    data_comprometida = to_datetime(row["l_commitdate"])
    data_recebimento = to_datetime(row["l_receiptdate"])

    dias_atraso = max(
        (data_recebimento.date() - data_comprometida.date()).days,
        0
    )

    atrasada = dias_atraso > 0

    return {
        "_id": f'{row["l_orderkey"]}:{row["l_linenumber"]}',

        "pedidoId": int(row["l_orderkey"]),
        "numeroItem": int(row["l_linenumber"]),

        "datas": {
            "envio": data_envio,
            "comprometida": data_comprometida,
            "recebimento": data_recebimento,
        },

        "entrega": {
            "modalidade": row["l_shipmode"],
            "atrasada": atrasada,
            "diasAtraso": dias_atraso,
        },

        "cliente": {
            "id": int(row["o_custkey"]),
            "segmento": row["c_mktsegment"],
            "nacao": row["cliente_nacao"],
            "regiao": row["cliente_regiao"],
        },

        "fornecedor": {
            "id": int(row["l_suppkey"]),
            "nome": row["fornecedor_nome"],
            "nacao": row["fornecedor_nacao"],
            "regiao": row["fornecedor_regiao"],
        },

        "produto": {
            "id": int(row["l_partkey"]),
            "marca": row["p_brand"],
            "tipo": row["p_type"],
        },

        "quantidade": float(row["l_quantity"]),
    }


def main():
    limit = int(os.getenv("ETL_LIMIT", "10000"))
    batch = int(os.getenv("ETL_BATCH", "1000"))

    if not 1 <= limit <= 1000000 or not 1 <= batch <= 10000:
        raise SystemExit(
            "ETL_LIMIT deve ser 1..1000000 e ETL_BATCH 1..10000."
        )

    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "tpch"),
        cursorclass=pymysql.cursors.SSDictCursor,
        charset="utf8mb4",
        read_timeout=1200,
    )

    client = MongoClient(
        os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=5000,
    )

    col = client[
        os.getenv("MONGO_DATABASE", "tpch_bi")
    ]["fato_entregas"]

    total = 0

    try:
        # Confirma que o MongoDB está acessível.
        client.admin.command("ping")

        with conn.cursor() as cursor:
            cursor.execute(SQL, (limit,))

            while True:
                rows = cursor.fetchmany(batch)

                if not rows:
                    break

                documents = [make_document(row) for row in rows]

                operations = [
                    ReplaceOne(
                        {"_id": document["_id"]},
                        document,
                        upsert=True,
                    )
                    for document in documents
                ]

                col.bulk_write(operations, ordered=False)

                total += len(documents)
                print(f"Entregas carregadas/atualizadas: {total}")

        # Índices para facilitar as consultas analíticas.
        col.create_index("datas.recebimento")
        col.create_index("entrega.atrasada")
        col.create_index("entrega.modalidade")
        col.create_index("fornecedor.id")
        col.create_index("cliente.regiao")

        print("\nETL FINALIZADA COM SUCESSO!")
        print(f"Documentos processados: {total}")
        print(f"Coleção: {col.full_name}")

    finally:
        conn.close()
        client.close()


if __name__ == "__main__":
    main()
