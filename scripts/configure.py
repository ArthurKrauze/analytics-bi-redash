"""Cria .env local e completa somente valores ausentes ou placeholders."""
import secrets
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SECRETS = {"MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "POSTGRES_PASSWORD",
           "REDASH_COOKIE_SECRET", "REDASH_SECRET_KEY", "REDASH_ADMIN_PASSWORD"}


def main():
    values = dict(dotenv_values(ROOT / ".env.example"))
    path = ROOT / ".env"
    values.update(dotenv_values(path) if path.exists() else {})
    for key in SECRETS:
        if not values.get(key) or values[key].startswith("ALTERAR"):
            values[key] = secrets.token_hex(24)
    # Aspas simples preservam $, espaços e # em credenciais já configuradas.
    def quoted(value):
        return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
    path.write_text("\n".join(f"{key}={quoted(value)}" for key, value in values.items()) + "\n", encoding="utf-8")
    print(".env configurado. Senhas preservadas/geradas, sem exibição no terminal.")


if __name__ == "__main__":
    main()
