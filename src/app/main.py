"""FastAPI application entrypoint.

Mirrors the NestJS ``main.ts`` setup:
  * 3 CORS origins (localhost:3000, localhost:3001, 100.99.123.84:3000)
  * Swagger / OpenAPI mounted under ``/api/docs`` and ``/api/openapi.json``
  * ``/v1/report*`` exposed at the root (no global ``/api`` prefix)
  * ``/health`` and the HTMX web panel ``/`` complete the surface
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import configure_logging
from app.routers import health, reports_v1, web

configure_logging()

app = FastAPI(
    title="VX Control Center API",
    description="Sistema de registro y monitoreo de equipos",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
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
app.include_router(reports_v1.router)
app.include_router(web.router)
