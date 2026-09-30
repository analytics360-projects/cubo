"""Aprovisiona CuboIP Analítica: conexión, datasets, gráficas y tableros.

Se ejecuta dentro del contenedor `superset`:
    docker compose exec superset python /app/bootstrap/aprovisionar.py
Es idempotente: se puede correr cada vez que cambien las definiciones.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import Superset  # noqa: E402
from dashboards import CHARTS, DASHBOARDS, LABEL_COLORS  # noqa: E402
from datasets import DATASETS  # noqa: E402

DB_NAME = "CuboIP (staging)"


def _id(*parts):
    return hashlib.sha1("::".join(parts).encode()).hexdigest()[:10].upper()


def native_filters(dash, ds_ids, chart_ids):
    out = []
    for f in dash["filters"]:
        fid = f"NATIVE_FILTER-{_id(dash['slug'], f[1])}"
        base = {
            "id": fid, "name": f[1], "type": "NATIVE_FILTER", "description": "", "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []}, "chartsInScope": chart_ids, "tabsInScope": [],
        }
        if f[0] == "time":
            base.update({
                "filterType": "filter_time", "targets": [{}],
                "controlValues": {"enableEmptyFilter": False},
                "defaultDataMask": {"filterState": {"value": f[2]}, "extraFormData": {"time_range": f[2]}},
            })
        else:
            _, _, col, ds_name = f
            base.update({
                "filterType": "filter_select",
                "targets": [{"datasetId": ds_ids[ds_name], "column": {"name": col}}],
                "controlValues": {"multiSelect": True, "enableEmptyFilter": False, "defaultToFirstItem": False,
                                  "inverseSelection": False, "searchAllOptions": False, "sortAscending": True},
                "defaultDataMask": {"filterState": {}, "extraFormData": {}},
            })
        out.append(base)
    return out


def layout(dash, chart_ids, chart_names):
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": dash["title"]}},
    }
    for r, row in enumerate(dash["rows"]):
        row_id = f"ROW-{_id(dash['slug'], str(r))}"
        pos["GRID_ID"]["children"].append(row_id)
        pos[row_id] = {"type": "ROW", "id": row_id, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                       "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        for c, cell in enumerate(row):
            parents = ["ROOT_ID", "GRID_ID", row_id]
            if cell[0] == "md":
                cid = f"MARKDOWN-{_id(dash['slug'], str(r), str(c))}"
                pos[cid] = {"type": "MARKDOWN", "id": cid, "children": [], "parents": parents,
                            "meta": {"width": cell[1], "height": cell[2], "code": cell[3]}}
            else:
                key, width, height = cell
                cid = f"CHART-{_id(dash['slug'], key)}"
                pos[cid] = {"type": "CHART", "id": cid, "children": [], "parents": parents,
                            "meta": {"width": width, "height": height, "chartId": chart_ids[key],
                                     "sliceName": chart_names[key]}}
            pos[row_id]["children"].append(cid)
    return pos


def main():
    ss = Superset(os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])

    db_id = ss.upsert_database(DB_NAME, os.environ["CUBOIP_DB_URI"], {
        "metadata_params": {},
        "engine_params": {"connect_args": {"application_name": "cuboip-analitica",
                                           "options": "-c statement_timeout=60000"}},
        "metadata_cache_timeout": {"schema_cache_timeout": 3600, "table_cache_timeout": 3600},
        "schemas_allowed_for_file_upload": [],
        "cost_estimate_enabled": True,
        "allows_virtual_table_explore": True,
        "disable_data_preview": False,
    })
    print(f"base de datos {DB_NAME}: {db_id}")

    ds_ids = {}
    for ds in DATASETS:
        ds_ids[ds["name"]] = ss.upsert_dataset(db_id, ds)
        print(f"  dataset {ds['name']}: {ds_ids[ds['name']]}")

    existing = ss.managed_charts()
    chart_ids, chart_names = {}, {}
    for key, (ds_name, title, (viz, params), desc) in CHARTS.items():
        params = {**params, "color_scheme": "cuboip"}
        chart_ids[key] = ss.upsert_chart(key, title, viz, ds_ids[ds_name], params, desc, existing)
        chart_names[key] = title
    for key, chart_id in existing.items():
        if key not in CHARTS:
            ss._req("DELETE", f"chart/{chart_id}")
            print(f"  gráfica retirada: {key}")
    print(f"  {len(chart_ids)} gráficas")

    for dash in DASHBOARDS:
        keys = [cell[0] for row in dash["rows"] for cell in row if cell[0] != "md"]
        ids = [chart_ids[k] for k in keys]
        meta = {
            "color_scheme": "cuboip",
            "label_colors": LABEL_COLORS,
            "refresh_frequency": 600,
            "timed_refresh_immune_slices": [],
            "cross_filters_enabled": True,
            "native_filter_configuration": native_filters(dash, ds_ids, ids),
            "chart_configuration": {
                str(i): {"id": i, "crossFilters": {"scope": "global", "chartsInScope": [x for x in ids if x != i]}}
                for i in ids
            },
            "global_chart_configuration": {"scope": {"rootPath": ["ROOT_ID"], "excluded": []}, "chartsInScope": ids},
            "expanded_slices": {},
            "default_filters": "{}",
        }
        dash_id = ss.upsert_dashboard(dash["title"], dash["slug"], layout(dash, chart_ids, chart_names), meta)
        dash["id"] = dash_id
        print(f"  tablero {dash['title']}: /superset/dashboard/{dash['slug']}/ (id {dash_id})")

    # Relación gráfica ↔ tableros (la API no la deriva del layout).
    owners = {}
    for dash in DASHBOARDS:
        for row in dash["rows"]:
            for cell in row:
                if cell[0] != "md":
                    owners.setdefault(chart_ids[cell[0]], set()).add(dash["id"])
    for chart_id, dash_ids in owners.items():
        ss.put(f"chart/{chart_id}", {"dashboards": sorted(dash_ids)})
    reportes(ss, db_id, {d["slug"]: d["id"] for d in DASHBOARDS})
    print("listo")


def reportes(ss, db_id, dash):
    """Reportes y alertas por correo. Inactivos mientras no haya SMTP configurado."""
    activo = bool(os.environ.get("SMTP_HOST"))
    destino = [{"type": "Email", "recipient_config_json": {"target": os.environ["ADMIN_EMAIL"]}}]
    comunes = {"timezone": "America/Mexico_City", "recipients": destino, "active": activo,
               "working_timeout": 600, "log_retention": 90, "grace_period": 14400}
    definiciones = [
        {"type": "Report", "name": "Resumen ejecutivo diario", "crontab": "0 7 * * *",
         "dashboard": dash["resumen-ejecutivo"], "report_format": "PDF",
         "description": "PDF del resumen ejecutivo cada mañana a las 7:00."},
        {"type": "Report", "name": "Incidentes: resumen semanal", "crontab": "0 8 * * 1",
         "dashboard": dash["incidentes"], "report_format": "PDF",
         "description": "Tablero de incidentes y despacho cada lunes a las 8:00."},
        {"type": "Alert", "name": "Alertas críticas sin atender", "crontab": "*/15 * * * *",
         "dashboard": dash["alertas-ia"], "report_format": "PNG", "database": db_id,
         "sql": "SELECT count(*) FROM vision.alerts WHERE status = 'new' AND priority IN ('critica', 'alta') "
                "AND NOT simulacion AND created_at < now() - interval '15 minutes'",
         "validator_type": "operator", "validator_config_json": {"op": ">", "threshold": 0},
         "description": "Avisa si hay alertas críticas o altas con más de 15 minutos sin que nadie las tome."},
        {"type": "Alert", "name": "Cámaras sin conexión", "crontab": "0 * * * *",
         "dashboard": dash["camaras"], "report_format": "PNG", "database": db_id,
         "sql": "SELECT count(*) FROM vision.cameras WHERE status = 'offline' "
                "AND status_changed_at < now() - interval '1 hour'",
         "validator_type": "operator", "validator_config_json": {"op": ">", "threshold": 0},
         "description": "Avisa cada hora si hay cámaras caídas por más de una hora."},
    ]
    for r in definiciones:
        body = {**comunes, **r}
        found = ss.find("report", "name", r["name"])
        if found:
            ss.put(f"report/{found['id']}", body)
        else:
            ss.post("report/", body)
    print(f"  {len(definiciones)} reportes y alertas ({'activos' if activo else 'inactivos: falta SMTP'})")



if __name__ == "__main__":
    main()
