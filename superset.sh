#!/bin/bash

# Script de instalación automática de Apache Superset en Ubuntu
# Uso: ./install_superset.sh

set -e

echo "🚀 Instalando Apache Superset en Ubuntu..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si el script se ejecuta como root
if [[ $EUID -eq 0 ]]; then
   print_error "No ejecutes este script como root"
   exit 1
fi

# Verificar versión de Python
print_status "Verificando versión de Python..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_status "Python $PYTHON_VERSION encontrado ✓"
else
    print_error "Se requiere Python 3.8 o superior. Versión actual: $PYTHON_VERSION"
    exit 1
fi

# Actualizar sistema
print_status "Actualizando paquetes del sistema..."
sudo apt update

# Instalar dependencias del sistema
print_status "Instalando dependencias del sistema..."
sudo apt install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    libsasl2-dev \
    libldap2-dev \
    default-libmysqlclient-dev \
    pkg-config

# Crear directorio para Superset
SUPERSET_DIR="$HOME/superset"
print_status "Creando directorio de Superset en $SUPERSET_DIR"
mkdir -p "$SUPERSET_DIR"
cd "$SUPERSET_DIR"

# Crear entorno virtual
print_status "Creando entorno virtual..."
python3 -m venv venv

# Activar entorno virtual
print_status "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
print_status "Actualizando pip..."
pip install --upgrade pip

# Actualizar setuptools y wheel
print_status "Actualizando setuptools y wheel..."
pip install --upgrade setuptools wheel

# Instalar Superset
print_status "Instalando Apache Superset..."
# Para Python 3.12, usar versión más reciente que sea compatible
pip install "apache-superset>=4.0.0"

# Instalar dependencias adicionales necesarias con versiones compatibles
print_status "Instalando dependencias adicionales..."
pip install flask-cors redis celery
pip install psycopg2-binary
pip install "marshmallow>=3.19.0,<4.0.0"
pip install Pillow  # Para screenshots y thumbnails
pip install "numpy>=1.24.0"  # Compatible con Python 3.12

# Crear configuración básica
print_status "Creando configuración básica..."
cat > superset_config.py << 'EOF'
# Configuración de Superset
import os

# Base de datos SQLite
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.expanduser("~/superset/superset.db")}'

# Clave secreta - CAMBIAR EN PRODUCCIÓN
SECRET_KEY = 'tu_clave_secreta_muy_segura_cambiar_en_produccion'

# Configuración de seguridad
WTF_CSRF_ENABLED = True

# Configurar logging
ENABLE_TIME_ROTATE = True
TIME_ROTATE_LOG_LEVEL = 'INFO'
FILENAME = f'{os.path.expanduser("~/superset")}/superset.log'

# Configuración CORS (simplificada)
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
}

# Configuración de cache (opcional)
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
}
EOF

# Configurar variables de entorno
export SUPERSET_CONFIG_PATH="$SUPERSET_DIR/superset_config.py"
export FLASK_APP=superset

# Inicializar base de datos
print_status "Inicializando base de datos..."
superset db upgrade

# Crear usuario administrador
print_status "Creando usuario administrador..."
echo "Por favor, introduce los datos del usuario administrador:"
superset fab create-admin

# Cargar ejemplos
read -p "¿Deseas cargar los ejemplos de datos? (y/N): " load_examples
if [[ $load_examples =~ ^[Yy]$ ]]; then
    print_status "Cargando ejemplos..."
    superset load_examples
fi

# Inicializar Superset
print_status "Inicializando Superset..."
superset init

# Crear script de inicio
print_status "Creando script de inicio..."
cat > start_superset.sh << EOF
#!/bin/bash
cd "$SUPERSET_DIR"
source venv/bin/activate
export SUPERSET_CONFIG_PATH="$SUPERSET_DIR/superset_config.py"
export FLASK_APP=superset
superset run -h 0.0.0.0 -p 8088 --with-threads
EOF

chmod +x start_superset.sh

# Crear script para activar entorno
cat > activate_superset.sh << EOF
#!/bin/bash
cd "$SUPERSET_DIR"
source venv/bin/activate
export SUPERSET_CONFIG_PATH="$SUPERSET_DIR/superset_config.py"
export FLASK_APP=superset
echo "Entorno de Superset activado. Ejecuta 'superset run -p 8088' para iniciar."
exec bash
EOF

chmod +x activate_superset.sh

# Configurar como servicio systemd
read -p "¿Deseas instalar Superset como servicio para que esté siempre en línea? (Y/n): " install_service
if [[ ! $install_service =~ ^[Nn]$ ]]; then
    print_status "Configurando Superset como servicio systemd..."
    
    # Crear archivo de servicio
    sudo tee /etc/systemd/system/superset.service > /dev/null << EOF
[Unit]
Description=Apache Superset
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SUPERSET_DIR
Environment=SUPERSET_CONFIG_PATH=$SUPERSET_DIR/superset_config.py
Environment=FLASK_APP=superset
ExecStart=$SUPERSET_DIR/venv/bin/superset run -h 0.0.0.0 -p 8088 --with-threads
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Recargar systemd y habilitar servicio
    sudo systemctl daemon-reload
    sudo systemctl enable superset
    
    # Preguntar si iniciar ahora
    read -p "¿Deseas iniciar el servicio ahora? (Y/n): " start_now
    if [[ ! $start_now =~ ^[Nn]$ ]]; then
        sudo systemctl start superset
        print_status "Servicio iniciado. Verificando estado..."
        sleep 3
        
        if sudo systemctl is-active --quiet superset; then
            print_status "✅ Superset está ejecutándose como servicio"
            echo "   Estado: $(sudo systemctl is-active superset)"
            echo "   Puerto: 8088"
        else
            print_warning "⚠️  El servicio no se inició correctamente"
            echo "   Revisa los logs con: journalctl -u superset -f"
        fi
    fi
    
    # Crear script para gestionar el servicio
    cat > manage_superset_service.sh << EOF
#!/bin/bash
# Script para gestionar el servicio de Superset

case \$1 in
    start)
        echo "Iniciando Superset..."
        sudo systemctl start superset
        ;;
    stop)
        echo "Deteniendo Superset..."
        sudo systemctl stop superset
        ;;
    restart)
        echo "Reiniciando Superset..."
        sudo systemctl restart superset
        ;;
    status)
        echo "Estado del servicio Superset:"
        sudo systemctl status superset
        ;;
    logs)
        echo "Logs de Superset (Ctrl+C para salir):"
        journalctl -u superset -f
        ;;
    enable)
        echo "Habilitando inicio automático..."
        sudo systemctl enable superset
        ;;
    disable)
        echo "Deshabilitando inicio automático..."
        sudo systemctl disable superset
        ;;
    *)
        echo "Uso: \$0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start    - Iniciar Superset"
        echo "  stop     - Detener Superset"
        echo "  restart  - Reiniciar Superset"
        echo "  status   - Ver estado del servicio"
        echo "  logs     - Ver logs en tiempo real"
        echo "  enable   - Habilitar inicio automático"
        echo "  disable  - Deshabilitar inicio automático"
        ;;
esac
EOF

    chmod +x manage_superset_service.sh
    print_status "Script de gestión de servicio creado: manage_superset_service.sh"
fi

# Información final
print_status "¡Instalación completada!"
echo ""
echo "📍 Directorio de instalación: $SUPERSET_DIR"
echo "🔧 Archivo de configuración: $SUPERSET_DIR/superset_config.py"
echo "🚀 Para iniciar manualmente: $SUPERSET_DIR/start_superset.sh"
echo "⚙️  Para activar entorno: $SUPERSET_DIR/activate_superset.sh"

if [[ ! $install_service =~ ^[Nn]$ ]]; then
    echo "🔧 Gestión de servicio: $SUPERSET_DIR/manage_superset_service.sh"
    echo ""
    echo "Comandos de servicio útiles:"
    echo "  sudo systemctl status superset    # Ver estado"
    echo "  sudo systemctl start superset     # Iniciar"
    echo "  sudo systemctl stop superset      # Detener"
    echo "  sudo systemctl restart superset   # Reiniciar"
    echo "  journalctl -u superset -f         # Ver logs"
    echo ""
    echo "O usa el script de gestión:"
    echo "  ./manage_superset_service.sh status"
    echo "  ./manage_superset_service.sh logs"
fi

echo ""
print_warning "IMPORTANTE: Cambia la SECRET_KEY en superset_config.py antes de usar en producción"
echo ""

if [[ $install_service =~ ^[Nn]$ ]]; then
    echo "Para iniciar Superset manualmente:"
    echo "  cd $SUPERSET_DIR"
    echo "  ./start_superset.sh"
fi

echo ""
echo "🌐 Accede a Superset en: http://localhost:8088"
echo "👤 Usuario: El que creaste durante la instalación"
