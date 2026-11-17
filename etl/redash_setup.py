"""Cria/reutiliza fonte, queries, gráficos e dashboard local via API do Redash."""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from etl.config import ROOT, artifacts_dir

TITLE = "Equipe 12 - Atrasos nas entregas"
BOOTSTRAP = r'''
import json, sys
from redash import create_app, models
configuration = json.load(sys.stdin)
app = create_app()
with app.app_context():
    org = models.Organization.query.filter_by(slug="default").first()
    if org is None:
        org = models.Organization(name="Equipe 12", slug="default", settings={})
        admin = models.Group(name="admin", permissions=["admin", "super_admin"], org=org, type=models.Group.BUILTIN_GROUP)
        default = models.Group(name="default", permissions=models.Group.DEFAULT_PERMISSIONS, org=org, type=models.Group.BUILTIN_GROUP)
        models.db.session.add_all([org, admin, default])
        models.db.session.commit()
    user = models.User.query.filter_by(email=configuration["email"], org_id=org.id).first()
    if user is None:
        user = models.User(org=org, email=configuration["email"], name="Equipe 12", group_ids=[org.admin_group.id, org.default_group.id])
        user.hash_password(configuration["password"])
        models.db.session.add(user)
        models.db.session.commit()
    print("CODEX_RESULT=" + json.dumps({"key": user.api_key}))
'''


class API:
    def __init__(self, base, key):
        self.base, self.key = base.rstrip("/"), key

    def call(self, path, payload=None):
        request = urllib.request.Request(self.base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": f"Key {self.key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Redash HTTP {exc.code} em {path}. Confira docker compose logs server worker.") from None


def admin_key():
    credentials = {"email": os.environ["REDASH_ADMIN_EMAIL"], "password": os.environ["REDASH_ADMIN_PASSWORD"]}
    process = subprocess.run(["docker", "compose", "exec", "-T", "server", "python", "-c", BOOTSTRAP],
        cwd=ROOT, input=json.dumps(credentials), text=True, encoding="utf-8", capture_output=True, timeout=120)
    # A chave e as senhas nunca são exibidas nem salvas em artifacts/.
    for line in process.stdout.splitlines():
        if line.startswith("CODEX_RESULT=") and process.returncode == 0:
            return json.loads(line.split("=", 1)[1])["key"]
    raise RuntimeError("Não foi possível preparar o administrador local do Redash. Confira o estado de server e postgres.")


def chart(x, y, x_title, y_title, kind="column"):
    return {"globalSeriesType": kind, "columnMapping": {x: "x", y: "y"},
        "legend": {"enabled": True}, "sortX": kind == "line", "numberFormat": "0,0.00",
        "xAxis": {"type": "category", "title": {"text": x_title}, "labels": {"enabled": True}},
        "yAxis": [{"type": "linear", "rangeMin": 0, "title": {"text": y_title}}, {"type": "linear", "opposite": True}],
        "seriesOptions": {y: {"name": y_title, "type": kind, "yAxis": 0}}}


def specifications():
    return [
        ("01_resumo_atrasos.json", "Indicadores gerais", "TABLE", {}, 0, 8, 6, 5),
        ("02_atrasos_modalidade.json", "Taxa de atraso por modalidade (%)", "CHART", chart("modalidade", "taxa_atraso_percentual", "Modalidade de transporte", "Taxa de atraso (%)"), 0, 13, 3, 8),
        ("03_evolucao_mensal.json", "Evolução mensal da taxa de atraso (%)", "CHART", chart("mes_compromisso", "taxa_atraso_percentual", "Mês da data comprometida", "Taxa de atraso (%)", "line"), 3, 13, 3, 8),
        ("04_fornecedores.json", "Fornecedores: volume, taxa e gravidade", "TABLE", {}, 0, 21, 6, 9),
        ("05_faixas_atraso.json", "Itens por faixa de atraso (itens)", "CHART", chart("faixa", "total_itens", "Faixa de atraso em dias corridos", "Quantidade de itens"), 0, 30, 3, 8),
        ("06_atrasos_regiao_cliente.json", "Taxa de atraso por região do cliente (%)", "CHART", chart("regiao_cliente", "taxa_atraso_percentual", "Região do cliente", "Taxa de atraso (%)"), 3, 30, 3, 8),
    ]


def main():
    base = os.getenv("REDASH_URL", "http://localhost:5000")
    for attempt in range(60):
        try:
            with urllib.request.urlopen(base + "/ping", timeout=2):
                break
        except (OSError, urllib.error.URLError):
            if attempt == 59:
                raise RuntimeError("Redash não respondeu. Abra o Docker Desktop e verifique docker compose ps.")
            time.sleep(2)
    api = API(base, admin_key())
    sources = api.call("/api/data_sources")
    source = next((x for x in sources if x["name"] == "TPC-H Entregas"), None)
    if source is None:
        source = api.call("/api/data_sources", {"name": "TPC-H Entregas", "type": "mongodb",
            "options": {"connectionString": "mongodb://mongodb:27017", "dbName": os.getenv("MONGO_DATABASE", "tpch_bi")}})
    dashboards = api.call("/api/dashboards?page_size=250")["results"]
    dashboard = next((x for x in dashboards if x["name"] == TITLE), None)
    dashboard = api.call(f'/api/dashboards/{dashboard["id"]}') if dashboard else api.call("/api/dashboards", {"name": TITLE})
    existing = api.call("/api/queries?q=Equipe%2012&page_size=250")["results"]
    widgets = dashboard.get("widgets", [])

    def widget(visualization_id, name, pos, text=""):
        options = {"position": dict(zip(("col", "row", "sizeX", "sizeY"), pos)), "title": name}
        found = next((w for w in widgets if (w.get("visualization") or {}).get("id") == visualization_id and visualization_id is not None), None)
        if not found:
            return api.call("/api/widgets", {"dashboard_id": dashboard["id"], "visualization_id": visualization_id,
                                            "text": text, "width": 1, "options": options})
        return found

    notes = "### Atrasos nas entregas\nGrão: item de pedido. Taxa = itens atrasados / total de itens. Média considera somente atrasados. Mês usa data comprometida. Dados sintéticos TPC-H. Fornecedores devem ser comparados com seu volume."
    if not any(w.get("text") == notes for w in widgets):
        widget(None, "Escopo e indicadores", (0, 0, 6, 3), notes)
    created_queries = []
    summary_query = None
    for filename, title, kind, options, col, row, sx, sy in specifications():
        name = "Equipe 12 - " + title
        definition = json.loads((ROOT / "queries" / filename).read_text(encoding="utf-8"))
        found = next((q for q in existing if q["name"] == name), None)
        query = api.call(f'/api/queries/{found["id"]}' if found else "/api/queries",
            {"name": name, "description": "Fonte: TPC-H no MySQL, ETL validada para MongoDB. Grão: item de pedido.",
             "query": json.dumps(definition), "data_source_id": source["id"], "options": {"parameters": []}, "is_draft": False})
        vis = next((v for v in query.get("visualizations", []) if v.get("name") == title), None)
        vis = api.call(f'/api/visualizations/{vis["id"]}' if vis else "/api/visualizations",
            {"query_id": query["id"], "type": kind, "name": title, "description": title, "options": options})
        widget(vis["id"], title, (col, row, sx, sy))
        job = api.call(f'/api/queries/{query["id"]}/results', {"max_age": 0, "parameters": {}})
        for attempt in range(120):
            pending = job.get("job")
            if not pending:
                break
            if pending["status"] == 3:
                break
            if pending["status"] in (4, 5):
                raise RuntimeError(f"Consulta Redash falhou: {name}. Confira worker e MongoDB.")
            time.sleep(1)
            job = api.call(f'/api/jobs/{pending["id"]}')
        else:
            raise RuntimeError(f"Tempo excedido na consulta: {name}")
        created_queries.append({"nome": name, "id": query["id"]})
        if filename.startswith("01_"):
            summary_query = query
    for field, label, decimals, col in [("total_itens", "Itens analisados", 0, 0),
        ("taxa_atraso_percentual", "Taxa de atraso (%)", 2, 2), ("media_dias_atraso", "Atraso médio entre atrasados (dias)", 2, 4)]:
        found = api.call(f'/api/queries/{summary_query["id"]}')
        old = next((v for v in found.get("visualizations", []) if v.get("name") == label), None)
        if not old:
            old = api.call("/api/visualizations", {"query_id": summary_query["id"], "type": "COUNTER", "name": label,
                "description": label, "options": {"counterColName": field, "counterLabel": label,
                    "rowNumber": 1, "stringDecimal": decimals, "stringDecChar": ",", "stringThouSep": "."}})
        widget(old["id"], label, (col, 3, 2, 5))
    dashboard = api.call(f'/api/dashboards/{dashboard["id"]}', {"is_draft": False})
    report = {"url": f'{base}/dashboard/{dashboard["slug"]}', "dashboard_id": dashboard["id"],
              "consultas": created_queries, "status": "CRIADO_E_CONSULTAS_EXECUTADAS"}
    (artifacts_dir() / "redash.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f'Dashboard pronto: {report["url"]}. Login e senha estão no .env local.')


if __name__ == "__main__":
    main()
