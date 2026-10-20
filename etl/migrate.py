"""TPC-H MySQL -> MongoDB, documento por lineitem (grão da fato).
Uso: python -m etl.migrate
"""
import os
from datetime import datetime, time
from decimal import Decimal
from dotenv import load_dotenv
import pymysql
from pymongo import MongoClient, ReplaceOne

load_dotenv()

SQL = """
SELECT
 l.l_orderkey, l.l_linenumber, o.o_orderdate,
 o.o_custkey, c.c_mktsegment,
 cn.n_name AS cliente_nacao, cr.r_name AS cliente_regiao,
 l.l_partkey, p.p_brand, p.p_type,
 l.l_suppkey, sn.n_name AS fornecedor_nacao, sr.r_name AS fornecedor_regiao,
 l.l_quantity, l.l_extendedprice, l.l_discount
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation cn ON cn.n_nationkey = c.c_nationkey
JOIN region cr ON cr.r_regionkey = cn.n_regionkey
JOIN part p ON p.p_partkey = l.l_partkey
JOIN supplier s ON s.s_suppkey = l.l_suppkey
JOIN nation sn ON sn.n_nationkey = s.s_nationkey
JOIN region sr ON sr.r_regionkey = sn.n_regionkey
ORDER BY l.l_orderkey, l.l_linenumber
LIMIT %s
"""

def make_document(row):
    price = Decimal(str(row["l_extendedprice"]))
    discount = Decimal(str(row["l_discount"]))
    net = (price * (1 - discount)).quantize(Decimal("0.01"))
    date = row["o_orderdate"]
    if not isinstance(date, datetime):
        date = datetime.combine(date, time.min)
    return {
        "_id": f'{row["l_orderkey"]}:{row["l_linenumber"]}',
        "pedidoId": int(row["l_orderkey"]),
        "numeroItem": int(row["l_linenumber"]),
        "dataPedido": date,
        "cliente": {
            "id": int(row["o_custkey"]),
            "segmento": row["c_mktsegment"],
            "nacao": row["cliente_nacao"],
            "regiao": row["cliente_regiao"],
        },
        "produto": {
            "id": int(row["l_partkey"]),
            "marca": row["p_brand"],
            "tipo": row["p_type"],
        },
        "fornecedor": {
            "id": int(row["l_suppkey"]),
            "nacao": row["fornecedor_nacao"],
            "regiao": row["fornecedor_regiao"],
        },
        "quantidade": float(row["l_quantity"]),
        "precoBase": float(price),
        "desconto": float(discount),
        "receitaLiquida": float(net),
    }

def main():
    limit = int(os.getenv("ETL_LIMIT", "10000"))
    batch = int(os.getenv("ETL_BATCH", "1000"))
    if not 1 <= limit <= 1000000 or not 1 <= batch <= 10000:
        raise SystemExit("ETL_LIMIT deve ser 1..1000000 e ETL_BATCH 1..10000.")
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "tpch"),
        cursorclass=pymysql.cursors.SSDictCursor,
        charset="utf8mb4",
        read_timeout=240,
    )
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    col = client[os.getenv("MONGO_DATABASE", "tpch_bi")]["fato_vendas"]
    total = 0
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL, (limit,))
            while True:
                rows = cursor.fetchmany(batch)
                if not rows:
                    break
                docs = [make_document(row) for row in rows]
                col.bulk_write(
                    [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in docs],
                    ordered=False,
                )
                total += len(docs)
                print(f"Itens carregados/atualizados: {total}")
        col.create_index("dataPedido")
        col.create_index("cliente.regiao")
        col.create_index("produto.marca")
        print(f"Finalizado: {total} itens | {col.full_name}")
        print("Reexecução atualiza a amostra, mas não exclui documentos antigos.")
    finally:
        conn.close()
        client.close()

if __name__ == "__main__":
    main()
