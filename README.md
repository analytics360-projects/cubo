# cubo — infraestructura de CuboIP

Repositorio de despliegue de CuboIP: charts de Helm para el cluster (microk8s), scripts de
instalación de servidores y guías de los ambientes. No tiene código de la aplicación: el backend
es `amon`, el front `horus` y los servicios de video e IA `ra`.

Mapa completo del sistema (componentes, URLs públicas, puertos, NAT, apps móviles y guía para el
equipo de validación): `amon/docs/README-sistema.md` en el repo `amon`.

## Contenido

| Ruta | Qué es |
|---|---|
| `Infrastructure/<servicio>/` | Charts de Helm por servicio (amon, horus, go2rtc, ra-recorder, ra-clip, ra-ai-worker, ra-tracker, ollama, jaeger y los servicios heredados de PCM). |
| `Infrastructure/*-configurations.yaml` | ConfigMaps de cada servicio (`amon-configurations.yaml`, etc.). |
| `Infrastructure/README-video.md` | Despliegue del video y la visión en el cluster: go2rtc, ra, GPU, Secrets, TURN y copiloto. |
| `Infrastructure/go2rtc/README.md` | ICE, candidatos y TURN de go2rtc. |
| `deploy`, `deploy_360`, `deploy_monitor` | Scripts de despliegue al cluster (regcred contra Docker Hub, instalación de charts). |
| `db.sh` | Instala PostgreSQL 16 con PostGIS, pgvector, pg_trgm, unaccent, partman y cron, y crea las extensiones en la base de amon. |
| `minio.sh` | Instala MinIO como servicio del sistema. |
| `superset.sh` | Instalación antigua de Superset en Ubuntu (reemplazada por `analitica/`). |
| `redis_install` | Instalación de Redis. |
| `argocd-service-nodeport.yaml` | NodePort de Argo CD. |
| `docs/despliegue-244.md` | Ambiente de pruebas y público en 10.19.5.244: compose, puertos, NAT, proxy, variables, actualizaciones y recuperación de la GPU. |

Fuera de `development`, todavía:

- `analitica/`: CuboIP Analítica (Superset 6.1 con la marca de CuboIP, VM 10.19.5.243). Hoy solo
  está en la rama `feat/video`, con cambios locales sin commit. Su README es la guía del stack.
- `proxy-publico/`: configuración de nginx del proxy público (VM 10.19.5.242) y su README. Aún
  **sin versionar**: existe solo en el checkout principal de `cubo`.

## Ambientes

| Ambiente | Dónde | Guía |
|---|---|---|
| Pruebas y acceso público (`https://cubo.servicios360.com.mx`) | Docker Compose en 10.19.5.244, base en 10.19.5.100, proxy en 10.19.5.242, Superset en 10.19.5.243 | `docs/despliegue-244.md` |
| Cluster | microk8s con los charts de `Infrastructure/` | `Infrastructure/README-video.md` |

## Reglas

- Los secretos no se versionan: van en `.env` del servidor o en Secrets de Kubernetes. Al
  documentar, solo el nombre de la variable y su propósito.
- Cada componente nuevo lleva nombre de dios (amon, horus, ra, thot, wadjet, sekhmet, hathor,
  mafdet…); en la interfaz de usuario los nombres son descriptivos.
