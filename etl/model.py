"""Transformações e regras de qualidade sem dependência de banco."""
from datetime import date, datetime, time
from decimal import Decimal


def to_datetime(value):
    if isinstance(value, datetime):
        return datetime.combine(value.date(), time.min)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise ValueError(f"Data obrigatória inválida: {value!r}")


def make_document(row):
    key = f'{row["l_orderkey"]}:{row["l_linenumber"]}'
    required = (
        "o_custkey", "cliente_encontrado", "c_mktsegment", "cliente_nacao",
        "cliente_regiao", "fornecedor_nome", "fornecedor_nacao", "fornecedor_regiao",
        "p_brand", "p_type", "l_shipmode",
    )
    missing = [field for field in required if row.get(field) is None or str(row[field]).strip() == ""]
    if missing:
        raise ValueError(f"Item {key}: dimensão ausente ou relacionamento órfão: {missing}")
    envio = to_datetime(row["l_shipdate"])
    compromisso = to_datetime(row["l_commitdate"])
    recebimento = to_datetime(row["l_receiptdate"])
    if recebimento < envio:
        raise ValueError(f"Item {key}: recebimento anterior ao envio.")
    quantity = Decimal(str(row["l_quantity"]))
    if not quantity.is_finite() or quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError(f"Item {key}: quantidade deve ser inteira e positiva no TPC-H.")
    days = max((recebimento - compromisso).days, 0)
    return {
        "_id": key, "pedidoId": int(row["l_orderkey"]), "numeroItem": int(row["l_linenumber"]),
        "datas": {"envio": envio, "comprometida": compromisso, "recebimento": recebimento},
        "entrega": {"modalidade": str(row["l_shipmode"]).strip(), "atrasada": days > 0, "diasAtraso": days},
        "cliente": {"id": int(row["o_custkey"]), "segmento": row["c_mktsegment"],
                    "nacao": row["cliente_nacao"], "regiao": row["cliente_regiao"]},
        "fornecedor": {"id": int(row["l_suppkey"]), "nome": row["fornecedor_nome"],
                       "nacao": row["fornecedor_nacao"], "regiao": row["fornecedor_regiao"]},
        "produto": {"id": int(row["l_partkey"]), "marca": row["p_brand"], "tipo": row["p_type"]},
        "quantidade": int(quantity),
    }


def nested(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value
