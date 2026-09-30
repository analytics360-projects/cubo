"""Configuración de Superset con marca CuboIP.

VM dev-superset-cuboip-01 (10.19.5.243, Proxmox 360 VMID 110).
Fuente de datos: base `cuboip` en 10.19.5.100 (compartida con el staging del .244)
mediante el rol de solo lectura `superset_ro`. Ese servidor tiene 1 GB de RAM y
lo usan más de 25 bases: todo lo que toque la base va cacheado y con límites.
"""
import os
from datetime import timedelta

from celery.schedules import crontab

env = os.environ.get

# ---------------------------------------------------------------------------
# Básico
# ---------------------------------------------------------------------------
SECRET_KEY = env("SUPERSET_SECRET_KEY")
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{env('META_DB_USER')}:{env('META_DB_PASSWORD')}"
    f"@{env('META_DB_HOST', 'metadb')}:5432/{env('META_DB_NAME', 'superset')}"
)
SUPERSET_WEBSERVER_TIMEOUT = 120
ROW_LIMIT = 50000
SQL_MAX_ROW = 100000
DISPLAY_MAX_ROW = 10000
SQLLAB_TIMEOUT = 60
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
ENABLE_PROXY_FIX = True
PREFERRED_URL_SCHEME = "https"
WEBDRIVER_BASEURL = "http://superset:8088/"
WEBDRIVER_BASEURL_USER_FRIENDLY = env("SUPERSET_PUBLIC_URL", "https://10.19.5.243/")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"],
        "default-src": ["'self'"],
        "img-src": ["'self'", "blob:", "data:", "https://tile.openstreetmap.org",
                    "https://server.arcgisonline.com"],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'", "https://tile.openstreetmap.org", "https://server.arcgisonline.com"],
        "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'"],
        "script-src": ["'self'", "'strict-dynamic'"],
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,
    "session_cookie_secure": True,
}

# ---------------------------------------------------------------------------
# Idioma y formatos (México)
# ---------------------------------------------------------------------------
BABEL_DEFAULT_LOCALE = "es"
LANGUAGES = {
    "es": {"flag": "mx", "name": "Español"},
    "en": {"flag": "us", "name": "English"},
}
D3_FORMAT = {"decimal": ".", "thousands": ",", "grouping": [3], "currency": ["$", ""]}
D3_TIME_FORMAT = {
    "dateTime": "%A, %e de %B de %Y, %X",
    "date": "%d/%m/%Y",
    "time": "%H:%M:%S",
    "periods": ["a. m.", "p. m."],
    "days": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
    "shortDays": ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
    "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "shortMonths": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                    "sep", "oct", "nov", "dic"],
}
CURRENCIES = ["MXN", "USD"]
DEFAULT_TIMEZONE = "America/Mexico_City"

# ---------------------------------------------------------------------------
# Marca CuboIP (tokens tomados de horus/src/tailwind.css)
# ---------------------------------------------------------------------------
APP_NAME = "CuboIP Analítica"
APP_ICON = "/static/assets/cuboip/logo-cuboip-light.svg"
LOGO_TARGET_PATH = "/superset/welcome/"
LOGO_TOOLTIP = "CuboIP Analítica"
FAVICONS = [
    {"href": "/static/assets/cuboip/favicon.ico", "sizes": "32x32"},
    {"href": "/static/assets/cuboip/cubo360_192.png", "sizes": "192x192", "type": "image/png"},
]

_FONT_SANS = ('-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
              'Inter, "Segoe UI", Roboto, system-ui, sans-serif')
_FONT_MONO = '"SF Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace'

_TOKENS_COMUNES = {
    "brandAppName": APP_NAME,
    "brandLogoAlt": "CuboIP",
    "brandLogoHref": "/superset/welcome/",
    "brandLogoHeight": "28px",
    "brandLogoMargin": "12px 0",
    "brandIconMaxWidth": 200,
    "brandSpinnerUrl": "/static/assets/cuboip/spinner-cuboip.svg",
    "fontFamily": _FONT_SANS,
    "fontFamilyCode": _FONT_MONO,
    "fontSize": 13,
    "borderRadius": 8,
    "borderRadiusLG": 12,
    "borderRadiusSM": 6,
    "controlHeight": 34,
    "fontWeightStrong": "600",
    "colorWarning": "#F5B544",
}

THEME_DEFAULT = {
    "token": {
        **_TOKENS_COMUNES,
        "brandLogoUrl": "/static/assets/cuboip/logo-cuboip-light.svg",
        "colorPrimary": "#0E7490",
        "colorLink": "#0E7490",
        "colorLinkHover": "#0891B2",
        "colorInfo": "#0891B2",
        "colorSuccess": "#16A34A",
        "colorError": "#DC2626",
        "colorBgBase": "#FFFFFF",
        "colorBgLayout": "#F4F5F7",
        "colorBgContainer": "#FFFFFF",
        "colorBgElevated": "#FFFFFF",
        "colorFillAlter": "#F7F8FA",
        "colorTextBase": "#17171A",
        "colorTextSecondary": "#6E7480",
        "colorBorder": "#E5E7EB",
        "colorBorderSecondary": "#EEF0F3",
        "colorEditorSelection": "#CFF7FD",
        "boxShadow": "0 10px 30px -16px rgba(15,23,42,.18)",
    },
    "algorithm": "default",
}

THEME_DARK = {
    "token": {
        **_TOKENS_COMUNES,
        "brandLogoUrl": "/static/assets/cuboip/logo-cuboip-dark.svg",
        "colorPrimary": "#22D3EE",
        "colorLink": "#22D3EE",
        "colorLinkHover": "#67E8F9",
        "colorInfo": "#22D3EE",
        "colorSuccess": "#34D399",
        "colorError": "#FF4D5E",
        "colorBgBase": "#080B10",
        "colorBgLayout": "#080B10",
        "colorBgContainer": "#11161D",
        "colorBgElevated": "#171E27",
        "colorFillAlter": "#171E27",
        "colorTextBase": "#E9EEF4",
        "colorTextSecondary": "#9DA9B6",
        "colorBorder": "#1E2632",
        "colorBorderSecondary": "#1A222D",
        "colorEditorSelection": "#164E63",
        "boxShadow": "0 10px 30px -14px rgba(0,0,0,.55)",
    },
    "algorithm": "dark",
}

# Paletas de gráficas: orden de series de horus (veudora-chart.ts) y semáforo.
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "cuboip",
        "description": "Paleta CuboIP",
        "label": "CuboIP",
        "isDefault": True,
        "colors": ["#0EA5C6", "#7C5CFF", "#34D399", "#F5B544", "#FF4D5E",
                   "#3987E5", "#B9D03C", "#D95926", "#EC4899", "#64748B",
                   "#14B8A6", "#A78BFA"],
    },
    {
        "id": "cuboip_semaforo",
        "description": "Estados: operando, advertencia, falla, sin dato",
        "label": "CuboIP semáforo",
        "isDefault": False,
        "colors": ["#16A34A", "#F5B544", "#DC2626", "#94A3B8", "#0EA5C6"],
    },
]
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [
    {
        "id": "cuboip_cian",
        "label": "CuboIP cian",
        "description": "Intensidad de actividad",
        "isDiverging": False,
        "isDefault": True,
        "colors": ["#ECFEFF", "#A5F3FC", "#22D3EE", "#0891B2", "#155E75", "#083344"],
    },
    {
        "id": "cuboip_alarma",
        "label": "CuboIP alarma",
        "description": "De tranquilo a crítico",
        "isDiverging": False,
        "isDefault": False,
        "colors": ["#F0FDF4", "#BBF7D0", "#F5B544", "#F97316", "#FF4D5E", "#991B1B"],
    },
]

# Mapas base sin llave (Carto ya exige llave): Esri y OpenStreetMap.
_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"
DECKGL_BASE_MAP = [
    [f"tile://{_ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}", "Gris claro (Esri)"],
    [f"tile://{_ESRI}/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}", "Gris oscuro (Esri)"],
    [f"tile://{_ESRI}/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}", "Calles (Esri)"],
    [f"tile://{_ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}", "Satélite (Esri)"],
    ["tile://https://tile.openstreetmap.org/{z}/{x}/{y}.png", "OpenStreetMap"],
]

# ---------------------------------------------------------------------------
# Funcionalidad
# ---------------------------------------------------------------------------
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "ALERT_REPORTS_FILTER": True,
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True,
    "ENABLE_DASHBOARD_SCREENSHOT_ENDPOINTS": True,
    "ENABLE_DASHBOARD_DOWNLOAD_WEBDRIVER_SCREENSHOT": True,
    "THUMBNAILS": True,
    "DASHBOARD_RBAC": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DRILL_BY": True,
    "DRILL_TO_DETAIL": True,
    "TAGGING_SYSTEM": True,
    "ALLOW_FULL_CSV_EXPORT": True,
    "EMBEDDED_SUPERSET": True,
    "EMBEDDABLE_CHARTS": True,
    "LISTVIEWS_DEFAULT_CARD_VIEW": True,
    "DATE_FORMAT_IN_EMAIL_SUBJECT": True,
}

# ---------------------------------------------------------------------------
# Caché y Celery (Redis local de la VM)
# ---------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST", "redis")
REDIS_URL = f"redis://{REDIS_HOST}:6379"


def _cache(prefix, db, timeout):
    return {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": timeout,
        "CACHE_KEY_PREFIX": prefix,
        "CACHE_REDIS_URL": f"{REDIS_URL}/{db}",
    }


CACHE_CONFIG = _cache("cuboip_meta_", 1, int(timedelta(hours=1).total_seconds()))
# Resultados de consultas: 10 min por defecto para no castigar al .100.
DATA_CACHE_CONFIG = _cache("cuboip_data_", 2, int(timedelta(minutes=10).total_seconds()))
FILTER_STATE_CACHE_CONFIG = _cache("cuboip_filter_", 3, int(timedelta(days=90).total_seconds()))
EXPLORE_FORM_DATA_CACHE_CONFIG = _cache("cuboip_explore_", 3, int(timedelta(days=7).total_seconds()))
THUMBNAIL_CACHE_CONFIG = _cache("cuboip_thumb_", 4, int(timedelta(days=7).total_seconds()))
RATELIMIT_STORAGE_URI = f"{REDIS_URL}/5"


class CeleryConfig:
    broker_url = f"{REDIS_URL}/0"
    result_backend = f"{REDIS_URL}/0"
    imports = ("superset.sql_lab", "superset.tasks.scheduler", "superset.tasks.thumbnails",
               "superset.tasks.cache")
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {"task": "reports.scheduler", "schedule": crontab(minute="*", hour="*")},
        "reports.prune_log": {"task": "reports.prune_log", "schedule": crontab(minute=10, hour=0)},
    }


CELERY_CONFIG = CeleryConfig
RESULTS_BACKEND_USE_MSGPACK = True
from flask_caching.backends.rediscache import RedisCache  # noqa: E402

RESULTS_BACKEND = RedisCache(host=REDIS_HOST, port=6379, key_prefix="cuboip_results_", db=6)

# ---------------------------------------------------------------------------
# Reportes y alertas por correo
# ---------------------------------------------------------------------------
ALERT_REPORTS_NOTIFICATION_DRY_RUN = env("SMTP_HOST", "") == ""
EMAIL_REPORTS_SUBJECT_PREFIX = "[CuboIP] "
EMAIL_REPORTS_CTA = "Abrir en CuboIP Analítica"
SMTP_HOST = env("SMTP_HOST", "")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_STARTTLS = env("SMTP_STARTTLS", "true") == "true"
SMTP_SSL = env("SMTP_SSL", "false") == "true"
SMTP_USER = env("SMTP_USER", "")
SMTP_PASSWORD = env("SMTP_PASSWORD", "")
SMTP_MAIL_FROM = env("SMTP_MAIL_FROM", "cuboip-analitica@analytics360.com.mx")
SMTP_SSL_SERVER_AUTH = False
ALERT_REPORTS_WORKING_TIME_OUT_KILL = True
SCREENSHOT_LOCATE_WAIT = 30
SCREENSHOT_LOAD_WAIT = 120
