"""Executa pipelines reais, exporta evidências e escreve análise dos resultados."""
import csv
import json
from datetime import datetime, timezone

from etl.analytics import mongo_pipeline
from etl.config import COLLECTION, ROOT, artifacts_dir, mongo_client, mongo_database


def number(value, decimals=0):
    return f"{value:,.{decimals}f}".translate(str.maketrans({",": ".", ".": ","}))


def conclusions(results):
    summary = results["01_resumo_atrasos"][0]
    modes = results["02_atrasos_modalidade"]
    eligible = [r for r in modes if r["total_itens"] >= 100]
    suppliers = results["04_fornecedores"]
    text = [
        f"O recorte contém {number(summary['total_itens'])} itens de pedido, dos quais {number(summary['itens_atrasados'])} chegaram após a data comprometida.",
        f"A taxa de atraso é {number(summary['taxa_atraso_percentual'], 2)}%. Cada item tem o mesmo peso, independentemente da quantidade de unidades.",
    ]
    if summary["media_dias_atraso"] is not None:
        text.append(f"Entre os itens atrasados, o atraso médio é {number(summary['media_dias_atraso'], 2)} dias corridos.")
    if len(eligible) >= 2:
        worst = max(eligible, key=lambda x: x["taxa_atraso_percentual"])
        best = min(eligible, key=lambda x: x["taxa_atraso_percentual"])
        spread = worst["taxa_atraso_percentual"] - best["taxa_atraso_percentual"]
        text.append(f"Entre modalidades com pelo menos 100 itens, {worst['modalidade']} tem a maior taxa ({number(worst['taxa_atraso_percentual'], 2)}%, {number(worst['total_itens'])} itens) e {best['modalidade']} a menor ({number(best['taxa_atraso_percentual'], 2)}%, {number(best['total_itens'])} itens). A diferença descritiva é {number(spread, 2)} pontos percentuais.")
        if spread < 2:
            text.append("A diferença entre modalidades ficou abaixo de 2 pontos percentuais. Esse limite é um critério exploratório da equipe, sem teste de significância. O resultado pede investigar atrasos compartilhados antes de propor troca de modalidade.")
        else:
            text.append("A diferença entre modalidades alcançou pelo menos 2 pontos percentuais. Esse critério exploratório orienta investigar rotas e perfis de carga. A associação observada não demonstra que o transporte causou o atraso.")
    if suppliers and summary["itens_atrasados"]:
        top = suppliers[0]
        share = 100 * top["itens_atrasados"] / summary["itens_atrasados"]
        text.append(f"{top['fornecedor']} reúne o maior número de itens atrasados ({number(top['itens_atrasados'])}, {number(share, 2)}% dos atrasados), com taxa de {number(top['taxa_atraso_percentual'], 2)}% em {number(top['total_itens'])} itens. O volume orienta uma auditoria inicial, sem atribuir a causa ao fornecedor.")
        top_ten = sum(r['itens_atrasados'] for r in suppliers[:10])
        text.append(f"Os dez fornecedores com mais ocorrências acumulam {number(top_ten)} itens atrasados, {number(100 * top_ten / summary['itens_atrasados'], 2)}% do total de atrasados. Esse indicador complementa o ranking individual para avaliar concentração.")
    severe = next((r['total_itens'] for r in results['05_faixas_atraso'] if r['faixa'].startswith('3.')), 0)
    if summary['itens_atrasados']:
        text.append(f"A faixa acima de 14 dias reúne {number(severe)} itens, {number(100 * severe / summary['itens_atrasados'], 2)}% dos atrasados. O acompanhamento deve combinar redução da frequência com tratamento dos atrasos longos.")
    text.append("Na evolução mensal, confira o volume de cada coorte. Os meses de borda do período gerado têm composições e volumes diferentes e não comprovam melhoria ou piora operacional. O gráfico usa o mês do compromisso, mantendo a mesma definição do denominador.")
    text.append("Ações propostas: conferir compromissos de entrega, investigar modalidades/rotas com taxa elevada e volume suficiente e acompanhar taxa e gravidade mensalmente. O TPC-H é sintético e sustenta uma demonstração do método, sem evidenciar ganhos em uma empresa real.")
    return text


def main():
    output = artifacts_dir()
    validation = json.loads((output / "validacao.json").read_text(encoding="utf-8"))
    if validation["status"] != "OK":
        raise ValueError("A validação precisa estar OK antes de exportar resultados.")
    results = {}
    with mongo_client() as client:
        database = mongo_database(client)
        for path in sorted((ROOT / "queries").glob("*.json")):
            query = json.loads(path.read_text(encoding="utf-8"))
            rows = list(database[COLLECTION].aggregate(mongo_pipeline(query)))
            results[path.stem] = rows
            if rows:
                with (output / f"{path.stem}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
        document = database[COLLECTION].find_one()
        (output / "documento_exemplo.json").write_text(json.dumps(document, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary = results.get("01_resumo_atrasos", [])
    if not summary or summary[0]["total_itens"] != validation["destino_mongodb"]["itens"]:
        raise ValueError("Dados mudaram após a validação. Execute novamente a validação.")
    total = summary[0]
    expected = validation["destino_mongodb"]
    if total["itens_atrasados"] != expected["atrasados"] or total["dias_atraso_total"] != expected["dias_atraso"]:
        raise ValueError("Indicadores mudaram após a validação. Execute novamente a validação.")
    report = {"gerado_utc": datetime.now(timezone.utc).isoformat(), "escopo": validation["escopo"], "consultas": results}
    (output / "resultados.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    insights = conclusions(results)
    markdown = "# Análise gerencial com dados processados\n\n" + "\n\n".join(insights)
    markdown += "\n\nFonte: MySQL TPC-H, ETL para MongoDB, consultas em queries/. Evidências: validacao.json e resultados.json.\n"
    (output / "ANALISE_GERENCIAL.md").write_text(markdown, encoding="utf-8")
    from etl.preview import generate
    generate(results, validation, insights)
    print(markdown)


if __name__ == "__main__":
    main()
