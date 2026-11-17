"""Painel offline com resultados reais, complementar à implantação no Redash."""
import html
import json
from etl.config import artifacts_dir


def number(value, places=0):
    if value is None:
        return "Não aplicável"
    return f"{value:,.{places}f}".translate(str.maketrans({",": ".", ".": ","}))


def table(rows, fields):
    heading = "".join(f"<th>{html.escape(label)}</th>" for _, label, _ in fields)
    body = []
    for row in rows:
        cells = []
        for key, _, places in fields:
            value = html.escape(str(row[key])) if places is None else number(row[key], places)
            cells.append(f"<td>{value}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<div class='scroll'><table><thead><tr>{heading}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def bars(rows, label, value, max_value, unit):
    return "".join(f"<div class='bar-row'><span>{html.escape(str(row[label]))}</span><div class='track'><i style='width:{100 * row[value] / max_value:.3f}%'></i></div><strong>{number(row[value], 2 if unit == '%' else 0)} {unit}</strong></div>" for row in rows)


def generate(results, validation, insights):
    summary = results["01_resumo_atrasos"][0]
    modes = results["02_atrasos_modalidade"]
    monthly = results["03_evolucao_mensal"]
    bands = results["05_faixas_atraso"]
    suppliers = results["04_fornecedores"]
    categories = [("total_itens", "Itens analisados", 0, ""), ("itens_atrasados", "Itens atrasados", 0, ""),
                  ("taxa_atraso_percentual", "Taxa de atraso", 2, "%"), ("media_dias_atraso", "Média entre atrasados", 2, " dias")]
    cards = "".join(f"<article><span>{label}</span><strong>{number(summary[field], places)}{unit}</strong></article>" for field, label, places, unit in categories)
    paragraphs = "".join(f"<p>{html.escape(text)}</p>" for text in insights)
    supplier_fields = [("fornecedor", "Fornecedor", None), ("total_itens", "Total de itens", 0),
        ("itens_atrasados", "Atrasados", 0), ("taxa_atraso_percentual", "Taxa (%)", 2), ("media_dias_atraso", "Média entre atrasados (dias)", 2)]
    month_fields = [("mes_compromisso", "Mês do compromisso", None), ("total_itens", "Total de itens", 0),
        ("itens_atrasados", "Atrasados", 0), ("taxa_atraso_percentual", "Taxa (%)", 2), ("media_dias_atraso", "Média (dias)", 2)]
    points = " ".join(f"{70 + i * 1000 / max(len(monthly) - 1, 1):.2f},{280 - row['taxa_atraso_percentual'] * 2.3:.2f}" for i, row in enumerate(monthly))
    ticks = "".join(f"<text x='52' y='{285 - tick * 2.3}' text-anchor='end'>{tick}%</text><line x1='65' y1='{280 - tick * 2.3}' x2='1080' y2='{280 - tick * 2.3}' stroke='#d8e2e7'/>" for tick in (0, 25, 50, 75, 100))
    labels = "".join(f"<text x='{70 + i * 1000 / max(len(monthly) - 1, 1):.2f}' y='310' text-anchor='middle'>{row['mes_compromisso']}</text>" for i, row in enumerate(monthly) if i % 12 == 0 or i == len(monthly) - 1)
    monthly_svg = f"<svg role='img' aria-label='Taxa mensal de atraso em porcentagem, por mês do compromisso' viewBox='0 0 1140 330'>{ticks}<polyline fill='none' stroke='#087f8c' stroke-width='3' points='{points}'/>{labels}</svg>"
    document = f"""<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Equipe 12 — Atrasos nas entregas</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f7f8;color:#182c3a;font:16px/1.6 'Segoe UI',Arial,sans-serif}}main{{max-width:1240px;margin:auto;padding:44px 28px}}header{{padding:30px 0}}h1{{font-size:42px;line-height:1.15;margin:8px 0 20px}}h2{{font-size:25px;margin-top:0}}.eyebrow{{color:#087f8c;font-weight:700}}.notice{{border-left:4px solid #b17316;padding:12px 18px;background:#fff6e6}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin:28px 0}}article,section{{background:white;padding:26px;border:1px solid #dbe5e8;border-radius:10px}}article span{{display:block;color:#526b7a}}article strong{{font-size:33px;display:block;color:#075c66}}section{{margin:22px 0}}.bar-row{{display:grid;grid-template-columns:150px 1fr 105px;gap:14px;align-items:center;margin:18px 0}}.track{{height:25px;background:#edf2f4}}.track i{{display:block;height:100%;background:#087f8c}}.bar-row strong{{text-align:right}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:15px}}th,td{{padding:11px 12px;border-bottom:1px solid #e1e8ec;text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#edf4f5}}small,.muted{{color:#526b7a}}svg{{width:100%;font:14px Arial}}details{{margin-top:18px}}footer{{margin:30px 0}}a{{color:#075c66}}@media(max-width:760px){{.kpis{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:32px}}.bar-row{{grid-template-columns:100px 1fr 88px}}main{{padding:22px 14px}}}}@media print{{body{{background:white}}section{{break-inside:avoid}}details{{display:block}}}}
</style><main><header><div class='eyebrow'>EQUIPE 12 · DATA ANALYTICS E BI</div><h1>Atrasos nas entregas</h1><p>Decisão apoiada: onde concentrar a investigação de falhas logísticas.</p><p class='notice'><strong>Painel offline com dados reais processados.</strong> MySQL e MongoDB executados no Windows. O dashboard Redash precisa de implantação em outro ambiente compatível. Este arquivo serve como apoio à apresentação.</p><p class='muted'>TPC-H sintético, SF 0.01. Grão: item de pedido. Validação MySQL × MongoDB: {html.escape(validation['status'])}. Escopo: {html.escape(validation['escopo']['criterio'])}.</p></header>
<div class='kpis'>{cards}</div><section><h2>Taxa de atraso por modalidade (%)</h2><p>A mesma escala de 0% a 100% permite comparar as modalidades sem ampliar visualmente diferenças pequenas.</p>{bars(modes, 'modalidade', 'taxa_atraso_percentual', 100, '%')}<details><summary>Volumes e gravidade por modalidade</summary>{table(modes, [('modalidade','Modalidade',None), *supplier_fields[1:]])}</details></section>
<section><h2>Evolução mensal da taxa de atraso (%)</h2><p>Mês da data comprometida. Meses de borda têm volumes e composições diferentes.</p>{monthly_svg}<details><summary>Ver valores e volumes de todos os meses</summary>{table(monthly, month_fields)}</details></section>
<section><h2>Gravidade dos atrasos</h2><p>Quantidade de itens por faixa de atraso em dias corridos.</p>{bars(bands, 'faixa', 'total_itens', max(row['total_itens'] for row in bands), 'itens')}</section>
<section><h2>Fornecedores com mais itens atrasados</h2><p>Os dez primeiros por quantidade de atrasados. A taxa e o volume precisam ser lidos juntos.</p>{table(suppliers[:10], supplier_fields)}</section>
<section><h2>Interpretação gerencial</h2>{paragraphs}</section><footer><p>Fontes: <a href='resultados.json'>resultados dos pipelines</a> e <a href='validacao.json'>validação integral</a>. Os arquivos CSV permitem conferir cada visualização.</p><p>Taxa = atrasados / total de itens × 100. Média = soma dos dias / itens atrasados. Atualização pela execução de <code>python -m etl.evidence</code>.</p></footer></main></html>"""
    path = artifacts_dir() / "PAINEL_OFFLINE.html"
    path.write_text(document, encoding="utf-8")
    return path


def main():
    from etl.evidence import conclusions
    output = artifacts_dir()
    report = json.loads((output / "resultados.json").read_text(encoding="utf-8"))
    validation = json.loads((output / "validacao.json").read_text(encoding="utf-8"))
    print(generate(report["consultas"], validation, conclusions(report["consultas"])))


if __name__ == "__main__":
    main()
