from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.camel import CamelModel


class CreateReportRequest(BaseModel):
    """Payload entrante del cliente de escritorio.

    ``model_config = {"extra": "ignore"}`` hace que cualquier campo no
    declarado se descarte en silencio, sin error. Eso cubre tanto campos
    futuros como los antiguos ``empresa`` y ``tipo_verificacion``, que se
    dejaron de declarar en septiembre de 2026: nunca se almacenaron, así que
    declararlos solo servía para sugerir que hacían algo. Los clientes que
    todavía los envíen siguen recibiendo 201.
    """

    timestamp: datetime
    migasfree_cid: str
    usuario_grafico: str
    # Etiquetas del equipo. Opcional: los clientes desplegados antes de
    # septiembre de 2026 no lo envían y deben seguir funcionando.
    etiquetas: str | None = None
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
