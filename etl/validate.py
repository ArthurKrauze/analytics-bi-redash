"""Confere os agregados da amostra ETL MySQL x MongoDB.
Uso: python -m etl.validate
"""
import os
from decimal import Decimal
from dotenv import load_dotenv
import pymysql
from pymongo import MongoClient

load_dotenv()
LIMIT = int(os.getenv("ETL_LIMIT", "10000"))
SQL = """
SELECT COUNT(*) AS itens,
       SUM(ROUND(l_extendedprice * (1-l_discount), 2)) AS receita
FROM (
 SELECT l_extendedprice,l_discount
 FROM lineitem
 ORDER BY l_orderkey,l_linenumber
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
    )
    mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    try:
        with sql.cursor() as cur:
            cur.execute(SQL, (LIMIT,))
            origin = cur.fetchone()
        col = mongo[os.getenv("MONGO_DATABASE", "tpch_bi")]["fato_vendas"]
        result = list(col.aggregate([{"$group": {
            "_id": None, "itens": {"$sum": 1},
            "receita": {"$sum": "$receitaLiquida"}
        }}]))
        target = result[0] if result else {"itens": 0, "receita": 0}
        a = Decimal(str(origin["receita"] or 0))
        b = Decimal(str(target["receita"] or 0))
        print(f"MySQL:   itens={origin['itens']} receita={a:.2f}")
        print(f"MongoDB: itens={target['itens']} receita={b:.2f}")
        print(f"Diferença absoluta de receita: {abs(a-b):.4f}")
        ok = origin["itens"] == target["itens"] and abs(a-b) <= Decimal("0.05")
        print("VALIDAÇÃO:", "OK" if ok else "DIVERGÊNCIA")
        if not ok:
            raise SystemExit(1)
    finally:
        sql.close()
        mongo.close()
if __name__ == "__main__":
    main()
