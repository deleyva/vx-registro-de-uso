#!/bin/bash

# Script de ejemplo para registrar un equipo en VX Control Center
# Detecta automáticamente información del sistema

# Configuración
API_URL="${VX_API_URL:-http://localhost:3001}"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}VX Control Center - Registro de Equipo${NC}"
echo "==========================================="
echo ""

# Detectar información del sistema
echo -e "${BLUE}📊 Detectando información del sistema...${NC}"

# Hostname
HOSTNAME=$(hostname)
echo "Hostname: $HOSTNAME"

# IP Address (primera no-loopback)
if [[ "$OSTYPE" == "darwin"* ]]; then
    IP_ADDRESS=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
else
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
fi
echo "IP: $IP_ADDRESS"

# MAC Address
if [[ "$OSTYPE" == "darwin"* ]]; then
    MAC_ADDRESS=$(ifconfig en0 | grep ether | awk '{print $2}')
else
    MAC_ADDRESS=$(ip link show | grep ether | head -n 1 | awk '{print $2}')
fi
echo "MAC: $MAC_ADDRESS"

# Sistema Operativo
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_INFO="macOS $(sw_vers -productVersion)"
    OS_VERSION=$(sw_vers -productVersion)
    CPU_INFO=$(sysctl -n machdep.cpu.brand_string)
    RAM_TOTAL=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
    DISK_TOTAL=$(df -H / | awk 'NR==2 {print int($2)}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_INFO=$(lsb_release -d | cut -f2)
    OS_VERSION=$(lsb_release -r | cut -f2)
    CPU_INFO=$(lscpu | grep "Model name" | cut -d':' -f2 | xargs)
    RAM_TOTAL=$(free -g | awk 'NR==2 {print $2}')
    DISK_TOTAL=$(df -BG / | awk 'NR==2 {print int($2)}')
else
    OS_INFO="Unknown"
    OS_VERSION="Unknown"
    CPU_INFO="Unknown"
    RAM_TOTAL=0
    DISK_TOTAL=0
fi

echo "OS: $OS_INFO"
echo "CPU: $CPU_INFO"
echo "RAM: ${RAM_TOTAL}GB"
echo "Disco: ${DISK_TOTAL}GB"
echo ""

# Construir JSON
JSON_PAYLOAD=$(cat <<EOF
{
  "hostname": "$HOSTNAME",
  "ipAddress": "$IP_ADDRESS",
  "macAddress": "$MAC_ADDRESS",
  "osInfo": "$OS_INFO",
  "osVersion": "$OS_VERSION",
  "cpuInfo": "$CPU_INFO",
  "ramTotal": $RAM_TOTAL,
  "diskTotal": $DISK_TOTAL
}
EOF
)

# Enviar a la API
echo -e "${BLUE}📤 Registrando equipo en $API_URL...${NC}"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "$API_URL/api/devices/register")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✅ Equipo registrado exitosamente!${NC}"
    echo ""
    echo "Respuesta de la API:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Error al registrar equipo (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Respuesta:"
    echo "$BODY"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Registro completado!${NC}"
echo ""
echo "Puedes ver tu equipo en el dashboard:"
echo "http://localhost:3000"
