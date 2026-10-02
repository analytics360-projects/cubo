# CuboIP en 10.19.5.244 (skynet): pruebas y acceso público

El .244 corre CuboIP completo con Docker Compose y es lo que se publica en
**https://cubo.servicios360.com.mx**. Mapa general del sistema: `amon/docs/README-sistema.md`.

```
Internet ── Cloudflare (proxy, TLS; Origin Rule al puerto 32443) ── NAT 186.96.163.115:32443/7878
        ── proxy público 10.19.5.242 (nginx) ──┬─ /            → horus   .244:7143
                                               ├─ /api /notifications /ari /health → amon .244:7101
                                               ├─ /thot/       → horus .244:7143 → thot (WebSocket)
                                               ├─ /s3/         → MinIO   .244:7110
                                               └─ /analitica/  → Superset .243
Equipos de campo (TCP crudo, sin Cloudflare) ── NAT 186.96.163.115:3001 → wadjet .244:3131
Celulares (TURN, UDP)                        ── NAT 3478 → coturn .244:7178 (Pendiente)
Paneles de alarma (mafdet, en desarrollo)    ── NAT 3011-3013 → amon .244:7151-7153 (Pendiente)
```

| | |
|---|---|
| Servidor | `skynet`, 10.19.5.244: 32 CPU, 61 GB RAM, NVIDIA RTX A5000 24 GB, Docker con runtime de NVIDIA |
| Base de datos | PostgreSQL 14 en **10.19.5.100**, base `cuboip` (pgvector, PostGIS, pg_trgm). Servidor compartido con poca RAM: nada de pruebas de carga contra él. El 5432 del .244 es de otro proyecto. |
| Carpeta | `/srv/cuboip` (LV propio de 200 GB en `/etc/fstab`) |
| Compose | proyecto **`cuboip`**: contenedores `cuboip-*`, red `cuboip-net`. En el servidor corren otros proyectos (CVAT, vitra, capdocs, pce-*, otro go2rtc y otro Ollama): no tocar nada que no empiece por `cuboip-`. |
| Puertos | solo el rango 7100-7199 (más 3131 de wadjet) |

## Levantar, bajar y revisar

```bash
cd /srv/cuboip
docker compose -p cuboip up -d              # todo (restart: unless-stopped)
docker compose -p cuboip ps
docker compose -p cuboip logs -f amon       # o horus, go2rtc, thot, ra-ai-worker...
docker compose -p cuboip restart amon
docker compose -p cuboip down               # los datos quedan en /srv/cuboip/data
```

El usuario inicial de la aplicación lo crea el seed de amon; su contraseña la da el responsable
del ambiente y debe cambiarse al entrar. No se escribe en ningún documento.

## Servicios y puertos

| Contenedor | Puerto del host | Qué es |
|---|---|---|
| `cuboip-horus` | **7143** (HTTPS), 7100 (HTTP → 301 a HTTPS) | Front (nginx). Hace de proxy en el mismo origen de `/api`, `/notifications`, `/ari` (amon) y `/thot/` (thot). Certificado de la CA propia "CuboIP Desarrollo CA" para el acceso por IP; por el dominio el certificado lo presenta Cloudflare. |
| `cuboip-amon` | **7101** (HTTP) | API .NET. Aplica migraciones EF al arrancar. Salud: `/health`. |
| `cuboip-go2rtc` | **7155** tcp/udp (WebRTC), 127.0.0.1:7102 (API, solo depuración) | Video de las cámaras. Candidato ICE `10.19.5.244:7155`. |
| `cuboip-minio` | **7110** (S3), **7111** (consola) | Almacenamiento de amon (bucket `cuboip`). |
| `cuboip-redis` | — | Caché, pases de video, anillo de llaves, líder. |
| `cuboip-ra-recorder` / `cuboip-ra-media` | — | Grabación continua y servidor de medios (solo amon, con token). |
| `cuboip-ra-tracker` | — | Identidad global multicámara. |
| `cuboip-ra-clip` (GPU) | **7120** | CLIP, ReID, rostros, placas. Publicado en la LAN para que un amon de desarrollo pueda enrolar rostros. |
| `cuboip-ra-ai-worker` (GPU) | — | YOLO y analíticas. |
| `cuboip-ollama` (GPU) | — | Copiloto (imhotep), modelo `qwen2.5:7b`. No es el Ollama del host (11434). |
| `cuboip-thot` | — (detrás del nginx de horus en `/thot/`) | Thot: señalización WebRTC del video del agente, página `/v/` e ingesta del video por SMS, difusión a varios espectadores y grabación. Código en `ra/thot`. |
| `cuboip-coturn` | **7178** udp/tcp, relevo **7180-7199/udp** (red del host) | TURN/STUN con credenciales efímeras para el video del agente en segundo plano. |
| `cuboip-wadjet` | **3131** → 3001 (TCP de los equipos), **7131** (HTTP, salud) | Wadjet: receptor TCP de los botones de pánico Eview EV-07B (Sekhmet). Código en `ra/wadjet`. |
| amon · mafdet | 7151, 7152, 7153 | **En desarrollo.** Receptor de paneles de alarma dentro de amon: 7151 SIA-DC, 7152 Visonic/Contact ID, 7153 MLR2. |
| `cuboip-buildkitd` | — | BuildKit propio (caché en `/srv/cuboip/buildkit-state`). |

**Nunca** publicar la API de go2rtc (1984) ni su RTSP (8554).

## NAT de la IP pública 186.96.163.115

| Público | Destino | Para | Estado |
|---|---|---|---|
| 32443/tcp | 10.19.5.242:443 | Proxy público (HTTPS). Cloudflare llega aquí por la Origin Rule; el proxy solo acepta 443 desde rangos de Cloudflare | Hecho |
| 7878/tcp | 10.19.5.242:80 | Proxy público (HTTP → 301 a HTTPS) | Hecho |
| 3001/tcp | 10.19.5.244:3131 | wadjet (botones Eview; comando "Servidor GPRS" = `ip,186.96.163.115,3001`) | Hecho, probado desde internet |
| 3478/udp y 3478/tcp | 10.19.5.244:7178 | coturn (TURN/STUN) | **Pendiente** (equipo de red) |
| 7180-7199/udp | 10.19.5.244:7180-7199 (1:1) | Relevo de coturn | **Pendiente** (equipo de red) |
| 3011/tcp | 10.19.5.244:7151 | mafdet SIA-DC | **Pendiente**; mafdet en desarrollo |
| 3012/tcp | 10.19.5.244:7152 | mafdet Visonic / Contact ID | **Pendiente**; mafdet en desarrollo |
| 3013/tcp | 10.19.5.244:7153 | mafdet MLR2 | **Pendiente**; mafdet en desarrollo |

Lo que es TCP o UDP crudo (equipos, paneles, TURN) no pasa por Cloudflare: va directo por NAT.
La IP pública puede ser dinámica; conviene un DNS sin proxy de Cloudflare para los equipos de campo.

## Dominio y proxy público (10.19.5.242)

Un solo dominio, `cubo.servicios360.com.mx`; la ruta decide el sistema. VM
`inf-proxy-cuboip-01` (Proxmox 360, VMID 121), nginx en `/etc/nginx/conf.d/cuboip-publico.conf`.
Fuente y detalle: `proxy-publico/README.md` (aún sin versionar).

| Ruta | Destino |
|---|---|
| `/` | horus (.244:7143) |
| `/api/…`, `/notifications`, `/ari`, `/health` | amon (.244:7101), con WebSocket |
| `/thot/` | WebSocket de la señalización de video, por el nginx de horus |
| `/analitica/` | Superset en 10.19.5.243 (`SUPERSET_APP_ROOT=/analitica`) |
| `/s3/` | MinIO (.244:7110), solo GET/HEAD con URL firmada |
| `/api/VideoInterno`, `/api/Thot/senal/evento` | 403 (uso interno) |
| `/cubo` | 301 a `/` |
| otro host o acceso por IP | se cierra sin responder |

- Cloudflare: registro A `cubo` → 186.96.163.115 con proxy; SSL Full (Full strict cuando se cargue
  el Origin CA); Origin Rule con la condición `(http.host eq "cubo.servicios360.com.mx")` que cambia
  el puerto de destino a **32443**. Una condición con `full_uri` y wildcard nunca coincide: Cloudflare
  va al 443 (sin NAT) y responde 522.
- El acceso por IP sin dominio (`https://186.96.163.115:32443/`) se rechaza.
- Cloudflare bloquea el User-Agent `Python-urllib` (error 1010): los scripts de prueba deben mandar
  otro (p. ej. el de Dart que usa la app).
- Cloudflare no pasa UDP: WebRTC hacia go2rtc (7155) cae a MSE por WebSocket, y el video de
  celulares por datos móviles usa WebSocket o TURN.
- El service worker de horus no atiende `/analitica`, `/api`, `/s3`, `/notifications`, `/ari` ni
  `/health`; si un navegador viejo sigue mostrando horus en `/analitica`, basta recargar.
- **Pendiente:** certificado Origin CA de Cloudflare en el proxy (hoy autofirmado provisional; SSL
  en Full, no Full strict).
- **Pendiente:** `MINIO_PUBLIC_URL=/s3` en amon. Solo existe en la rama `feat/minio-url-publica`
  (sin unir a development). Sin ella, las URLs prefirmadas salen con el origen interno y los planos
  y audios no cargan desde fuera.

## CuboIP Analítica (Superset, 10.19.5.243)

VM `dev-superset-cuboip-01` (VMID 110), stack en `/opt/cuboip-analitica`
(`docker compose -p cuboip-analitica`). Lee la base `cuboip` del .100 con el rol de solo lectura
`superset_ro`. Publicado en `https://cubo.servicios360.com.mx/analitica/`. Código en
`cubo/analitica/` (hoy en la rama `feat/video`).

## Variables de entorno

Los valores viven en `/srv/cuboip/.env` (chmod 600) o en `docker-compose.yml`. Aquí solo el
nombre y el propósito. Lo configurable por el usuario va en horus (Sistema → Configuración), no en
variables: estas son conexiones y secretos de arranque.

### amon

| Variable | Propósito |
|---|---|
| `POSTGRESCONNECTIONSTRING` | Base `cuboip` del .100 (secreto). |
| `REPORTS_CONNECTIONSTRING` | Opcional: conexión de solo lectura para reportes. |
| `REDISCONNECTIONSTRING` | Redis (secreto). |
| `JwtIssuerOptions__SecretKey` | Firma de los tokens (secreto, propia del ambiente). Los tokens duran 12 h; la sesión ya no se cierra por inactividad. |
| `STORAGE_TYPE`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY_ID`, `MINIO_SECRET_ACCESS_KEY`, `BUCKET_NAME` | Almacenamiento (secretos las llaves). |
| `MINIO_PUBLIC_URL` | **Pendiente** (rama `feat/minio-url-publica`): origen público `/s3` de las URLs prefirmadas. |
| `DATAPROTECTION_KEYS_PATH` | Carpeta del anillo de llaves (`data/dataprotection-keys`). Cifra contraseñas de cámaras y secretos. Respaldarla: si se pierde no se descifran. |
| `AMON_PROXIES_CONFIABLES` | Redes CIDR de proxies confiables para `X-Forwarded-For`. Por omisión loopback y redes privadas; así amon ve la IP real del cliente (auditoría y límites por IP). |
| `GO2RTC_URL`, `GO2RTC_USER`, `GO2RTC_PASSWORD` | API de go2rtc (secretos usuario y contraseña). |
| `VIDEO_AMON_INTERNAL_URL`, `VIDEO_MJPEG_FFMPEG_RAW`, `VIDEO_ICE_SERVERS`, `VIDEO_*` | Video de cámaras (MJPEG interno, iceServers, pases). |
| `VISION_ENABLED`, `VISION_RTSP_BASE`, `VISION_MEDIA_URL`, `VISION_MEDIA_TOKEN`, `CLIP_URL`, `VISION_*` | Visión e IA (nekhbet) y servidor de medios de ra. `VISION_MEDIA_TOKEN` es secreto e igual a `RA_MEDIA_TOKEN`. |
| `COPILOT_PROVIDER`, `OLLAMA_URL`, `COPILOT_MODEL`, `COPILOT_TIMEOUT_SECONDS`, `COPILOT_DEBATE`, `COPILOT_TIMEZONE` | Copiloto (imhotep): Ollama del compose, `qwen2.5:7b`. |
| `CAMERAS_EXPOSE_CREDENTIALS` | `false`: el front nunca recibe credenciales de cámaras. |
| `ARI_ENABLED` | Conmutador (sin PBX en el .244). |
| `OTEL_ENABLED` | Trazas OpenTelemetry. |
| `THOT_URL` | Señalización interna de thot. |
| `THOT_URL_EMISOR` | URL de la señalización que se entrega a la app del agente: `wss://cubo.servicios360.com.mx/thot/` (antes la IP privada, que los celulares fuera de la LAN no alcanzan). |
| `THOT_SECRETO` | Secreto compartido amon ↔ thot para pases y avisos firmados. |
| `THOT_ESPERA_SEGUNDOS` | Cuánto espera amon a que la app del agente abra el video (por omisión 90; en el .244, 60). |
| `THOT_ICE_SERVERS` | iceServers (JSON) para el emisor. |
| `THOT_TURN_URLS` | URLs TURN que se entregan a la app: pública `186.96.163.115:3478` (udp/tcp) y LAN `10.19.5.244:7178`. |
| `THOT_TURN_SECRETO` | `static-auth-secret` de coturn; amon genera credenciales efímeras con él (secreto). |
| `THOT_TURN_VIGENCIA_SEGUNDOS`, `THOT_PASE_*`, `THOT_MAX_MINUTOS`, `THOT_*` | Vigencias de pases y transmisiones. La URL pública, el texto del SMS, la caducidad del enlace, la grabación y la calidad se editan en horus (Configuración → Video en vivo y por SMS). |
| `SEKHMET_GATEWAY_HOST`, `SEKHMET_GATEWAY_PUERTO` | IP pública y puerto que se programan en los Eview (`186.96.163.115`, `3001`). |
| `SEKHMET_GATEWAY_SECRET` | Secreto HMAC compartido con wadjet (`CUBO_GATEWAY_SECRET`). |
| `SEKHMET_*` (SMS, Twilio, límites) | Botones de pánico; los secretos de proveedores de SMS van solo en `.env` o cifrados en ConfiguracionGlobal. |

### ra, thot, wadjet y coturn

| Servicio | Variables |
|---|---|
| ra-* | `DATABASE_URL` (secreto), `GO2RTC_USER`/`GO2RTC_PASSWORD`, `RA_MEDIA_TOKEN`, `AI_DEVICE`/`CLIP_DEVICE=cuda`, `RECORDER_TZ`. Sin `TZ`: los segmentos se nombran e indexan en UTC. Detalle en `ra/README.md`. |
| thot | `THOT_SECRETO`, `AMON_URL`, `GO2RTC_*`, `THOT_GO2RTC_RTSP`, `THOT_TURN_URLS`, `THOT_TURN_SECRETO`, `THOT_ICE_SERVERS`, `THOT_CALIDAD_DIFUSION`. Ver `ra/thot/README.md`. |
| wadjet | `CUBO_INGESTA_URL`, `CUBO_GATEWAY_SECRET` (= `SEKHMET_GATEWAY_SECRET`), `TCP_PORT`, `HTTP_PORT`. Ver `ra/wadjet/README.md`. |
| coturn | `listening-port=7178`, `min-port=7180`, `max-port=7199`, `external-ip=186.96.163.115/10.19.5.244`, `use-auth-secret` con `--static-auth-secret` desde `.env` (`THOT_TURN_SECRETO`). |

## Actualizar un servicio

`/srv/cuboip/actualizar.sh` recibe el código, aplica `parches/`, construye con el BuildKit propio,
recrea el contenedor y borra solo la imagen anterior de ese servicio.

```bash
# Desde una máquina con acceso a GitHub (el servidor no guarda credenciales):
git -C amon fetch origin && git -C amon archive origin/development \
  | ssh developer@10.19.5.244 /srv/cuboip/actualizar.sh amon --stdin
git -C horus fetch origin && git -C horus archive origin/development \
  | ssh developer@10.19.5.244 /srv/cuboip/actualizar.sh horus --stdin
git -C ra fetch origin && git -C ra archive origin/development \
  | ssh developer@10.19.5.244 /srv/cuboip/actualizar.sh ra --stdin

# Reconstruir con el código que ya está en src/:
/srv/cuboip/actualizar.sh ra-ai-worker --sin-codigo
```

Servicios: `amon horus ra-recorder ra-tracker ra-clip ra-ai-worker ollama`, `ra` (los de ra) o
`todo`.

**Despliegue coordinado.** `actualizar.sh <servicio> --stdin` reemplaza **todo** el código del
servicio con lo que recibe. Varias personas y sesiones despliegan al mismo .244: antes de desplegar
una rama, `git fetch` y une `origin/development` en ella (o despliega development con la rama ya
unida). Si no, borras lo que otro desplegó minutos antes. Lo que se despliegue desde una rama sin
unir se pierde en el siguiente despliegue desde development.

Cambios en `.env`: respaldar antes (`.env.bak-<motivo>-<fecha>`) y recrear el contenedor afectado
(`docker compose -p cuboip up -d amon`); un `restart` no relee el `.env`.

Si buildx se queda quieto después de "importing to docker … DONE", la imagen ya está cargada:
Ctrl+C y `docker compose -p cuboip up -d <servicio>`.

## GPU: los contenedores pierden la tarjeta

ra-clip, ra-ai-worker y ollama reservan la RTX A5000 (consumo aproximado: clip 1.6 GB, ai-worker
1.3 GB, ollama con qwen2.5:7b 5.1 GB; otros procesos del servidor usan unos 5 GB).

**Síntomas**

- El copiloto tarda más de un minuto en responder.
- `docker exec cuboip-ollama /opt/ollama/bin/ollama ps` muestra el modelo al `100% CPU`.
- `docker exec cuboip-ollama nvidia-smi -L` (o en ra-ai-worker / ra-clip) responde
  `Failed to initialize NVML: Unknown Error`.
- La IA de video se vuelve lenta o deja de generar detecciones.

**Arreglo**

```bash
cd /srv/cuboip
docker compose -p cuboip up -d --force-recreate ollama ra-ai-worker ra-clip
```

**Verificación**

```bash
for c in cuboip-ollama cuboip-ra-ai-worker cuboip-ra-clip; do docker exec $c nvidia-smi -L; done
docker exec cuboip-ollama /opt/ollama/bin/ollama ps     # debe decir 100% GPU
```

El 2026-10-02 el chat del copiloto pasó de 73 s a 0.3 s tras recrearlos. Causa probable: una
recarga de systemd en el host desconecta los cgroups de dispositivos NVIDIA de los contenedores ya
creados; puede repetirse. Un `restart` no basta: hay que recrear.

## Carpetas de `/srv/cuboip`

| Ruta | Uso |
|---|---|
| `.env` | Secretos y conexiones. No copiar ni versionar. |
| `docker-compose.yml`, `docker-bake.hcl` | Servicios e imágenes. |
| `config/` | `go2rtc.yaml`, `horus-nginx.conf` (incluye `/thot/`), coturn, imagen de Ollama, BuildKit. |
| `tls/` | CA "CuboIP Desarrollo CA" y certificado del .244 (la llave de la CA no sale del servidor). |
| `src/{amon,horus,ra}` | Código con el que se construyeron las imágenes. |
| `parches/` | Commits que se aplican sobre development si aún no los trae. |
| `data/dataprotection-keys` | Anillo de llaves de amon. **Respaldar.** |
| `data/recordings`, `data/faces`, `data/minio`, `data/redis`, `data/models`, `data/ollama` | Datos y modelos. |
| `logs/` | Bitácoras de construcción. |

## Si algo falla

- amon: `docker logs cuboip-amon`; salud en `http://10.19.5.244:7101/health` o
  `https://cubo.servicios360.com.mx/health`.
- Cámaras: `camaras.video_estado` o `GET api/Video/{id}/fuente`.
- Video del agente que no abre fuera de la LAN: revisar `THOT_URL_EMISOR` (debe ser el dominio
  público) y el NAT de TURN (Pendiente): con TURN configurado la app no usa el camino por el
  servidor, así que sin esa NAT el video por datos móviles no conecta.
- Disco raíz: las imágenes de Docker viven en `/` y hay poco espacio; no dejar imágenes viejas.

## Pendientes

- **Pendiente:** NAT de TURN (3478 udp/tcp → 7178 y 7180-7199/udp).
- **Pendiente:** NAT de mafdet (3011-3013 → 7151-7153) y el propio mafdet (en desarrollo).
- **Pendiente:** Origin CA de Cloudflare en el proxy y SSL Full (strict).
- **Pendiente:** `MINIO_PUBLIC_URL` en amon (unir `feat/minio-url-publica`).
- **Pendiente:** versionar `proxy-publico/` y `analitica/` en development.
- **Pendiente:** charts de Kubernetes para thot, wadjet y coturn (hoy solo existen en el compose del .244).
