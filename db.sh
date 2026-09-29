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
# pgvector: embeddings de visión (búsqueda forense, ReID, reconocimiento facial) en el
# esquema vision de amon. pg_trgm (contrib) acelera la búsqueda parcial de placas. Sin
# ellas amon crea el esquema igual, sin esas columnas/índices (WARNING en el log).
# unaccent (contrib) la usan la búsqueda en narrativas, los detenidos de integración y
# Sepomex. amon también intenta crear unaccent, pg_trgm y postgis en su migración
# ExtensionesBase, pero si su usuario no es superusuario solo deja un aviso en el log.
apt install postgresql-16-pgvector -y

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
    "vector"
    "pg_trgm"
    "unaccent"
)

# Las extensiones se crean en la base que usa amon, no en "postgres" (antes se creaban
# siempre ahí y la base de amon se quedaba sin ellas si era otra). La base sale, en este
# orden, del primer argumento, de AMON_DB o del Database= de POSTGRESCONNECTIONSTRING;
# si no hay ninguno, "postgres" (el valor de Infrastructure/amon-configurations.yaml).
# Ejemplo: sudo AMON_DB=cuboip ./db.sh
AMON_DB="${1:-${AMON_DB:-}}"
if [ -z "$AMON_DB" ] && [ -n "${POSTGRESCONNECTIONSTRING:-}" ]; then
    AMON_DB=$(echo "$POSTGRESCONNECTIONSTRING" | tr ';' '\n' | sed -n 's/^[[:space:]]*[Dd]atabase[[:space:]]*=[[:space:]]*//p' | head -n1)
fi
AMON_DB="${AMON_DB:-postgres}"
if ! [[ "$AMON_DB" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo "Nombre de base no válido: '$AMON_DB'" >&2
    exit 1
fi
echo "Base de amon: $AMON_DB"

# La base se crea si no existe, para que las extensiones queden en ella desde el inicio.
if [ "$(su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname = '$AMON_DB'\"")" != "1" ]; then
    su - postgres -c "createdb $AMON_DB"
fi

for EXT in "${EXTENSIONS[@]}"; do
    su - postgres -c "psql -d $AMON_DB -c \"CREATE EXTENSION IF NOT EXISTS $EXT;\""
done

echo "PostgreSQL y PostGIS configurados correctamente para la versión $PG_VERSION (extensiones en la base $AMON_DB)."
