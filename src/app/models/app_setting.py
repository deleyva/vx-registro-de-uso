"""Ajustes de la aplicación persistidos en base de datos.

Guarda las claves que la interfaz puede cambiar, siempre hasheadas: la de
acceso del profesorado y la del administrador delegado. La llave maestra vive
en el entorno (``ADMIN_PASSWORD``) y nunca aquí, para que ninguna pantalla
pueda dejar fuera a quien administra el servidor.

La tabla es clave/valor a propósito: no merece una tabla por cada ajuste.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACCESS_PASSWORD_KEY = "access_password"
ADMIN_PASSWORD_KEY = "admin_password"
# "true"/"false": si el panel exige clave para leer. Lo cambia el administrador
# desde /admin. /admin sigue protegida aunque esto valga "false".
AUTH_REQUIRED_KEY = "auth_required"


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
