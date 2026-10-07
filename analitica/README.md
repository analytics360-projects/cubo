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

`bootstrap/` crea o actualiza de forma idempotente la conexión, 18 datasets virtuales con métricas en español, 140 gráficas y 9 tableros con filtros nativos:

1. Resumen ejecutivo
2. Alertas de IA y analíticas de video
3. Incidentes y despacho
4. Cámaras y video
5. Vehículos, placas y aforo
6. Control de acceso y corporativo
7. Auditoría y uso de la plataforma
8. Tiempos de servicio y cumplimiento (`/superset/dashboard/servicio/`)
9. Riesgo y clasificación (`/superset/dashboard/riesgo/`, opcional: requiere el esquema `shai`)

### Tiempos de servicio y cumplimiento

Lee las vistas `khonsu.*` de amon (migración `20261028093000_KhonsuTableros`, documentadas en
`amon/docs/khonsu/README.md`). La lógica de los tiempos vive en la base, no en Superset: el panel de
horus (Reportes → Tiempos de servicio) y este tablero dan las mismas cifras.

| Dataset | Vista | Para qué |
|---|---|---|
| `cuboip_servicio` | `khonsu.v_cumplimiento` | Un renglón por folio: tramos en minutos (atención, despacho, traslado, llegada, en sitio, cierre), meta aplicada, resultado contra la meta y protocolo. |
| `cuboip_calor` | `khonsu.v_calor` | Folios con coordenadas (del folio o del sitio) y peso por prioridad para el mapa de calor. |

Filtros nativos: periodo, **cliente**, sitio, corporación, incidencia, prioridad y resultado de la
meta. El enlace "Abrir en Analítica" de horus apunta a este tablero (slug configurable en horus).

**Un cliente que solo debe ver lo suyo** (usuario de Superset por cliente): crea un rol a partir de
`CuboIP Consulta` y una regla de *Row Level Security* (Configuración → Seguridad de filas) de tipo
*Regular* sobre `cuboip_servicio` y `cuboip_calor` con la cláusula `empresa_id = <id del cliente>`
(o `id_cuenta IN (...)` por sitios). Los filtros nativos no son seguridad: sin RLS el usuario puede
quitarlos.

### Riesgo y clasificación (opcional)

Datasets `cuboip_riesgo` (`shai.v_riesgo`), `cuboip_alertas_preventivas` (`shai.alertas`) y
`cuboip_clasificacion` (`shai.v_valores`) del módulo shai (rama `feat/predictivo-clasificacion` de
amon, `amon/docs/shai/README.md` §10). Están marcados `opcional`: mientras la base no tenga el
esquema `shai`, `aprovisionar.py` los omite junto con sus gráficas y el tablero, y los crea en la
siguiente corrida.

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
Las migraciones de khonsu y shai dan la lectura de sus vistas a `superset_ro` si el rol ya existe;
`superset_ro_extra.sql` la repone si el rol se creó después.

## Pendiente

- **SMTP:** hay 2 reportes (resumen diario 7:00, incidentes lunes 8:00) y 2 alertas (críticas sin atender >15 min, cámaras caídas >1 h) creados pero inactivos hasta llenar `SMTP_*` en `.env`, reiniciar y volver a correr `aprovisionar.py`.
- Roles: `CuboIP Consulta` (solo tableros) y `CuboIP Analista` (+ SQL Lab), creados con `bootstrap/roles.py`.
