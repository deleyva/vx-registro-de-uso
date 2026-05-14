#!/bin/sh
set -e

# Stop and disable the service before the package files are removed.
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop vx-registro.service || true
    systemctl disable vx-registro.service || true
fi

exit 0
