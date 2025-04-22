#!/bin/bash

set -e

echo "🔄 Actualizando sistema..."
apt update && apt upgrade -y

echo "📦 Descargando e instalando MinIO..."
wget https://dl.min.io/server/minio/release/linux-amd64/archive/minio_20240113075303.0.0_amd64.deb
dpkg -i minio_20240113075303.0.0_amd64.deb

echo "👤 Creando usuario y grupo minio-user..."
groupadd -r minio-user
useradd -M -r -g minio-user minio-user

echo "📁 Creando directorio de datos..."
mkdir -p /mnt/data
chown minio-user:minio-user /mnt/data

echo "⚙️ Configurando entorno MINIO en /etc/default/minio..."
cat > /etc/default/minio <<EOF
MINIO_VOLUMES="/mnt/data"
MINIO_OPTS="--certs-dir /home/minio/.minio/certs --console-address :9001"
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
EOF

echo "🌐 Permitiendo puertos 9000 y 9001 en UFW..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 9000:9001/tcp
fi

echo "📥 Descargando e instalando certgen..."
wget https://github.com/minio/certgen/releases/download/v1.2.0/certgen_1.2.0_linux_amd64.deb
dpkg -i certgen_1.2.0_linux_amd64.deb

echo "🔐 Generando certificados TLS..."
certgen -host "$(hostname -I | awk '{print $1}')"

echo "📁 Moviendo certificados a la ruta correspondiente..."
mkdir -p /home/minio/.minio/certs
mv private.key public.crt /home/minio/.minio/certs
chown -R minio-user:minio-user /home/minio/.minio/certs

echo "🛠️ Creando archivo systemd para MinIO..."

cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO Object Storage
Documentation=https://min.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=minio-user
Group=minio-user
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server \$MINIO_VOLUMES \$MINIO_OPTS
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Recargando systemd y habilitando servicio..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable minio
systemctl start minio

echo "✅ MinIO ha sido instalado y está corriendo:"
systemctl status minio --no-pager
