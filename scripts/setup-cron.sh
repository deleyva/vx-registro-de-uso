#!/bin/bash

# Script para configurar cron y enviar métricas automáticamente

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Configuración de Cron para VX Control Center${NC}"
echo "==============================================="
echo ""

# Obtener ruta absoluta del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
USAGE_SCRIPT="$SCRIPT_DIR/client-usage.sh"

# Verificar que existe el script
if [ ! -f "$USAGE_SCRIPT" ]; then
    echo "Error: No se encuentra client-usage.sh en $SCRIPT_DIR"
    exit 1
fi

# Hacer ejecutable
chmod +x "$USAGE_SCRIPT"

# Solicitar información
echo "Este script configurará un cron job para enviar métricas cada 5 minutos"
echo ""
read -p "API URL [http://localhost:3001]: " API_URL
API_URL=${API_URL:-http://localhost:3001}

read -p "Device ID (del registro previo): " DEVICE_ID

if [ -z "$DEVICE_ID" ]; then
    echo "Error: Debes proporcionar un Device ID"
    exit 1
fi

# Crear script wrapper con variables de entorno
WRAPPER_SCRIPT="$SCRIPT_DIR/.vx-cron-wrapper.sh"
cat > "$WRAPPER_SCRIPT" <<EOF
#!/bin/bash
export VX_API_URL="$API_URL"
export VX_DEVICE_ID="$DEVICE_ID"
$USAGE_SCRIPT >> /tmp/vx-control-usage.log 2>&1
EOF

chmod +x "$WRAPPER_SCRIPT"

# Añadir a crontab
CRON_JOB="*/5 * * * * $WRAPPER_SCRIPT"

# Verificar si ya existe
if crontab -l 2>/dev/null | grep -q "$WRAPPER_SCRIPT"; then
    echo "El cron job ya existe"
else
    # Añadir nuevo cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✅ Cron job configurado correctamente${NC}"
fi

echo ""
echo "Configuración completada:"
echo "- Frecuencia: Cada 5 minutos"
echo "- Script: $WRAPPER_SCRIPT"
echo "- Logs: /tmp/vx-control-usage.log"
echo ""
echo "Para ver los cron jobs activos:"
echo "  crontab -l"
echo ""
echo "Para ver los logs:"
echo "  tail -f /tmp/vx-control-usage.log"
echo ""
echo "Para eliminar el cron job:"
echo "  crontab -e   (y elimina la línea manualmente)"
