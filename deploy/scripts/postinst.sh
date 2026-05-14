#!/bin/sh
set -e

# Probe Docker + compose v2 once. Warn (don't fail) if missing — the host admin
# can install it after; the service stays enabled and starts on the next boot.
DOCKER_OK=no
if ! command -v docker >/dev/null 2>&1; then
    echo "⚠️  Docker no está instalado. Instálalo y luego: sudo systemctl start vx-registro"
elif ! docker compose version >/dev/null 2>&1; then
    echo "⚠️  El plugin 'docker compose' v2 no está disponible. Instálalo y luego: sudo systemctl start vx-registro"
else
    DOCKER_OK=yes
fi

systemctl daemon-reload || true
systemctl enable vx-registro.service || true

if [ "$DOCKER_OK" = yes ]; then
    systemctl start vx-registro.service || true
fi

echo "✅ vx-registro instalado."
echo "🔐 IMPORTANTE: /opt/vx-registro/.env trae credenciales por defecto (postgres/postgres)."
echo "   Edítalo y reinicia: sudo nano /opt/vx-registro/.env && sudo systemctl restart vx-registro"

exit 0
