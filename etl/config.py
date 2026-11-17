"""Configuração única, independente do diretório de execução."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
COLLECTION = "fato_entregas"


def integer(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} deve ser um inteiro.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} deve estar entre {minimum} e {maximum}.")
    return value


def scope():
    limit = integer("ETL_LIMIT", 0, 0, 1000000)
    return {"limite": limit, "criterio": "Todos os itens" if limit == 0
            else "Primeiros itens por l_orderkey e l_linenumber"}


def mysql_connection(stream=False):
    import pymysql
    password = os.getenv("MYSQL_PASSWORD")
    if not password or password == "ALTERAR":
        raise ValueError("Configure MYSQL_PASSWORD no .env ou execute scripts/setup.ps1.")
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=integer("MYSQL_PORT", 3307, 1, 65535),
        user=os.getenv("MYSQL_USER", "tpch"), password=password,
        database=os.getenv("MYSQL_DATABASE", "tpch"), charset="utf8mb4",
        cursorclass=pymysql.cursors.SSDictCursor if stream else pymysql.cursors.DictCursor,
        connect_timeout=10, read_timeout=1200,
    )


def mongo_client():
    from pymongo import MongoClient
    return MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                       serverSelectionTimeoutMS=10000)


def mongo_database(client):
    return client[os.getenv("MONGO_DATABASE", "tpch_bi")]


def artifacts_dir():
    path = ROOT / "artifacts"
    path.mkdir(exist_ok=True)
    return path
