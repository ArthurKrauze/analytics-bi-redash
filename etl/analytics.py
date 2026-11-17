"""Pipelines MongoDB e conversão do formato de ordenação do Redash 10."""
import copy
import json
from etl.config import COLLECTION, ROOT


def group(key):
    return {"$group": {"_id": key, "total_itens": {"$sum": 1},
        "itens_atrasados": {"$sum": {"$cond": ["$entrega.atrasada", 1, 0]}},
        "dias_atraso_total": {"$sum": "$entrega.diasAtraso"},
        "media_dias_atraso": {"$avg": {"$cond": ["$entrega.atrasada", "$entrega.diasAtraso", None]}}}}


def project(labels):
    return {"$project": {"_id": 0, **labels, "total_itens": 1, "itens_atrasados": 1,
        "dias_atraso_total": 1,
        "taxa_atraso_percentual": {"$round": [{"$multiply": [{"$divide": ["$itens_atrasados", "$total_itens"]}, 100]}, 2]},
        "media_dias_atraso": {"$round": ["$media_dias_atraso", 2]}}}


def queries():
    return {
        "01_resumo_atrasos.json": [group(None), project({})],
        "02_atrasos_modalidade.json": [group("$entrega.modalidade"), project({"modalidade": "$_id"}),
                                      {"$sort": {"taxa_atraso_percentual": -1, "modalidade": 1}}],
        "03_evolucao_mensal.json": [group({"$dateToString": {"format": "%Y-%m", "date": "$datas.comprometida", "timezone": "UTC"}}),
                                    project({"mes_compromisso": "$_id"}), {"$sort": {"mes_compromisso": 1}}],
        "04_fornecedores.json": [group({"id": "$fornecedor.id", "nome": "$fornecedor.nome"}),
                                  project({"fornecedor_id": "$_id.id", "fornecedor": "$_id.nome"}),
                                  {"$sort": {"itens_atrasados": -1, "total_itens": -1, "fornecedor_id": 1}}],
        "05_faixas_atraso.json": [
            {"$project": {"faixa": {"$switch": {"branches": [
                {"case": {"$eq": ["$entrega.diasAtraso", 0]}, "then": "0. No prazo"},
                {"case": {"$lte": ["$entrega.diasAtraso", 7]}, "then": "1. De 1 a 7 dias"},
                {"case": {"$lte": ["$entrega.diasAtraso", 14]}, "then": "2. De 8 a 14 dias"}],
                "default": "3. Acima de 14 dias"}}}},
            {"$group": {"_id": "$faixa", "total_itens": {"$sum": 1}}},
            {"$project": {"_id": 0, "faixa": "$_id", "total_itens": 1}}, {"$sort": {"faixa": 1}}],
        "06_atrasos_regiao_cliente.json": [group("$cliente.regiao"), project({"regiao_cliente": "$_id"}),
                                            {"$sort": {"taxa_atraso_percentual": -1, "regiao_cliente": 1}}],
    }


def redash_query(pipeline):
    result = copy.deepcopy(pipeline)
    for stage in result:
        if "$sort" in stage:
            stage["$sort"] = [{"name": name, "direction": direction} for name, direction in stage["$sort"].items()]
    return {"collection": COLLECTION, "aggregate": result}


def mongo_pipeline(query):
    stages = copy.deepcopy(query["aggregate"])
    for stage in stages:
        if isinstance(stage.get("$sort"), list):
            stage["$sort"] = {item["name"]: item["direction"] for item in stage["$sort"]}
    return stages


def main():
    for name, pipeline in queries().items():
        (ROOT / "queries" / name).write_text(json.dumps(redash_query(pipeline), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(name)


if __name__ == "__main__":
    main()
