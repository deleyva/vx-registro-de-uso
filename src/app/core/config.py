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
        "http://100.99.123.84:3000",
    ]

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
