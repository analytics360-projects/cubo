"""Cliente mínimo de la API de Superset para el aprovisionamiento de CuboIP Analítica.

Todas las operaciones son idempotentes: se busca por nombre y se crea o actualiza.
"""
import json
import os
import time

import requests
import urllib3

# Por nginx: la cookie de sesión es Secure y el CSRF exige HTTPS con Referer del mismo origen.
BASE = os.environ.get("SUPERSET_URL", "https://nginx" + os.environ.get("SUPERSET_APP_ROOT", "").rstrip("/"))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Superset:
    def __init__(self, user, password):
        self.s = requests.Session()
        self.s.verify = False  # red interna del compose; el certificado es para 10.19.5.243
        r = self.s.post(f"{BASE}/api/v1/security/login",
                        json={"username": user, "password": password, "provider": "db", "refresh": True})
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        csrf = self.s.get(f"{BASE}/api/v1/security/csrf_token/").json()["result"]
        self.s.headers.update({"X-CSRFToken": csrf, "Referer": f"{BASE}/"})

    # -- HTTP -----------------------------------------------------------------
    def _req(self, method, path, **kw):
        for intento in range(6):
            r = self.s.request(method, f"{BASE}/api/v1/{path}", **kw)
            if r.status_code != 429:
                break
            time.sleep(1 + intento)  # límite de peticiones de Superset
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:800]}")
        return r.json() if r.text else {}

    def get(self, path, **kw):
        return self._req("GET", path, **kw)

    def post(self, path, body):
        return self._req("POST", path, json=body)

    def put(self, path, body):
        return self._req("PUT", path, json=body)

    def find(self, resource, col, value):
        q = {"filters": [{"col": col, "opr": "eq", "value": value}], "page_size": 100}
        res = self.get(f"{resource}/", params={"q": json.dumps(q)})["result"]
        return res[0] if res else None

    # -- Base de datos --------------------------------------------------------
    def upsert_database(self, name, uri, extra):
        body = {
            "database_name": name,
            "sqlalchemy_uri": uri,
            "expose_in_sqllab": True,
            "allow_run_async": True,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
            "allow_file_upload": False,
            "cache_timeout": 600,
            "extra": json.dumps(extra),
        }
        found = self.find("database", "database_name", name)
        if found:
            self.put(f"database/{found['id']}", body)
            return found["id"]
        return self.post("database/", body)["id"]

    # -- Datasets -------------------------------------------------------------
    def upsert_dataset(self, db_id, ds):
        found = self.find("dataset", "table_name", ds["name"])
        if not found:
            ds_id = self.post("dataset/", {
                "database": db_id, "schema": ds.get("schema", "vision"),
                "table_name": ds["name"], "sql": ds["sql"],
            })["id"]
        else:
            ds_id = found["id"]
        current = self.get(f"dataset/{ds_id}")["result"]
        # Refresca columnas desde el SQL para que existan antes de describirlas.
        self.put(f"dataset/{ds_id}", {"sql": ds["sql"]})
        self._req("PUT", f"dataset/{ds_id}/refresh")
        current = self.get(f"dataset/{ds_id}")["result"]

        cols = []
        for c in current["columns"]:
            meta = ds.get("columns", {}).get(c["column_name"], {})
            cols.append({
                "id": c["id"],
                "column_name": c["column_name"],
                "verbose_name": meta.get("label", c.get("verbose_name")),
                "description": meta.get("description", c.get("description")),
                "is_dttm": c["column_name"] == ds.get("time_column") or c.get("is_dttm", False),
                "groupby": True,
                "filterable": True,
                "type": c.get("type"),
                "python_date_format": c.get("python_date_format"),
            })
        existing_metrics = {m["metric_name"]: m["id"] for m in current["metrics"]}
        metrics = []
        for m in ds.get("metrics", []):
            item = {
                "metric_name": m["name"],
                "verbose_name": m["label"],
                "expression": m["sql"],
                "d3format": m.get("format"),
                "description": m.get("description"),
                "metric_type": m.get("type"),
            }
            if m["name"] in existing_metrics:
                item["id"] = existing_metrics[m["name"]]
            metrics.append(item)
        self.put(f"dataset/{ds_id}?override_columns=true", {
            "description": ds.get("description"),
            "main_dttm_col": ds.get("time_column"),
            "cache_timeout": ds.get("cache_timeout", 600),
            "columns": cols,
            "metrics": metrics,
        })
        return ds_id

    # -- Gráficas -------------------------------------------------------------
    def managed_charts(self):
        """Gráficas creadas por este aprovisionamiento, por clave estable (params.cuboip_key)."""
        out, page = {}, 0
        while True:
            q = {"columns": ["id", "params"], "page": page, "page_size": 100}
            res = self.get("chart/", params={"q": json.dumps(q)})["result"]
            for c in res:
                key = json.loads(c.get("params") or "{}").get("cuboip_key")
                out[key or f"_sin_clave_{c['id']}"] = c["id"]
            if len(res) < 100:
                return out
            page += 1

    def upsert_chart(self, key, name, viz, ds_id, params, description=None, existing=None):
        params = {"viz_type": viz, "datasource": f"{ds_id}__table", **params, "cuboip_key": key}
        body = {
            "slice_name": name,
            "viz_type": viz,
            "datasource_id": ds_id,
            "datasource_type": "table",
            "params": json.dumps(params),
            "description": description,
        }
        if existing and key in existing:
            self.put(f"chart/{existing[key]}", body)
            return existing[key]
        return self.post("chart/", body)["id"]

    # -- Tableros -------------------------------------------------------------
    def upsert_dashboard(self, title, slug, position, json_metadata, css="", published=True):
        body = {
            "dashboard_title": title,
            "slug": slug,
            "position_json": json.dumps(position),
            "json_metadata": json.dumps(json_metadata),
            "css": css,
            "published": published,
        }
        found = self.find("dashboard", "slug", slug)
        if found:
            self.put(f"dashboard/{found['id']}", body)
            return found["id"]
        return self.post("dashboard/", body)["id"]
