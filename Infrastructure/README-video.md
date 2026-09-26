# Video y visión de CuboIP: despliegue

```
navegador ──HTTPS/WSS──▶ amon (JWT + permiso de cámara, pase de un solo uso)
    │                     │  API/WS basic auth (ClusterIP go2rtc:1984)
    │  medios WebRTC      ▼
    └──UDP/TCP ICE──────▶ go2rtc ◀── RTSP de las cámaras
                          │ RTSP con auth (ClusterIP go2rtc:8554)
                          ├──▶ ra-recorder ──▶ PVC ra-recordings
                          └──▶ ra-ai-worker (GPU, StatefulSet) ──▶ ra-clip:8001 (GPU)
                                   │
                   Postgres: esquema vision (lo crea amon) ── NOTIFY vision_alert ──▶ amon ──SignalR──▶ navegador
```

## Requisitos del cluster

- **GPU NVIDIA** para ra-clip y ra-ai-worker: driver NVIDIA en el nodo y el device
  plugin (`microk8s enable gpu` lo instala y crea la RuntimeClass `nvidia`). Si el
  cluster exige RuntimeClass, poner `runtimeClassName: nvidia` en ambos charts.
  Comprobar: `kubectl describe node | grep nvidia.com/gpu`. Sin GPU se puede
  desplegar con `gpu.count=0` (CPU, solo pruebas: muy lento).
- **pgvector** en el Postgres (`postgresqllocal`): la imagen debe ser
  `pgvector/pgvector:pg16` (o tener la extensión instalada). Sin pgvector amon crea
  el esquema `vision` igual pero sin columnas de embeddings (búsqueda forense,
  ReID, reconocimiento facial desactivados); al instalarlo, correr
  `SELECT vision.ensure_vector();`. El esquema `vision` lo crea la migración de
  amon (no hay que correr SQL a mano).
- Volúmenes: `ra-recordings` (grabaciones + snapshots + rostros), `ra-ai-models`,
  `ra-clip-cache`. Con **ReadWriteOnce** (microk8s-hostpath) ra-recorder y
  ra-ai-worker tienen que caer en el mismo nodo; en varios nodos usar una
  storageClass **ReadWriteMany** (NFS) para `ra-recordings`.

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

# Llave con la que amon cifra las URLs RTSP (con usuario/contraseña) de las cámaras.
# NO perderla: sin ella no se pueden descifrar las fuentes guardadas.
kubectl -n $NS create secret generic amon-video \
  --from-literal=credentials_key="$(openssl rand -base64 32)"
```

## Orden de despliegue

1. Postgres con pgvector (ver arriba) y los Secrets.
2. amon con las variables nuevas (`amon-configurations.yaml` + chart amon). Al
   arrancar aplica la migración que crea `vision`, sincroniza las cámaras a
   `vision.cameras` y registra sus streams en go2rtc.
3. `go2rtc` con los candidatos WebRTC públicos:
   `helm upgrade --install go2rtc Infrastructure/go2rtc -n $NS --set 'webrtc.candidates={IP_PUBLICA:30555}'`
   (amon vuelve a registrar los streams por sí solo; go2rtc no los persiste).
4. `ra-recorder` (crea el PVC `ra-recordings`).
5. `ra-clip` (la primera vez descarga modelos al PVC de caché; para los pesos ReID
   domain-generalized ver `scripts/download_reid_weights.sh` en ra).
6. `ra-ai-worker` (`--set replicaCount=N` para repartir cámaras entre N réplicas).

Imágenes: `heberestrada/images:ra-ai-worker_latest`, `ra-clip_latest` (construidas
con `TORCH_INDEX=https://download.pytorch.org/whl/cu121` y, clip, `GPU=1`) y
`ra-recorder_latest`, con el mismo `regcred` que el resto.

## Puertos a abrir en el servidor

| Puerto | Proto | Para |
|---|---|---|
| NodePort de amon (32003) | TCP | API, MSE por WebSocket, snapshot y señalización WebRTC (ya abierto) |
| 30555 (webrtc.mode=nodePort) **o** 8555 (hostNetwork) | UDP y TCP | ICE de WebRTC desde el navegador |
| 3478 udp/tcp, 5349 tcp (solo con TURN propio) | | TURN |

**Nunca** exponer 1984 (API go2rtc) ni 8554 (RTSP): van por ClusterIP y exigen
usuario/contraseña. Detalle de ICE, candidatos y TURN en `go2rtc/README.md`.
