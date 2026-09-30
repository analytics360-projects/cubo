#!/bin/sh
# uso: shot.sh <ruta> <nombre> [dark] [WxH]  -> /opt/cuboip-analitica/shots/<nombre>.png
cd /opt/cuboip-analitica
sudo docker compose cp tools/shot.py superset:/tmp/shot.py >/dev/null
sudo docker compose exec -T -e WAIT_MS -e FULL superset python /tmp/shot.py "$1" "/tmp/$2.png" "${3:-light}" "${4:-1440x900}" && \
sudo docker compose cp superset:/tmp/$2.png shots/$2.png >/dev/null && echo shots/$2.png
