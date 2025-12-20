#!/bin/bash

set -e

# Actualizar lista de paquetes
apt update

# Instalar PostgreSQL y utilidades
apt install postgresql postgresql-contrib -y
apt install -y libpq-dev python3-dev build-essential

# Permitir tráfico en el puerto 5432 si UFW está disponible
if command -v ufw >/dev/null 2>&1; then
    ufw allow 5432
fi

# Instalar PostGIS
apt install postgis -y
apt install postgresql-16-partman -y
apt install postgresql-16-cron -y

# Cambiar contraseña del usuario postgres
su - postgres -c "psql -c \"ALTER ROLE postgres WITH PASSWORD '30083008';\""

# Obtener la versión principal de PostgreSQL instalada
PG_VERSION=$(psql -t -P format=unaligned -c "SHOW server_version;" | cut -d '.' -f1)
CONFIG_PATH="/etc/postgresql/${PG_VERSION}/main"

echo "Versión de PostgreSQL detectada: $PG_VERSION"
echo "Ruta de configuración: $CONFIG_PATH"

# Modificar postgresql.conf
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/g" "$CONFIG_PATH/postgresql.conf"

# Modificar pg_hba.conf si no está ya configurado
if ! grep -q "^host\s\+all\s\+all\s\+0.0.0.0/0\s\+md5" "$CONFIG_PATH/pg_hba.conf"; then
    echo "host    all             all             0.0.0.0/0               md5" >> "$CONFIG_PATH/pg_hba.conf"
fi

# Reiniciar PostgreSQL
systemctl restart postgresql

# Crear extensiones PostGIS
EXTENSIONS=(
    "postgis"
    "postgis_raster"
    "postgis_topology"
    "postgis_sfcgal"
    "fuzzystrmatch"
    "address_standardizer"
    "address_standardizer_data_us"
    "postgis_tiger_geocoder"
    "pg_partman"
    "pg_cron"
)

for EXT in "${EXTENSIONS[@]}"; do
    su - postgres -c "psql -d postgres -c \"CREATE EXTENSION IF NOT EXISTS $EXT;\""
done

echo "PostgreSQL y PostGIS configurados correctamente para la versión $PG_VERSION."
