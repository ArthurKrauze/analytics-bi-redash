"""Validação exata por chave, atributo e indicadores, com evidência JSON."""
import json
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone

from etl.config import (COLLECTION, artifacts_dir, integer, mongo_client,
                        mongo_database, mysql_connection, scope)
from etl.model import nested, to_datetime
from etl.source import reference_sql

FIELDS = {
    "pedidoId": "l_orderkey", "numeroItem": "l_linenumber", "quantidade": "l_quantity",
    "entrega.modalidade": "l_shipmode", "entrega.atrasada": "esperado_atrasada",
    "entrega.diasAtraso": "esperado_dias", "cliente.id": "o_custkey",
    "cliente.segmento": "c_mktsegment", "cliente.nacao": "cliente_nacao",
    "cliente.regiao": "cliente_regiao", "fornecedor.id": "l_suppkey",
    "fornecedor.nome": "fornecedor_nome", "fornecedor.nacao": "fornecedor_nacao",
    "fornecedor.regiao": "fornecedor_regiao", "produto.id": "l_partkey",
    "produto.marca": "p_brand", "produto.tipo": "p_type",
    "datas.envio": "l_shipdate", "datas.comprometida": "l_commitdate",
    "datas.recebimento": "l_receiptdate",
}


def counters():
    return {"itens": 0, "atrasados": 0, "dias_atraso": 0}


def add(target, late, days):
    target["itens"] += 1
    target["atrasados"] += int(bool(late))
    target["dias_atraso"] += int(days)


def metrics(counts):
    total, late, days = counts["itens"], counts["atrasados"], counts["dias_atraso"]
    return {**counts, "taxa_atraso_percentual": round(100 * late / total, 6) if total else None,
            "media_dias_entre_atrasados": round(days / late, 6) if late else None}


def compare_document(row, document):
    if document is None:
        return ["documento ausente"]
    errors = []
    for field, source in FIELDS.items():
        expected, actual = row[source], nested(document, field)
        if field.startswith("datas."):
            expected = to_datetime(expected)
        elif field == "entrega.atrasada":
            expected = bool(expected)
            if not isinstance(actual, bool):
                errors.append(f"{field}: tipo deve ser booleano")
        elif field in ("quantidade", "entrega.diasAtraso", "pedidoId", "numeroItem") or field.endswith(".id"):
            expected = int(expected)
        if actual != expected:
            errors.append(f"{field}: origem={expected!r}, destino={actual!r}")
    return errors


def validate(conn, collection, limit, batch):
    origin_total, target_total = counters(), counters()
    origin_groups, target_groups = defaultdict(counters), defaultdict(counters)
    errors, examples = 0, []
    sql, params = reference_sql(limit)
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        while rows := cursor.fetchmany(batch):
            ids = [f'{r["l_orderkey"]}:{r["l_linenumber"]}' for r in rows]
            documents = {d["_id"]: d for d in collection.find({"_id": {"$in": ids}})}
            for row, key in zip(rows, ids):
                add(origin_total, row["esperado_atrasada"], row["esperado_dias"])
                for group in (f'modalidade:{row["l_shipmode"]}', f'mes_compromisso:{row["esperado_mes"]}'):
                    add(origin_groups[group], row["esperado_atrasada"], row["esperado_dias"])
                differences = compare_document(row, documents.get(key))
                if differences:
                    errors += 1
                    if len(examples) < 20:
                        examples.append({"chave": key, "divergencias": differences})
    for document in collection.find({}):
        try:
            late, days = nested(document, "entrega.atrasada"), nested(document, "entrega.diasAtraso")
            committed = nested(document, "datas.comprometida")
            if not isinstance(late, bool) or isinstance(days, bool) or not isinstance(days, int) or days < 0:
                raise ValueError("Tipos de medidas inválidos")
            if not isinstance(committed, datetime):
                raise ValueError("Data comprometida inválida")
            add(target_total, late, days)
            for group in (f'modalidade:{nested(document, "entrega.modalidade")}',
                          f'mes_compromisso:{committed:%Y-%m}'):
                add(target_groups[group], late, days)
        except (TypeError, ValueError):
            errors += 1
            if len(examples) < 20:
                examples.append({"chave": str(document.get("_id")), "divergencias": ["estrutura inválida"]})
    actual_count = collection.count_documents({})
    groups_ok = dict(origin_groups) == dict(target_groups)
    valid = bool(origin_total["itens"]) and origin_total == target_total and not errors and groups_ok and actual_count == origin_total["itens"]
    return {
        "status": "OK" if valid else "DIVERGENCIA", "gerado_utc": datetime.now(timezone.utc).isoformat(),
        "escopo": scope(), "origem_mysql": metrics(origin_total), "destino_mongodb": metrics(target_total),
        "documentos_destino": actual_count, "itens_com_divergencia": errors,
        "grupos_conferem": groups_ok, "origem_por_grupo": dict(sorted(origin_groups.items())),
        "destino_por_grupo": dict(sorted(target_groups.items())), "exemplos_divergencias": examples,
        "observacao": "Base vazia reprova. Média sem itens atrasados é nula (não aplicável).",
    }


def main():
    with closing(mysql_connection(stream=True)) as conn, mongo_client() as client:
        with conn.cursor() as cursor:
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        report = validate(conn, mongo_database(client)[COLLECTION], scope()["limite"],
                          integer("ETL_BATCH", 1000, 1, 10000))
    path = artifacts_dir() / "validacao.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "origem_mysql", "destino_mongodb", "itens_com_divergencia", "grupos_conferem")}, ensure_ascii=False, indent=2))
    print(f"Evidência: {path}")
    if report["status"] != "OK":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
