"""Servicio de autenticación: dos roles y tres llaves.

| Llave | Dónde vive | Quién la cambia |
|-------|------------|-----------------|
| Clave de acceso | ``app_settings``, hasheada | administración, desde ``/admin`` |
| Clave de administración | ``app_settings``, hasheada | su propio dueño, desde ``/admin`` |
| **Llave maestra** | ``ADMIN_PASSWORD`` en el entorno | solo por SSH |

La llave maestra existe para que **ninguna ruta de la interfaz pueda dejar
fuera a quien administra el servidor**: pase lo que pase con la base de datos,
esa llave sigue entrando. La de administración delegada permite que otra
persona administre el panel sin tocar el servidor nunca.

El *sello* (``stamp``) identifica la versión de la llave con la que se abrió
cada sesión. Se guarda en la cookie y se compara en cada petición protegida,
así que cambiar una llave cierra las sesiones abiertas con la anterior, y solo
esas. Sin eso, rotar una clave filtrada sería decorativo.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.models.app_setting import (
    ACCESS_PASSWORD_KEY,
    ADMIN_PASSWORD_KEY,
    AUTH_REQUIRED_KEY,
    AppSetting,
)

logger = logging.getLogger("app.auth")

ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"

# De dónde salió la credencial con la que se abrió una sesión de administración.
SOURCE_ENV = "env"
SOURCE_DB = "db"


async def _get(db: AsyncSession, key: str) -> AppSetting | None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    return result.scalar_one_or_none()


async def _set(db: AsyncSession, key: str, plain: str) -> str:
    """Guarda ``plain`` hasheada bajo ``key`` y devuelve el sello nuevo."""
    now = datetime.now(tz=UTC)
    setting = await _get(db, key)
    if setting is None:
        db.add(
            AppSetting(key=key, value=security.hash_password(plain), updated_at=now)
        )
    else:
        setting.value = security.hash_password(plain)
        setting.updated_at = now
    await db.commit()
    return now.isoformat()


async def _get_raw(db: AsyncSession, key: str) -> str | None:
    setting = await _get(db, key)
    return setting.value if setting is not None else None


async def _set_raw(db: AsyncSession, key: str, value: str) -> None:
    """Guarda un valor SIN hashear. Solo para ajustes que no son secretos."""
    now = datetime.now(tz=UTC)
    setting = await _get(db, key)
    if setting is None:
        db.add(AppSetting(key=key, value=value, updated_at=now))
    else:
        setting.value = value
        setting.updated_at = now
    await db.commit()


async def _stamp(db: AsyncSession, key: str) -> str | None:
    setting = await _get(db, key)
    if setting is None or setting.updated_at is None:
        return None
    return setting.updated_at.isoformat()


# --- Clave de acceso (profesorado) -----------------------------------


async def ensure_access_password(db: AsyncSession) -> str | None:
    """Siembra la clave de acceso si aún no existe.

    Devuelve la clave en claro **solo** cuando ha tenido que generarla, para
    que quien arranca el servicio pueda leerla una vez en el log.
    """
    if await _get(db, ACCESS_PASSWORD_KEY) is not None:
        return None
    plain = settings.initial_access_password or secrets.token_urlsafe(9)
    generated = not settings.initial_access_password
    await _set(db, ACCESS_PASSWORD_KEY, plain)
    return plain if generated else None


async def current_stamp(db: AsyncSession) -> str | None:
    return await _stamp(db, ACCESS_PASSWORD_KEY)


async def verify_access_password(db: AsyncSession, password: str) -> bool:
    setting = await _get(db, ACCESS_PASSWORD_KEY)
    if setting is None:
        return False
    return security.verify_password(password, setting.value)


async def rotate_access_password(db: AsyncSession, new_password: str) -> str:
    stamp = await _set(db, ACCESS_PASSWORD_KEY, new_password)
    logger.info("Clave de acceso rotada")
    return stamp


# --- Interruptor de login --------------------------------------------


async def login_required(db: AsyncSession) -> bool:
    """Si el panel exige clave para leer.

    Lo cambia el administrador desde ``/admin``. Cuando está desactivado, el
    panel y la API de lectura quedan abiertos, pero ``/admin`` NO: seguir
    pidiendo la clave de administración ahí es lo que impide que, con el login
    quitado, cualquiera pueda volver a activarlo o cambiar las claves.
    """
    value = await _get_raw(db, AUTH_REQUIRED_KEY)
    if value is None:
        return True  # por defecto, el panel pide clave
    return value == "true"


async def set_login_required(db: AsyncSession, required: bool) -> None:
    await _set_raw(db, AUTH_REQUIRED_KEY, "true" if required else "false")
    logger.info("Login del panel %s", "activado" if required else "desactivado")


# --- Claves de administración ----------------------------------------


async def verify_admin_password(db: AsyncSession, password: str) -> str | None:
    """Devuelve de qué llave procede la credencial, o ``None`` si no vale.

    La llave maestra del entorno se comprueba primero y siempre: es la
    garantía de que quien administra el servidor nunca se queda fuera, hagan
    lo que hagan desde la interfaz.
    """
    if not password:
        return None
    if settings.admin_password and security.constant_time_equals(
        password, settings.admin_password
    ):
        return SOURCE_ENV
    setting = await _get(db, ADMIN_PASSWORD_KEY)
    if setting is not None and security.verify_password(password, setting.value):
        return SOURCE_DB
    return None


async def set_admin_password(db: AsyncSession, new_password: str) -> str:
    """Fija la clave de administración delegada y devuelve su sello nuevo."""
    stamp = await _set(db, ADMIN_PASSWORD_KEY, new_password)
    logger.info("Clave de administración delegada actualizada")
    return stamp


async def admin_stamp(db: AsyncSession, source: str) -> str | None:
    if source == SOURCE_ENV:
        return env_admin_stamp()
    if source == SOURCE_DB:
        return await _stamp(db, ADMIN_PASSWORD_KEY)
    return None


def env_admin_stamp() -> str:
    """Sello de la llave maestra.

    Cambiar ``ADMIN_PASSWORD`` en el entorno cierra las sesiones abiertas con
    ella, y solo esas: las del administrador delegado siguen vivas.
    """
    return security.fingerprint(settings.admin_password)


async def delegated_admin_configured(db: AsyncSession) -> bool:
    return await _get(db, ADMIN_PASSWORD_KEY) is not None
