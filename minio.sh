#!/bin/bash

set -e

MINIO_DEB="minio_20240113075303.0.0_amd64.deb"
CERTGEN_DEB="certgen_1.2.0_linux_amd64.deb"
MINIO_URL="https://dl.min.io/server/minio/release/linux-amd64/archive/$MINIO_DEB"
CERTGEN_URL="https://github.com/minio/certgen/releases/download/v1.2.0/$CERTGEN_DEB"

echo "🔄 Actualizando sistema..."
apt update && apt upgrade -y

echo "📦 Descargando MinIO .deb..."

# Intentar descarga limpia y válida de MinIO
download_minio() {
    rm -f "$MINIO_DEB"
    wget "$MINIO_URL"
    FILE_SIZE=$(stat -c%s "$MINIO_DEB")
    if [ "$FILE_SIZE" -lt 20000000 ]; then
        echo "❌ Archivo de MinIO incompleto o corrupto (<20MB). Reintentando..."
        rm -f "$MINIO_DEB"
        return 1
    fi
    echo "✅ MinIO descargado correctamente ($((FILE_SIZE / 1024 / 1024)) MB)"
    return 0
}

until download_minio; do
    echo "Reintentando descarga..."
    sleep 2
done

dpkg -i "$MINIO_DEB"
rm -f "$MINIO_DEB"

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

echo "🌐 Configurando firewall (puertos 9000 y 9001)..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 9000:9001/tcp
fi

echo "📥 Descargando certgen..."
rm -f "$CERTGEN_DEB"
wget "$CERTGEN_URL"
dpkg -i "$CERTGEN_DEB"
rm -f "$CERTGEN_DEB"

echo "🔐 Generando certificados TLS..."
certgen -host "$(hostname -I | awk '{print $1}')"

echo "📁 Moviendo certificados a ruta de MinIO..."
mkdir -p /home/minio/.minio/certs
mv private.key public.crt /home/minio/.minio/certs
chown -R minio-user:minio-user /home/minio/.minio/certs

echo "🛠️ Creando archivo de servicio systemd..."
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

echo "🔁 Recargando systemd y activando servicio MinIO..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable minio
systemctl start minio

echo "✅ MinIO ha sido instalado y está corriendo:"
systemctl status minio --no-pager
