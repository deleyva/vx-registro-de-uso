from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.camel import CamelModel


class CreateReportRequest(BaseModel):
    """Inbound payload from the MigrasFree desktop client.

    ``empresa`` and ``tipo_verificacion`` are accepted but silently discarded
    (they are not persisted). Unknown fields are ignored to keep parity with
    the NestJS ``ValidationPipe(whitelist: true)`` behavior, which strips
    unknown properties without erroring.
    """

    timestamp: datetime
    migrasfree_cid: str
    usuario_grafico: str
    empresa: str | None = None
    tipo_verificacion: str | None = None
    verificacion_equipos: dict[str, Any]
    resumen: dict[str, Any]

    model_config = {"extra": "ignore"}


class ReportResponse(CamelModel):
    """Response shape returned to clients.

    Serialized JSON keys (camelCase):
        id, timestamp, migrasfreeCid, usuarioGrafico, verificacionEquipos,
        resumen, createdAt
    """

    id: str
    timestamp: datetime
    migrasfree_cid: str
    usuario_grafico: str
    verificacion_equipos: dict[str, Any]
    resumen: dict[str, Any]
    created_at: datetime
