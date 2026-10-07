# CuboIP Analítica (Apache Superset 6.1)

Superset con la marca de CuboIP para tableros, reportes programados y alertas sobre la base de CuboIP.

| | |
|---|---|
| VM | `dev-superset-cuboip-01`, Proxmox 360 (10.19.5.11), VMID 110, 8 vCPU / 16 GB / 100 GB, Ubuntu 24.04 |
| IP | 10.19.5.243/24, gw 10.19.5.1, DNS 10.19.5.250 |
| URL | Pública: `https://cubo.servicios360.com.mx/analitica/` (proxy `inf-proxy-cuboip-01`, ver `cubo/proxy-publico`). Interna: `https://10.19.5.243/analitica/` (certificado de "CuboIP Desarrollo CA"; `http://10.19.5.243/ca.crt` para instalar la CA) |
| Subruta | `SUPERSET_APP_ROOT=/analitica` en `.env`. Superset 6.1 antepone la subruta dos veces al logo y arma las miniaturas sin ella: `nginx/default.conf` corrige ambos |
| Acceso SSH | `ubuntu@10.19.5.243` con la llave de `heber@mac` |
| Directorio | `/opt/cuboip-analitica` |
| Datos | base `cuboip` en 10.19.5.100 (la misma que usa el staging del .244), rol **`superset_ro`** de solo lectura |

## Servicios (`docker compose -p cuboip-analitica`)

- `superset`: web (gunicorn 4×4, detrás de nginx)
- `superset-worker` y `superset-beat`: Celery para SQL asíncrono, reportes programados, alertas y miniaturas (Playwright + Chromium)
- `metadb`: Postgres 16 con los metadatos de Superset
- `redis`: caché (resultados 10 min) y cola de Celery
- `nginx`: TLS en el 443, redirección desde el 80 y paquete de idioma público para la pantalla de acceso

## Marca

- `docker/superset_config.py`: `THEME_DEFAULT` / `THEME_DARK` con los tokens de `horus/src/tailwind.css`, paletas `cuboip`, `cuboip_semaforo`, `cuboip_cian` y `cuboip_alarma`, idioma español y formatos de México.
- `docker/assets/`: logotipos SVG (imagotipo + "Cubo**IP** | Analítica"), spinner, favicon, iconos, paneles del acceso con el patrón de cubos de horus y `cuboip.css`.
- `docker/po2json.py` + `es_overrides.json`: compila el español de Superset. La imagen lean solo trae los `.po`. Se descartan las traducciones con marcadores rotos, se usa "tablero" en lugar de "panel de control" y se corrigen cadenas vacías del acceso.

## Tableros

`bootstrap/` crea o actualiza de forma idempotente la conexión, 13 datasets virtuales con métricas en español, más de 100 gráficas y 7 tableros con filtros nativos:

1. Resumen ejecutivo
2. Alertas de IA y analíticas de video
3. Incidentes y despacho
4. Cámaras y video
5. Vehículos, placas y aforo
6. Control de acceso y corporativo
7. Auditoría y uso de la plataforma

Reglas de los datasets:

- Todas las fechas están en hora local. `vision.*` y `corp.*` guardan UTC; `public.*` guarda la hora local de amon.
- Se excluyen las simulaciones.
- En `vision.events` el filtro de tiempo se aplica dentro del SQL para no recorrer toda la tabla del servidor compartido.

```sh
# en la VM
cd /opt/cuboip-analitica
./desplegar.sh                                                      # construir y levantar
sudo docker compose exec superset python /app/bootstrap/aprovisionar.py   # tableros
tools/shot.sh /superset/dashboard/resumen-ejecutivo/ resumen light 1600x3400   # captura
```

## Rol de solo lectura

`superset_ro` se crea con `amon/docs/reportes/crear-usuario-lectura.sql`, que cubre `public` y excluye credenciales y tablas de seguridad. `bootstrap/superset_ro_extra.sql` agrega `vision` y `corp` sin datos sensibles: RTSP, embeddings, CURP/RFC, identificaciones, firmas y códigos QR.

Límites del rol: 20 conexiones, `statement_timeout` de 60 s y solo lectura.

Tras migraciones nuevas hay que volver a correr los dos scripts. Las tablas nuevas no quedan expuestas solas.

## Pendiente

- **SMTP:** hay 2 reportes (resumen diario 7:00, incidentes lunes 8:00) y 2 alertas (críticas sin atender >15 min, cámaras caídas >1 h) creados pero inactivos hasta llenar `SMTP_*` en `.env`, reiniciar y volver a correr `aprovisionar.py`.
- Roles: `CuboIP Consulta` (solo tableros) y `CuboIP Analista` (+ SQL Lab), creados con `bootstrap/roles.py`.
