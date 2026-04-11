from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import create_id
from app.db.base import Base


class Report(Base):
    """Verification report received from the MigrasFree desktop client."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=create_id)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    migasfree_cid: Mapped[str] = mapped_column(
        "migasfreeCid", String, nullable=False
    )
    usuario_grafico: Mapped[str] = mapped_column(
        "usuarioGrafico", String, nullable=False
    )
    verificacion_equipos: Mapped[dict[str, Any]] = mapped_column(
        "verificacionEquipos", JSONB, nullable=False
    )
    resumen: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("reports_timestamp_idx", "timestamp"),
        Index("reports_migasfreeCid_idx", "migasfreeCid"),
    )
