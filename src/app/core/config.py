from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/vx_control"
    )
    app_port: int = 3001
    environment: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # --- Autenticacion -------------------------------------------------
    # Se pone a false solo en desarrollo y en la suite que verifica la
    # paridad con la API NestJS antigua.
    auth_enabled: bool = True
    # Llave maestra. Vive SOLO aqui, nunca en la base de datos, de modo que
    # ninguna ruta de la interfaz pueda modificarla y dejar fuera al
    # administrador. El valor por defecto es PUBLICO y esta en el repositorio a
    # proposito: esto se despliega en la red local del centro y el objetivo es
    # que funcione nada mas instalarlo. Cambialo en el .env de produccion si el
    # panel llega a ser alcanzable desde fuera.
    admin_password: str = "vxloginadmin"
    # Clave de acceso del profesorado en el primer arranque. Tambien publica y
    # por el mismo motivo. Despues manda la copia hasheada en app_settings, que
    # el administrador cambia desde /admin.
    initial_access_password: str = "vxlogindocente"
    # Firma de la cookie de sesion. Vacia => se genera una efimera y las
    # sesiones mueren en cada reinicio (se avisa en el log).
    session_secret: str = ""
    session_max_age: int = 43200  # 12 h
    # Poner a true cuando haya HTTPS delante.
    cookie_secure: bool = False
    # Token opcional para POST /v1/report. Vacio (por defecto) => la ingesta
    # sigue abierta, que es lo que necesitan los clientes ya instalados.
    ingest_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def async_database_url(self) -> str:
        """Normalize the database URL to use the asyncpg driver."""
        url = self.database_url
        scheme = url.split("://", 1)[0] if "://" in url else ""
        if scheme == "postgresql":
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic — uses psycopg2."""
        url = self.async_database_url
        return url.replace("+asyncpg", "+psycopg2")


settings = Settings()
