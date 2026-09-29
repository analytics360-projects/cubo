# go2rtc (CuboIP)

Servidor de video interno de CuboIP. Recibe las cámaras (RTSP) y las re-sirve a:

| Consumidor | Cómo | Puerto |
|---|---|---|
| amon | API REST + WebSocket (`GO2RTC_URL=http://go2rtc:1984`, basic auth) | 1984 (ClusterIP) |
| ra-ai-worker, ra-recorder | RTSP (`rtsp://user:pass@go2rtc:8554/<vision_id>`) | 8554 (ClusterIP) |
| navegador | **solo** los medios WebRTC (ICE). La señalización SDP pasa por amon | `webrtc.port` tcp+udp |

El navegador nunca llama a la API de go2rtc: amon valida el JWT y los permisos de
la cámara y reenvía MSE (WebSocket) y la oferta/respuesta SDP de WebRTC.
**1984 y 8554 nunca se exponen fuera del cluster.**

Versión fija: `alexxit/go2rtc:1.9.10` (probada: sustitución `${VAR}` en el yaml,
401 sin credenciales y 200 con ellas).

## Credenciales

API y RTSP usan el mismo usuario/contraseña, del Secret `go2rtc-credentials`
(llaves `username` y `password`). Lo leen también amon, ra-ai-worker y ra-recorder.

```bash
kubectl create secret generic go2rtc-credentials \
  --from-literal=username=go2rtc \
  --from-literal=password="$(openssl rand -hex 24)"
```

Usa una contraseña sin `@ : / ? # %` (p. ej. hex): ra la mete dentro de la URL RTSP
(`rtsp://$(GO2RTC_USER):$(GO2RTC_PASSWORD)@go2rtc:8554`). Si lleva esos caracteres
tiene que ir url-encoded.

Alternativa (no recomendada, deja la clave en el values): `credentials.create=true`
con `credentials.username/password`; el template falla si van vacíos.

## WebRTC / ICE

ICE anuncia al navegador **el puerto en el que escucha go2rtc**, no el del Service.
Dos modos (`webrtc.mode`):

- `nodePort` (por defecto): Service NodePort tcp+udp. `webrtc.port` debe ser igual
  al nodePort (30000-32767; por defecto **30555**) y los candidatos
  `IP_PUBLICA:30555`.
- `hostNetwork`: el pod usa la red del nodo y escucha `webrtc.port` directo
  (p. ej. `--set webrtc.mode=hostNetwork --set webrtc.port=8555`). El puerto queda
  ocupado en el nodo; una sola réplica.

Candidatos (`webrtc.candidates`): lo que go2rtc anuncia además de las IPs del pod.
Sin candidatos el navegador solo vería IPs internas del cluster y no conectaría.

```yaml
webrtc:
  mode: nodePort
  port: 30555
  candidates:
    - 203.0.113.10:30555     # IP pública (o de la LAN de los operadores)
    - stun:30555             # o que go2rtc descubra su IP pública por STUN
```

Redes con NAT simétrico o que bloquean UDP: montar un TURN (coturn, 3478 udp/tcp y
5349 tls) y declararlo en `webrtc.iceServers` (lado servidor) **y** en el cliente
(la configuración ICE que amon entregue al navegador). Si WebRTC no conecta, el
reproductor debe caer a MSE por WebSocket (que va entero por amon, puerto HTTP).

## Puertos a abrir en el servidor

| Puerto | Proto | Para |
|---|---|---|
| `webrtc.port` (30555 con nodePort, 8555 con hostNetwork) | UDP y TCP | ICE de WebRTC desde los navegadores |
| 3478 / 5349 (solo si hay TURN propio) | UDP/TCP | TURN |

Nada más: el resto del video (MSE, snapshot, señalización) entra por el puerto de amon.

## Instalar

```bash
helm upgrade --install go2rtc Infrastructure/go2rtc -n <ns> \
  --set 'webrtc.candidates={203.0.113.10:30555}'
```
