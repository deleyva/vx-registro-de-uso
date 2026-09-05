"""Guardia de sesión: decide qué peticiones pasan sin credencial.

Superficie pública deliberada:

* ``POST /v1/report`` — la ingesta del cliente Tauri instalado por ``.deb`` en
  los equipos del centro. Exigirle credencial rompería las versiones ya
  desplegadas, así que se protege aparte con ``INGEST_TOKEN``, vacío por
  defecto.
* ``/health`` — sonda de vida para el orquestador.
* ``/static/*`` — CSS y HTMX, necesarios para pintar la propia pantalla de
  login.
* ``/login`` y ``/logout``.

Todo lo demás —panel, ``/admin``, ``GET /v1/report*`` y la documentación
OpenAPI— exige sesión válida.

El administrador puede **quitar el login** desde ``/admin``. Eso abre el panel
y la API de lectura, pero NO ``/admin``: las rutas de administración siguen
exigiendo la clave de administración pase lo que pase. Es lo que impide que,
con el login quitado, cualquiera vuelva a activarlo o cambie las claves.
"""

from __future__ import annotations

import time
from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.core.config import settings
from app.db import session as session_module
from app.services import auth as auth_service

PUBLIC_PATHS = frozenset({"/login", "/logout", "/health", "/favicon.ico"})
PUBLIC_PREFIXES = ("/static/",)
API_PREFIXES = ("/v1/", "/api/")
INGEST_PATH = "/v1/report"
# Rutas que exigen sesión de administración SIEMPRE, incluso con el login quitado.
ADMIN_PREFIX = "/admin"

# Limitación de intentos de login, en memoria y por IP. No pretende resistir
# a un atacante distribuido: frena el goteo de fuerza bruta contra una clave
# compartida, que es el riesgo real de este despliegue.
MAX_FAILURES = 10
FAILURE_WINDOW_SECONDS = 300
_failures: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "desconocido"


def login_locked(request: Request) -> bool:
    now = time.monotonic()
    key = _client_key(request)
    recent = [t for t in _failures.get(key, []) if now - t < FAILURE_WINDOW_SECONDS]
    _failures[key] = recent
    return len(recent) >= MAX_FAILURES


def record_login_failure(request: Request) -> None:
    _failures.setdefault(_client_key(request), []).append(time.monotonic())


def clear_login_failures(request: Request) -> None:
    _failures.pop(_client_key(request), None)


def is_ingest_request(request: Request) -> bool:
    return request.method == "POST" and request.url.path.rstrip("/") == INGEST_PATH


def _is_public(request: Request) -> bool:
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return True
    return is_ingest_request(request)


async def resolve_role(request: Request) -> str | None:
    """Rol de la sesión **verificado contra el estado actual**, o ``None``.

    Un sello de lectura solo vale si coincide con la última rotación de la
    clave de acceso; por eso rotar expulsa a quien entró con la anterior. El
    sello de administración se compara contra la llave de la que salió la
    sesión, así que cambiar una cierra sus sesiones sin tocar las de la otra.
    """
    session = getattr(request, "session", {})
    role = session.get("role")
    stamp = session.get("stamp")
    if not role or not stamp:
        return None
    if role == auth_service.ROLE_ADMIN:
        source = session.get("admin_source")
        if source == auth_service.SOURCE_ENV:
            return role if stamp == auth_service.env_admin_stamp() else None
        async with session_module.SessionLocal() as db:
            current = await auth_service.admin_stamp(db, source)
        return role if current is not None and stamp == current else None
    if role == auth_service.ROLE_VIEWER:
        async with session_module.SessionLocal() as db:
            current = await auth_service.current_stamp(db)
        return role if current is not None and stamp == current else None
    return None


def _unauthenticated_response(request: Request) -> Response:
    path = request.url.path
    if path.startswith(API_PREFIXES) and not path.startswith("/api/docs"):
        return JSONResponse({"detail": "No autenticado"}, status_code=401)
    target = f"/login?next={quote(request.url.path)}"
    if request.headers.get("HX-Request"):
        # htmx no sigue un 303 sobre una petición parcial: pintaría el login
        # dentro de la tabla. HX-Redirect fuerza una navegación completa.
        return Response(status_code=401, headers={"HX-Redirect": target})
    return RedirectResponse(target, status_code=303)


def _is_admin_route(request: Request) -> bool:
    path = request.url.path
    return path == ADMIN_PREFIX or path.startswith(ADMIN_PREFIX + "/")


class AuthGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled or _is_public(request):
            request.state.role = None
            return await call_next(request)

        role = await resolve_role(request)

        if role is None and not _is_admin_route(request):
            # Con el login quitado por el administrador, leer el panel no pide
            # nada. /admin nunca entra por aquí: se queda fuera del `if`.
            async with session_module.SessionLocal() as db:
                required = await auth_service.login_required(db)
            if not required:
                request.state.role = None
                return await call_next(request)

        if role is None:
            return _unauthenticated_response(request)

        request.state.role = role
        return await call_next(request)
