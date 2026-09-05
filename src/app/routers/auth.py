"""Rutas de sesión: ``/login``, ``/logout`` y ``/admin``.

La única ruta que cambia la clave de acceso compartida es
``POST /admin/rotate``, y exige teclear la clave de administración en ese
mismo formulario. Tener la sesión de administrador abierta no basta: es lo
que impide que alguien rote la clave desde un equipo con sesión olvidada.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import authguard
from app.core.config import settings
from app.db.session import get_db
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

MIN_PASSWORD_LENGTH = 8


def _safe_next(raw: str | None) -> str:
    """Solo se admite redirección interna: evita usar /login como trampolín."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return "/"
    if raw.startswith("/login"):
        return "/"
    return raw


def _login_page(
    request: Request, error: str | None, next_url: str, status_code: int = 200
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error, "next": next_url},
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, next: str | None = None) -> Response:
    if not settings.auth_enabled:
        return RedirectResponse("/", status_code=303)
    if await authguard.resolve_role(request) is not None:
        return RedirectResponse(_safe_next(next), status_code=303)
    return _login_page(request, None, _safe_next(next))


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    password: str = Form(""),
    next: str = Form("/"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    target = _safe_next(next)

    if authguard.login_locked(request):
        return _login_page(
            request,
            "Demasiados intentos fallidos. Espera unos minutos.",
            target,
            status_code=429,
        )

    admin_source = await auth_service.verify_admin_password(db, password)
    if admin_source is not None:
        stamp = await auth_service.admin_stamp(db, admin_source)
        request.session.clear()
        request.session["role"] = auth_service.ROLE_ADMIN
        request.session["admin_source"] = admin_source
        request.session["stamp"] = stamp
        authguard.clear_login_failures(request)
        return RedirectResponse(target, status_code=303)

    if await auth_service.verify_access_password(db, password):
        stamp = await auth_service.current_stamp(db)
        request.session.clear()
        request.session["role"] = auth_service.ROLE_VIEWER
        request.session["stamp"] = stamp
        authguard.clear_login_failures(request)
        return RedirectResponse(target, status_code=303)

    authguard.record_login_failure(request)
    return _login_page(request, "Clave incorrecta.", target, status_code=401)


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


def _require_admin(request: Request) -> bool:
    return getattr(request.state, "role", None) == auth_service.ROLE_ADMIN


async def _admin_page(
    request: Request,
    db: AsyncSession,
    error: str | None = None,
    notice: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "error": error,
            "notice": notice,
            "min_length": MIN_PASSWORD_LENGTH,
            "admin_source": request.session.get("admin_source"),
            "source_env": auth_service.SOURCE_ENV,
            "delegado_configurado": await auth_service.delegated_admin_configured(db),
            "login_requerido": await auth_service.login_required(db),
        },
        status_code=status_code,
    )


def _forbidden(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "forbidden.html",
        {},
        status_code=403,
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    if not _require_admin(request):
        return _forbidden(request)
    return await _admin_page(request, db)


@router.post("/admin/rotate", response_class=HTMLResponse)
async def admin_rotate(
    request: Request,
    admin_password: str = Form(""),
    new_password: str = Form(""),
    new_password_confirm: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    if not _require_admin(request):
        return _forbidden(request)

    # Se reexige la clave de administración aquí, no solo al iniciar sesión.
    if await auth_service.verify_admin_password(db, admin_password) is None:
        return await _admin_page(
            request, db, error="Clave de administración incorrecta.", status_code=403
        )
    error = _validate_new_password(new_password, new_password_confirm)
    if error:
        return await _admin_page(request, db, error=error, status_code=400)

    await auth_service.rotate_access_password(db, new_password)
    return await _admin_page(
        request,
        db,
        notice="Clave de acceso actualizada. Las sesiones abiertas con la clave anterior han quedado cerradas.",
    )


def _validate_new_password(new_password: str, confirm: str) -> str | None:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return f"La clave nueva debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
    if new_password != confirm:
        return "Las dos claves nuevas no coinciden."
    return None


@router.post("/admin/login-toggle", response_class=HTMLResponse)
async def admin_toggle_login(
    request: Request,
    admin_password: str = Form(""),
    enabled: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Activa o quita el login del panel.

    Quitarlo abre el panel y la API de lectura a cualquiera que alcance el
    puerto. NO abre ``/admin``: esta ruta y sus hermanas siguen exigiendo la
    clave de administración, que es la forma de volver a activarlo.
    """
    if not _require_admin(request):
        return _forbidden(request)
    if await auth_service.verify_admin_password(db, admin_password) is None:
        return await _admin_page(
            request, db, error="Clave de administración incorrecta.", status_code=403
        )

    required = enabled == "true"
    await auth_service.set_login_required(db, required)
    notice = (
        "El panel vuelve a pedir clave para entrar."
        if required
        else "Login quitado: cualquiera que alcance el panel puede ver los informes. "
        "La administración sigue pidiendo tu clave."
    )
    return await _admin_page(request, db, notice=notice)


@router.post("/admin/admin-password", response_class=HTMLResponse)
async def admin_set_admin_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    new_password_confirm: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Fija o cambia la clave de administración guardada en base de datos.

    Sirve para dos cosas con el mismo formulario: que quien tiene la llave
    maestra le dé una clave inicial a otro administrador, y que ese
    administrador la rote después sin pisar nunca el servidor. En ambos casos
    hay que teclear una clave de administración válida, así que una sesión
    olvidada abierta no basta.

    La llave maestra del ``.env`` no se toca aquí. Es lo que garantiza que
    quien administra el servidor no pueda quedarse fuera desde la interfaz.
    """
    if not _require_admin(request):
        return _forbidden(request)

    source = await auth_service.verify_admin_password(db, current_password)
    if source is None:
        return await _admin_page(
            request, db, error="Clave de administración incorrecta.", status_code=403
        )
    error = _validate_new_password(new_password, new_password_confirm)
    if error:
        return await _admin_page(request, db, error=error, status_code=400)

    stamp = await auth_service.set_admin_password(db, new_password)

    # Quien acaba de cambiar SU propia clave se quedaría fuera en la siguiente
    # petición, porque su sello ya no valdría. Se le renueva aquí mismo.
    if request.session.get("admin_source") == auth_service.SOURCE_DB:
        request.session["stamp"] = stamp

    return await _admin_page(
        request,
        db,
        notice="Clave de administración actualizada. Las sesiones abiertas con la anterior han quedado cerradas.",
    )
