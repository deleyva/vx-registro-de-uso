#!/bin/sh
set -e

ENV_FILE=/opt/vx-registro/.env

# ---------------------------------------------------------------------
# Claves y secretos.
#
# ADMIN_PASSWORD e INITIAL_ACCESS_PASSWORD traen valores PÚBLICOS por defecto,
# documentados en el README. Es una decisión deliberada: esto se despliega en la
# red local del centro y tiene que funcionar nada más instalarlo. El
# administrador las cambia desde /admin, y la del .env editando el fichero.
#
# SESSION_SECRET sí se genera aquí, único de esta máquina: no es una clave que
# nadie teclee, es la firma de las cookies. Publicarlo permitiría falsificar
# sesiones de administrador sin conocer ninguna clave, que es un problema
# distinto y que nadie ha pedido tener.
#
# Las variables que ya tengan valor NO se tocan: al actualizar el paquete se
# conserva lo que el administrador haya puesto.
# ---------------------------------------------------------------------

gen_secret() {
    # Solo A-Za-z0-9 a propósito. systemd (EnvironmentFile) y docker compose
    # interpretan de forma distinta comillas, '#' y '$'; ceñirse a alfanuméricos
    # evita que un carácter del secreto rompa el arranque del servicio.
    LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 28
}

# Devuelve 0 si ha escrito la variable, 1 si ya tenía valor y no se ha tocado.
ensure_var() {
    _name="$1"
    _value="$2"
    if grep -qE "^[[:space:]]*${_name}=..*" "$ENV_FILE" 2>/dev/null; then
        return 1
    fi
    # Quita la línea declarada pero vacía (VAR=) antes de añadir la definitiva.
    sed -i "/^[[:space:]]*${_name}=[[:space:]]*\$/d" "$ENV_FILE"
    printf '%s=%s\n' "$_name" "$_value" >> "$ENV_FILE"
    return 0
}

SECRET_GENERATED=no

if [ -f "$ENV_FILE" ]; then
    # Si el fichero no acaba en salto de línea, lo añadimos: sin esto la primera
    # variable nueva se pegaría al final de la última línea existente.
    if [ -s "$ENV_FILE" ] && [ "$(tail -c1 "$ENV_FILE" | wc -l)" -eq 0 ]; then
        printf '\n' >> "$ENV_FILE"
    fi

    if ensure_var SESSION_SECRET "$(gen_secret)"; then
        SECRET_GENERATED=yes
    fi
    ensure_var ADMIN_PASSWORD vxloginadmin || true
    ensure_var INITIAL_ACCESS_PASSWORD vxlogindocente || true
    ensure_var AUTH_ENABLED true || true
    ensure_var SESSION_MAX_AGE 43200 || true
    ensure_var COOKIE_SECURE false || true

    # El fichero guarda credenciales: solo root.
    chown root:root "$ENV_FILE" 2>/dev/null || true
    chmod 600 "$ENV_FILE" 2>/dev/null || true
fi

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

echo ""
echo "🔑 Claves iniciales del panel (públicas, documentadas en el README):"
echo "     administración : vxloginadmin"
echo "     profesorado    : vxlogindocente"
echo "   Entra en el panel con la de administración y cámbialas desde /admin."

if [ "$SECRET_GENERATED" = yes ]; then
    echo ""
    echo "🔏 Firma de cookies generada para este servidor (SESSION_SECRET)."
    echo "   No hay que teclearla nunca ni compartirla."
fi

echo ""
echo "🔐 Revisa las credenciales de Postgres en $ENV_FILE"
echo "   (siguen en postgres/postgres por defecto)."
echo "   Tras editarlo: sudo systemctl restart vx-registro"

exit 0
