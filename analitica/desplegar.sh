#!/bin/sh
# Reconstruye y levanta CuboIP Analítica. Uso: ./desplegar.sh
set -e
cd "$(dirname "$0")"
sudo docker compose build
sudo docker compose up -d
mkdir -p nginx/lang
sudo docker compose cp superset:/app/superset/translations/es/LC_MESSAGES/messages.json nginx/lang/es.json
sudo docker compose restart nginx
sudo docker compose ps
