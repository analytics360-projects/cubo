# Proxy público de CuboIP

```
Internet → Cloudflare (proxy naranja, SSL Full strict) → NAT IP pública :443/:80
        → inf-proxy-cuboip-01 (10.19.5.242, nginx) → sistemas internos
```

| | |
|---|---|
| Dominio | `cubo.servicios360.com.mx` (único) |
| VM | `inf-proxy-cuboip-01`, Proxmox 360 (10.19.5.11), VMID 121, 2 vCPU / 4 GB / 20 GB, Ubuntu 24.04 |
| IP | 10.19.5.242/24, gw 10.19.5.1, DNS 10.19.5.250 |
| SSH | `ubuntu@10.19.5.242` con la llave de `heber@mac`, solo desde 10.19.0.0/16 |
| Config | `/etc/nginx/conf.d/cuboip-publico.conf` (fuente: `nginx/cuboip-publico.conf`) |
| Certificado | `/etc/nginx/tls/origin.crt` y `origin.key` (Origin CA de Cloudflare) |

## Rutas (un solo dominio: `cubo.servicios360.com.mx`)

| URL | Sistema | Destino interno |
|---|---|---|
| `/` | CuboIP (horus) | `https://10.19.5.244:7143` |
| `/api/…`, `/notifications`, `/ari`, `/health` | API (amon), con WebSocket | `http://10.19.5.244:7101` |
| `/analitica/…` | CuboIP Analítica (Superset, `SUPERSET_APP_ROOT=/analitica`) | `https://10.19.5.243` |
| `/s3/…` | Archivos (MinIO), solo GET/HEAD con URL firmada | `http://10.19.5.244:7110`, con `Host: minio:9000` |
| `/api/v1/(chart\|dashboard)/N/thumbnail/` | Miniaturas de Superset (las arma sin subruta) | 302 a `/analitica/api/v1/…` |
| `/thot/…` | Señalización del video (thot): WebSocket de la app del agente, espectadores y página del celular | `https://10.19.5.244:7143` (nginx de horus → thot), con WebSocket |
| `/api/VideoInterno` | bloqueado (solo go2rtc por dentro) | 403 |
| `/api/Thot/senal/evento` | bloqueado (avisos internos thot → amon) | 403 |
| `/cubo` | redirige a `/` | 301 |
| Otro host o acceso por IP | se cierra sin responder | — |

Orden: `/analitica/` lleva la diagonal final para no atrapar `/analiticas-ia` de horus.

### `/s3` y la firma de MinIO

amon firma contra `MINIO_ENDPOINT` y, con `MINIO_PUBLIC_URL=/s3`, cambia el origen de la URL por `/s3`
(rama `feat/minio-url-publica` de amon). La firma cubre el Host y la ruta exactos. Por eso el proxy
quita `/s3` de la ruta **cruda** (`$request_uri`, sin normalizar `//` ni `%XX`) y reenvía con el Host
de `MINIO_ENDPOINT`: `minio:9000` en el staging, `10.19.5.96:9000` en microk8s. Si cambia el endpoint,
cambia también `proxy_set_header Host` en `location ^~ /s3/`.

## Balanceo

Cada sistema es un `upstream`. Para repartir la carga, agrega un `server` por réplica o nodo
(p. ej. los NodePort 32000/32003 de cada nodo microk8s) y recarga con `sudo nginx -t && sudo systemctl reload nginx`.

## Firewall y Cloudflare

- ufw: 22, 80 y 443 desde 10.19.0.0/16. Además, 80 y 443 solo desde los rangos de Cloudflare.
- `/usr/local/sbin/cloudflare-ips.sh` (fuente: `cloudflare-ips.sh`) regenera los rangos en
  `cloudflare-realip.conf` y en ufw. Corre cada semana con `cloudflare-ips.timer`.
- nginx toma la IP real del visitante de `CF-Connecting-IP`, así que amon la recibe en `X-Real-IP` y `X-Forwarded-For`.

## Cargar el certificado Origin CA

En Cloudflare → SSL/TLS → Origin Server → Create Certificate: RSA, host `cubo.servicios360.com.mx`
(o `*.servicios360.com.mx`), 15 años. Luego:

```sh
sudo tee /etc/nginx/tls/origin.crt   # pegar el certificado
sudo tee /etc/nginx/tls/origin.key   # pegar la llave privada
sudo chgrp www-data /etc/nginx/tls/origin.key && sudo chmod 640 /etc/nginx/tls/origin.key
sudo nginx -t && sudo systemctl reload nginx
```

Después se cambia SSL/TLS a **Full (strict)**. Mientras siga el certificado autofirmado provisional,
usa **Full**, nunca Flexible.

## Límites conocidos

- Cloudflare no pasa UDP. El video de celulares por datos móviles va por WebSocket (`/thot/`); con
  la app del agente en segundo plano hace falta TURN, que va directo por NAT y no por este proxy:
  coturn en el .244 (7178, relevo 7180-7199/udp). **Pendiente** el NAT 3478 udp/tcp → 7178 y
  7180-7199/udp. Ver `docs/despliegue-244.md`.
- WebRTC (UDP 7155 en el .244) no pasa por Cloudflare. El video cae en automático a MSE por WebSocket,
  que sí pasa. Lo que se pierde es el audio hacia la cámara.
- Mientras amon no tenga `MINIO_PUBLIC_URL`, las URLs prefirmadas siguen con el origen interno
  (`http://minio:9000/…`) y los planos y audios no cargan desde fuera.
