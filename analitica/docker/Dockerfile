# Superset con marca CuboIP (dev-superset-cuboip-01, 10.19.5.243)
FROM apache/superset:6.1.0

USER root

# Drivers y dependencias: Postgres (metadatos y CuboIP), Redis (caché/Celery),
# Playwright (capturas para reportes programados y miniaturas).
RUN . /app/.venv/bin/activate \
 && uv pip install --no-cache psycopg2-binary redis playwright Pillow \
 && PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright playwright install-deps chromium \
 && PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright playwright install chromium \
 && chmod -R a+rX /usr/local/share/playwright \
 && rm -rf /var/lib/apt/lists/*
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright

# La imagen lean trae solo los .po: compilamos el español para backend (.mo)
# y frontend (messages.json en formato Jed que carga superset/translations/utils.py).
COPY po2json.py es_overrides.json /tmp/
RUN . /app/.venv/bin/activate \
 && D=/app/superset/translations/es/LC_MESSAGES \
 && python /tmp/po2json.py $D/messages.po $D/messages.mo $D/messages.json \
 && rm /tmp/po2json.py /tmp/es_overrides.json

# Marca: logos, favicon, iconos y plantilla con estilos propios.
COPY assets/ /app/superset/static/assets/cuboip/
COPY templates/head_custom_extra.html /app/superset/templates/head_custom_extra.html

USER superset
