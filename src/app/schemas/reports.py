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
    migasfree_cid: str
    usuario_grafico: str
    # Etiquetas del equipo. Opcional: los clientes desplegados antes de
    # septiembre de 2026 no lo envían y deben seguir funcionando.
    etiquetas: str | None = None
    empresa: str | None = None
    tipo_verificacion: str | None = None
    verificacion_equipos: dict[str, Any]
    resumen: dict[str, Any]

    model_config = {"extra": "ignore"}


class ReportResponse(CamelModel):
    """Response shape returned to clients.

    Serialized JSON keys (camelCase):
        id, timestamp, migasfreeCid, usuarioGrafico, etiquetas,
        verificacionEquipos, resumen, createdAt

    ``etiquetas`` se añadió en septiembre de 2026 y vale ``null`` en todos los
    informes anteriores. Es una adición al contrato, no un cambio: ningún
    cliente lee esta respuesta (el cliente Tauri solo hace POST).
    """

    id: str
    timestamp: datetime
    migasfree_cid: str
    usuario_grafico: str
    etiquetas: str | None = None
    verificacion_equipos: dict[str, Any]
    resumen: dict[str, Any]
    created_at: datetime
