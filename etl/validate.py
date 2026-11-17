
"""Validação dos indicadores de atraso: MySQL x MongoDB."""

import os
from decimal import Decimal

from dotenv import load_dotenv
import pymysql
from pymongo import MongoClient

load_dotenv()

LIMIT = int(os.getenv("ETL_LIMIT", "10000"))

SQL = """
SELECT
    COUNT(*) AS total,
    SUM(
        CASE
            WHEN l_receiptdate > l_commitdate THEN 1
            ELSE 0
        END
    ) AS atrasadas,
    SUM(
        CASE
            WHEN l_receiptdate > l_commitdate
            THEN DATEDIFF(l_receiptdate, l_commitdate)
            ELSE 0
        END
    ) AS dias_atraso_total
FROM (
    SELECT
        l_receiptdate,
        l_commitdate
    FROM lineitem
    ORDER BY l_orderkey, l_linenumber
    LIMIT %s
) AS amostra
"""


def main():
    sql = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "tpch"),
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=1200,
    )

    mongo = MongoClient(
        os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=5000,
    )

    try:
        with sql.cursor() as cursor:
            cursor.execute(SQL, (LIMIT,))
            origem = cursor.fetchone()

        col = mongo[
            os.getenv("MONGO_DATABASE", "tpch_bi")
        ]["fato_entregas"]

        resultado = list(col.aggregate([
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "atrasadas": {
                        "$sum": {
                            "$cond": [
                                "$entrega.atrasada",
                                1,
                                0
                            ]
                        }
                    },
                    "dias_atraso_total": {
                        "$sum": "$entrega.diasAtraso"
                    }
                }
            }
        ]))

        destino = resultado[0] if resultado else {
            "total": 0,
            "atrasadas": 0,
            "dias_atraso_total": 0,
        }

        total_mysql = int(origem["total"])
        atrasadas_mysql = int(origem["atrasadas"] or 0)
        dias_mysql = int(origem["dias_atraso_total"] or 0)

        total_mongo = int(destino["total"])
        atrasadas_mongo = int(destino["atrasadas"])
        dias_mongo = int(destino["dias_atraso_total"])

        taxa_mysql = (
            atrasadas_mysql / total_mysql * 100
            if total_mysql else 0
        )

        taxa_mongo = (
            atrasadas_mongo / total_mongo * 100
            if total_mongo else 0
        )

        media_mysql = (
            dias_mysql / atrasadas_mysql
            if atrasadas_mysql else 0
        )

        media_mongo = (
            dias_mongo / atrasadas_mongo
            if atrasadas_mongo else 0
        )

        print("\n========== VALIDAÇÃO ==========")

        print("\nMYSQL (ORIGEM)")
        print(f"Total de itens: {total_mysql}")
        print(f"Itens atrasados: {atrasadas_mysql}")
        print(f"Taxa de atraso: {taxa_mysql:.2f}%")
        print(f"Média de dias de atraso: {media_mysql:.2f}")

        print("\nMONGODB (DESTINO)")
        print(f"Total de itens: {total_mongo}")
        print(f"Itens atrasados: {atrasadas_mongo}")
        print(f"Taxa de atraso: {taxa_mongo:.2f}%")
        print(f"Média de dias de atraso: {media_mongo:.2f}")

        print("\nCOMPARAÇÃO")
        print(f"Diferença na taxa: {abs(taxa_mysql - taxa_mongo):.4f} pontos percentuais")
        print(f"Diferença na média: {abs(media_mysql - media_mongo):.4f} dias")

        ok = (
            total_mysql == total_mongo
            and atrasadas_mysql == atrasadas_mongo
            and dias_mysql == dias_mongo
        )

        print("\nVALIDAÇÃO:", "OK" if ok else "DIVERGÊNCIA")

        if not ok:
            raise SystemExit(1)

    finally:
        sql.close()
        mongo.close()


if __name__ == "__main__":
    main()
