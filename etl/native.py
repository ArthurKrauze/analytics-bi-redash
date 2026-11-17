"""MySQL e MongoDB portáteis no Windows, sem Docker, serviço ou virtualização."""
import argparse
import json
import os
import re
import socket
import subprocess
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from etl.config import ROOT, integer

PACKAGES = {
    "mysql": ("mysql-8.0.44-winx64", "https://cdn.mysql.com/archives/mysql-8.0/mysql-8.0.44-winx64.zip"),
    "mongodb": ("mongodb-win32-x86_64-windows-6.0.26", "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-6.0.26.zip"),
}


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def install(runtime, kind):
    name, url = PACKAGES[kind]
    executable = "mysqld.exe" if kind == "mysql" else "mongod.exe"
    matches = list(runtime.glob(f"*/bin/{executable}"))
    if matches:
        return matches[0]
    archive = runtime / f"{kind}.zip"
    if not archive.exists():
        partial = archive.with_suffix(".download")
        print(f"Baixando {kind} do distribuidor oficial...", flush=True)
        urllib.request.urlretrieve(url, partial)
        partial.replace(archive)
    print(f"Extraindo {kind}...", flush=True)
    with zipfile.ZipFile(archive) as package:
        # Recusa caminhos fora da pasta de runtime.
        for member in package.infolist():
            if not (runtime / member.filename).resolve().is_relative_to(runtime.resolve()):
                raise ValueError("Caminho inválido no pacote.")
        package.extractall(runtime)
    matches = list(runtime.glob(f"*/bin/{executable}"))
    if len(matches) != 1:
        raise ValueError(f"Executável {executable} não encontrado no pacote oficial.")
    return matches[0]


def wait(port, process):
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"Banco encerrou ao iniciar. Confira os logs em .runtime/. Código {process.returncode}.")
        if listening(port):
            return
        time.sleep(1)
    raise TimeoutError(f"Banco não respondeu na porta {port}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop"], nargs="?", default="start")
    parser.add_argument("--runtime", type=Path, default=ROOT / ".runtime")
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    mysql_port = integer("MYSQL_PORT", 3307, 1, 65535)
    mongo_port = 27017
    manifest = runtime / "native.json"
    if args.action == "status":
        print(json.dumps({"mysql": listening(mysql_port), "mongodb": listening(mongo_port), "runtime": str(runtime)}, indent=2))
        return
    if args.action == "stop":
        if not manifest.exists():
            raise ValueError("Sem manifesto local: nenhum processo foi encerrado.")
        import pymysql
        from pymongo import MongoClient
        from pymongo.errors import AutoReconnect
        if listening(mysql_port):
            connection = pymysql.connect(host="127.0.0.1", port=mysql_port, user="root", password=os.environ["MYSQL_ROOT_PASSWORD"])
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT @@datadir")
                    actual = Path(cursor.fetchone()[0]).resolve()
                    if actual != (runtime / "mysql-data").resolve():
                        raise ValueError("Instância MySQL não pertence a este runtime.")
                    cursor.execute("SHUTDOWN")
            finally:
                connection.close()
        if listening(mongo_port):
            with MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=3000) as client:
                actual = Path(client.admin.command("getCmdLineOpts")["parsed"]["storage"]["dbPath"]).resolve()
                if actual != (runtime / "mongo-data").resolve():
                    raise ValueError("Instância MongoDB não pertence a este runtime.")
                try:
                    client.admin.command("shutdown")
                except AutoReconnect:
                    pass
        print("Bancos portáteis encerrados com seus comandos de shutdown.")
        return
    if os.name != "nt":
        raise ValueError("Este modo é específico para Windows. Em Linux utilize o Compose.")
    if listening(mysql_port) or listening(mongo_port):
        if manifest.exists() and listening(mysql_port) and listening(mongo_port):
            print("Bancos já respondem. Use etl.native status ou execute a ETL.")
            return
        raise RuntimeError("Porta 3307 ou 27017 em uso. Nenhum banco existente foi substituído.")
    runtime.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        mysql_exe, mongo_exe = list(pool.map(lambda kind: install(runtime, kind), ["mysql", "mongodb"]))
    mysql_data, mongo_data = runtime / "mysql-data", runtime / "mongo-data"
    mongo_data.mkdir(exist_ok=True)
    new_mysql = not (mysql_data / "mysql").exists()
    if new_mysql:
        subprocess.run([str(mysql_exe), "--no-defaults", "--initialize-insecure", f"--basedir={mysql_exe.parents[1]}",
                        f"--datadir={mysql_data}", "--console"], check=True, timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW, stdout=(runtime / "mysql-init.log").open("ab"), stderr=subprocess.STDOUT)
    handles = []
    try:
        for name, executable, extra in [
            ("mysql", mysql_exe, ["--no-defaults", f"--basedir={mysql_exe.parents[1]}", f"--datadir={mysql_data}",
                f"--port={mysql_port}", "--bind-address=127.0.0.1", "--mysqlx=OFF", "--skip-log-bin", "--innodb-buffer-pool-size=64M", "--console"]),
            ("mongodb", mongo_exe, ["--dbpath", str(mongo_data), "--bind_ip", "127.0.0.1", "--port", str(mongo_port),
                "--wiredTigerCacheSizeGB", "0.25", "--logpath", str(runtime / "mongodb.log"), "--logappend"]),
        ]:
            handle = (runtime / f"{name}-process.log").open("ab")
            handles.append(handle)
            process = subprocess.Popen([str(executable), *extra], stdout=handle, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS, cwd=runtime)
            wait(mysql_port if name == "mysql" else mongo_port, process)
            if name == "mysql":
                import pymysql
                connection = pymysql.connect(host="127.0.0.1", port=mysql_port, user="root",
                    password="" if new_mysql else os.environ["MYSQL_ROOT_PASSWORD"])
                try:
                    user, database = os.getenv("MYSQL_USER", "tpch"), os.getenv("MYSQL_DATABASE", "tpch")
                    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
                        raise ValueError("Nome de banco inválido para configuração automática.")
                    with connection.cursor() as cursor:
                        if new_mysql:
                            cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (os.environ["MYSQL_ROOT_PASSWORD"],))
                        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
                        cursor.execute("CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s", (user, os.environ["MYSQL_PASSWORD"]))
                        cursor.execute(f"GRANT ALL ON `{database}`.* TO %s@'localhost'", (user,))
                    connection.commit()
                finally:
                    connection.close()
        manifest.write_text(json.dumps({"runtime": str(runtime), "mysql_port": mysql_port, "mongo_port": mongo_port,
                                       "pacotes": PACKAGES}, indent=2), encoding="utf-8")
        print("MySQL e MongoDB prontos no Windows. Execute seed, migrate e validate.")
    finally:
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
