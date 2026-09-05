"""FastAPI application entrypoint.

Mirrors the NestJS ``main.ts`` setup:
  * CORS origins from ``CORS_ORIGINS``
  * Swagger / OpenAPI mounted under ``/api/docs`` and ``/api/openapi.json``
  * ``/v1/report*`` exposed at the root (no global ``/api`` prefix)
  * ``/health`` and the HTMX web panel ``/`` complete the surface

Sobre la autenticación: el orden de ``add_middleware`` importa. Starlette
ejecuta el ÚLTIMO añadido como el más externo, así que se añaden en orden
guardia → sesión → CORS para que el preflight se resuelva antes de nada, la
cookie esté descifrada cuando el guardia mira el rol, y el guardia decida
antes de llegar a la ruta.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.authguard import AuthGuardMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.db import session as session_module
from app.routers import auth as auth_router
from app.routers import health, reports_v1, web
from app.services import auth as auth_service

configure_logging()
logger = logging.getLogger("app.startup")


def _resolve_session_secret() -> str:
    if settings.session_secret:
        return settings.session_secret
    if settings.auth_enabled:
        logger.warning(
            "SESSION_SECRET no está definida: se genera una efímera y todas las "
            "sesiones se cerrarán en cada reinicio. Defínela en el .env."
        )
    return secrets.token_urlsafe(32)


def _ensure_admin_password() -> None:
    if settings.admin_password or not settings.auth_enabled:
        return
    generated = secrets.token_urlsafe(12)
    settings.admin_password = generated
    logger.warning(
        "ADMIN_PASSWORD no está definida. Clave de administración generada para "
        "esta ejecución: %s — anótala y fíjala en el .env, o cambiará en cada "
        "reinicio.",
        generated,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auth_enabled:
        _ensure_admin_password()
        async with session_module.SessionLocal() as db:
            generated = await auth_service.ensure_access_password(db)
        if generated:
            logger.warning(
                "Clave de acceso generada en el primer arranque: %s — cámbiala "
                "desde /admin.",
                generated,
            )
    yield


app = FastAPI(
    title="VX Control Center API",
    description="Sistema de registro y monitoreo de equipos",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Añadido primero => queda en la capa más interna (ver docstring del módulo).
app.add_middleware(AuthGuardMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=_resolve_session_secret(),
    session_cookie="vx_session",
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=settings.cookie_secure,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets (Tailwind output + vendored HTMX)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routers
app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(reports_v1.router)
app.include_router(web.router)
