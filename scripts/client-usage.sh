#!/bin/bash

# Script de ejemplo para enviar métricas de uso a VX Control Center
# Se puede ejecutar periódicamente con cron

# Configuración
API_URL="${VX_API_URL:-http://localhost:3001}"
DEVICE_ID="${VX_DEVICE_ID:-}"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$DEVICE_ID" ]; then
    echo -e "${RED}❌ Error: VX_DEVICE_ID no está configurado${NC}"
    echo ""
    echo "Primero registra el equipo con client-register.sh"
    echo "Luego configura: export VX_DEVICE_ID='tu-device-id'"
    exit 1
fi

# Detectar métricas de uso
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CPU_USAGE=$(ps -A -o %cpu | awk '{s+=$1} END {print s}')
    RAM_USAGE=$(ps -A -o rss | awk '{sum+=$1} END {print sum/1024/1024}')
    DISK_USAGE=$(df -H / | awk 'NR==2 {print int($3)}')
    UPTIME=$(sysctl -n kern.boottime | awk '{print $4}' | sed 's/,//')
    UPTIME=$(($(date +%s) - $UPTIME))
    PROCESS_COUNT=$(ps -A | wc -l)
else
    # Linux
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    RAM_USAGE=$(free -g | awk 'NR==2 {print $3}')
    DISK_USAGE=$(df -BG / | awk 'NR==2 {print int($3)}')
    UPTIME=$(awk '{print int($1)}' /proc/uptime)
    PROCESS_COUNT=$(ps -A | wc -l)
fi

# Construir JSON
JSON_PAYLOAD=$(cat <<EOF
{
  "deviceId": "$DEVICE_ID",
  "cpuUsage": ${CPU_USAGE},
  "ramUsage": ${RAM_USAGE},
  "diskUsage": ${DISK_USAGE},
  "uptime": ${UPTIME},
  "processCount": ${PROCESS_COUNT},
  "userActive": true
}
EOF
)

# Enviar a la API
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "$API_URL/api/usage")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✅ Métricas enviadas correctamente${NC}"
    echo "CPU: ${CPU_USAGE}% | RAM: ${RAM_USAGE}GB | Disco: ${DISK_USAGE}GB"
else
    echo -e "${RED}❌ Error al enviar métricas (HTTP $HTTP_CODE)${NC}"
    exit 1
fi
