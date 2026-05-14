#!/bin/sh
set -e

# Reload systemd after the unit file is gone.
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload || true
fi

# Note: /opt/vx-registro/.env and the postgres_data Docker volume are left in
# place on purpose so an uninstall does not destroy data or credentials.
echo "ℹ️  vx-registro eliminado. /opt/vx-registro/.env y el volumen de datos se conservan."

exit 0
