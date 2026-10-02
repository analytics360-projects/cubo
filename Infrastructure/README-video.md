# Video y visión de CuboIP: despliegue

```
navegador ──HTTPS/WSS──▶ amon (JWT + permiso de cámara, pase de un solo uso)
    │                     │  API/WS basic auth (ClusterIP go2rtc:1984)
    │  medios WebRTC      ▼
    └──UDP/TCP ICE──────▶ go2rtc ◀── RTSP de las cámaras
                          │ RTSP con auth (ClusterIP go2rtc:8554)
                          ├──▶ ra-recorder ──▶ PVC ra-recordings (+ subPath faces)
                          │     └─ contenedor media :8090 (ClusterIP ra-recorder, token) ◀── amon (lectura)
                          └──▶ ra-ai-worker (GPU, StatefulSet) ──▶ ra-clip:8001 (GPU) ◀── amon (CLIP_URL)
                                   │
                   Postgres: esquema vision (lo crea amon) ── NOTIFY vision_alert / vision_detections ──▶ amon ──SignalR──▶ navegador
                                   ▲
                          ra-tracker (1 réplica): identidad global y proyección a planta
```

amon **no monta** el PVC de ra: todo archivo de ra (reproducción y evidencia de
grabaciones, capturas de alertas/placas/eventos, recortes de rostros) lo pide al
servidor de medios (`VISION_MEDIA_URL`, contenedor `media` del pod de ra-recorder), así
funciona con cualquier número de réplicas de amon aunque el PVC sea ReadWriteOnce. Las
fotos de referencia que se suben al enrolar personas van al MinIO de amon
(`STORAGE_TYPE`). go2rtc alcanza a amon por el Service ClusterIP `amon-interno`
(`VIDEO_AMON_INTERNAL_URL`, MJPEG interno de Sense y Milestone).

## Requisitos del cluster

- **GPU NVIDIA** para ra-clip y ra-ai-worker: driver NVIDIA en el nodo y el device
  plugin (`microk8s enable gpu` lo instala y crea la RuntimeClass `nvidia`). Si el
  cluster exige RuntimeClass, poner `runtimeClassName: nvidia` en ambos charts.
  Comprobar: `kubectl describe node | grep nvidia.com/gpu`. Sin GPU se puede
  desplegar con `gpu.count=0` (CPU, solo pruebas: muy lento).
- **pgvector, PostGIS y pg_trgm** en el Postgres (`postgresqllocal`). Las tres son
  obligatorias para amon: pgvector para los embeddings de visión, PostGIS para la zona
  de los folios del 911 (`st_geomfromgeojson`; sin él falla ese cálculo) y pg_trgm para
  la búsqueda parcial de placas y de cruces de calles. En el servidor instalado con
  `db.sh` (Postgres 16 por apt) los paquetes son `postgis`, `postgresql-16-pgvector` y
  `postgresql-contrib`; `db.sh` crea las extensiones en la base `postgres`. Las
  extensiones son por base: si amon usa otra, créalas también ahí
  (`CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS vector;
  CREATE EXTENSION IF NOT EXISTS pg_trgm;`). En contenedor, `pgvector/pgvector:pg16`
  trae pgvector y pg_trgm pero **no PostGIS**: usa la imagen `postgres/` de ra
  (`FROM pgvector/pgvector:pg16` + `postgresql-16-postgis-3`, crea las tres al
  iniciar). Sin pgvector amon crea el esquema `vision` igual pero sin columnas de
  embeddings (búsqueda forense, ReID, reconocimiento facial desactivados); al
  instalarlo, correr `SELECT vision.ensure_vector();`. Sin pg_trgm la búsqueda parcial
  de placas funciona sin índice (más lenta). El esquema `vision` lo crea la migración
  de amon (no hay que correr SQL a mano).
- Volúmenes: `ra-recordings` (grabaciones + snapshots + subPath `faces` con los
  recortes de rostros), `ra-ai-models`, `ra-clip-cache`. Con **ReadWriteOnce**
  (microk8s-hostpath) ra-recorder y ra-ai-worker tienen que caer en el mismo nodo; en
  varios nodos usar una storageClass **ReadWriteMany** (NFS) para `ra-recordings`.
  amon no lo monta (usa el servidor de medios) y solo lleva un `emptyDir` de caché
  (`visionCache.sizeLimit`, 10Gi) por réplica.

## Secrets (crear antes de instalar)

```bash
NS=<namespace>
# Credenciales de go2rtc: API y RTSP. Las leen go2rtc, amon, ra-ai-worker y ra-recorder.
# Usar hex: la clave va dentro de la URL RTSP de ra (no debe llevar @ : / ? # %).
kubectl -n $NS create secret generic go2rtc-credentials \
  --from-literal=username=go2rtc --from-literal=password="$(openssl rand -hex 24)"

# Base de datos para los servicios ra (misma base que amon; entran al esquema vision
# por DB_SEARCH_PATH=vision,public).
kubectl -n $NS create secret generic ra-database \
  --from-literal=database_url='postgresql://USUARIO:CLAVE@postgresqllocal:5432/postgres'

# Token interno del servidor de medios de ra (lo leen ra-recorder, contenedor media, y amon).
kubectl -n $NS create secret generic ra-media-token \
  --from-literal=token="$(openssl rand -hex 32)"

```

Las URLs RTSP de las cámaras (con usuario y contraseña) las cifra amon con ASP.NET Data
Protection (`ICredentialProtector`, el mismo que las contraseñas de Hikvision; prefijo
`dp1:`). No hay llave que crear: el anillo de llaves se guarda en Redis
(`REDISCONNECTIONSTRING`, lista `amon:dataprotection:credentials`) o, si se define
`dataprotection_keys_path` en `amon-configurations`, en esa carpeta (montarla en un PVC).
Si el anillo se pierde, las fuentes guardadas quedan ilegibles y hay que volver a
capturarlas: respaldar Redis o usar la carpeta persistente.

## Orden de despliegue

1. Postgres con pgvector (ver arriba) y los Secrets.
2. amon con las variables nuevas (`amon-configurations.yaml` + chart amon). Al
   arrancar aplica la migración que crea `vision`, sincroniza las cámaras a
   `vision.cameras` y registra sus streams en go2rtc.
3. `go2rtc` con los candidatos WebRTC públicos:
   `helm upgrade --install go2rtc Infrastructure/go2rtc -n $NS --set 'webrtc.candidates={IP_PUBLICA:30555}'`
   (amon vuelve a registrar los streams por sí solo; go2rtc no los persiste).
4. `ra-recorder` (crea el PVC `ra-recordings`, el contenedor `media` y el Service
   ClusterIP `ra-recorder:8090`; el release debe llamarse `ra-recorder` para que
   `vision_media_url` de `amon-configurations` apunte bien).
5. `ra-clip` (la primera vez descarga modelos al PVC de caché; para los pesos ReID
   domain-generalized ver `scripts/download_reid_weights.sh` en ra).
6. `ra-ai-worker` (`--set replicaCount=N` para repartir cámaras entre N réplicas).
7. `ra-tracker` (siempre 1 réplica, `Recreate`): identidad global entre cámaras y
   proyección a planta. Solo Postgres, sin GPU ni volúmenes.

Imágenes: `heberestrada/images:ra-ai-worker_latest`, `ra-clip_latest` (construidas
con `TORCH_INDEX=https://download.pytorch.org/whl/cu121` y, clip, `GPU=1`),
`ra-recorder_latest` (recorder y servidor de medios, la misma imagen) y
`ra-tracker_latest` (`ra/tracker`), con el mismo `regcred` que el resto.

## Variables nuevas de amon (amon-configurations + Secret)

| Llave / Secret | Variable | Valor |
|---|---|---|
| `vision_media_url` | `VISION_MEDIA_URL` | `http://ra-recorder:8090` |
| Secret `ra-media-token` (`token`) | `VISION_MEDIA_TOKEN` | el mismo que `RA_MEDIA_TOKEN` del contenedor media |
| `vision_default_retention_days` | `VISION_DEFAULT_RETENTION_DAYS` | igual a `DEFAULT_RETENTION_DAYS` de ra-recorder |
| (fijo en el chart) | `VISION_CACHE_PATH` | `/cache/vision` (emptyDir) |
| `clip_url` | `CLIP_URL` | `http://ra-clip:8001` |
| `video_amon_internal_url` | `VIDEO_AMON_INTERNAL_URL` | `http://amon-interno:5001` (Service ClusterIP del chart amon) |
| `video_mjpeg_ffmpeg_raw` | `VIDEO_MJPEG_FFMPEG_RAW` | `mjpeg_cfr` (plantilla `ffmpeg:` del chart go2rtc, `-r 15`) |
| `video_mjpeg_max_fps` | `VIDEO_MJPEG_MAX_FPS` | `15` (mismo número que la plantilla) |

go2rtc lleva CPU reservada (`requests.cpu` 2000m): transcodifica subflujos y el MJPEG
de los VMS mientras alguien mira; sin reserva, con el nodo saturado, el primer
fragmento tardó más de 11 s en las pruebas.

## Puertos a abrir en el servidor

| Puerto | Proto | Para |
|---|---|---|
| NodePort de amon (32003) | TCP | API, MSE por WebSocket, snapshot y señalización WebRTC (ya abierto) |
| 30555 (webrtc.mode=nodePort) **o** 8555 (hostNetwork) | UDP y TCP | ICE de WebRTC desde el navegador |
| 3478 udp/tcp, 5349 tcp (solo con TURN propio) | | TURN |

**Nunca** exponer 1984 (API go2rtc) ni 8554 (RTSP): van por ClusterIP y exigen
usuario/contraseña. Detalle de ICE, candidatos y TURN en `go2rtc/README.md`.

## Video del agente y por SMS (thot) y TURN

El video de la app del agente (montu) y el video por SMS no pasan por go2rtc: los atiende
**thot** (`ra/thot`, Node + ffmpeg), con pases que emite amon (`amon/docs/thot/README.md`).

- Señalización y página del celular por WebSocket en `/thot/` y `/v/<código>` del mismo dominio
  (en el .244, detrás del nginx de horus). La URL que amon entrega a la app es `THOT_URL_EMISOR`
  y debe ser la pública (`wss://cubo.servicios360.com.mx/thot/`).
- `/api/Thot/senal/*` es solo para la red interna (thot → amon, firmado con `THOT_SECRETO`); el
  proxy público responde 403 en `/api/Thot/senal/evento`.
- Cloudflare no pasa UDP. La app del agente transmite por WebRTC nativo y necesita **TURN** fuera
  de la LAN. Solo cae al WebSocket a través de thot si amon no entrega TURN y la app está visible;
  con TURN configurado (como en el .244) no lo usa.
- TURN: coturn con credenciales efímeras (`use-auth-secret`). amon genera usuario y credencial con
  `THOT_TURN_SECRETO` (el mismo valor que `static-auth-secret` de coturn) y entrega
  `THOT_TURN_URLS` a la app. En el .244: coturn escucha en 7178 udp/tcp y releva en
  7180-7199/udp; el NAT público 3478 → 7178 y 7180-7199/udp está **Pendiente**.
- En el cluster todavía no hay chart de thot ni de coturn (**Pendiente**); el ejemplo de compose,
  nginx y coturn está en `ra/thot/deploy/`.

Guía del ambiente público, puertos y NAT: `docs/despliegue-244.md`.

## Ollama (copiloto de amon, fase 2)

Chart `Infrastructure/ollama`: Deployment + Service ClusterIP `ollama:11434` + PVC `ollama-models`
(modelos). Descarga al arrancar los modelos de `models` (el primero = `copilot_model` de
`amon-configurations`). CPU por defecto con `qwen2.5:1.5b`; producción con GPU:

```bash
helm upgrade --install ollama Infrastructure/ollama -n <ns> \
  --set 'models={qwen2.5:7b}' --set gpu.count=1 --set runtimeClassName=nvidia \
  --set resources.requests.memory=8Gi --set resources.limits.memory=16Gi
# y en amon-configurations: copilot_model: 'qwen2.5:7b', copilot_debate: 'true' (opcional)
```

Sin el chart (o `enabled: false`) el copiloto responde igual con las plantillas de sus
herramientas. Secret opcional `amon-plataforma` con `dahua_player_key` (reproductor SGVideo) y
`openai_api_key` (si `copilot_provider: openai`).
