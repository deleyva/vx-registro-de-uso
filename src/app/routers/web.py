"""Web panel — server-rendered HTMX dashboard.

Renders the same data the React frontend used to fetch over HTTP.
A request is treated as an HTMX partial render when either:
  * the ``HX-Request`` header is present, OR
  * the query parameter ``?partial=1`` is supplied.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assets import static_url
from app.core.config import settings
from app.db.session import get_db
from app.routers.reports_v1 import _parse_tri_bool
from app.schemas.reports import ReportResponse
from app.services import reports as reports_service
from app.services.reports import ReportFilters

router = APIRouter(tags=["web"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["static_url"] = static_url


def _format_es_datetime(dt: datetime) -> str:
    """Spanish-style date format, converted to Europe/Madrid."""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt = dt.astimezone(MADRID)
    return dt.strftime("%d/%m/%Y, %H:%M:%S")


def _format_relative(dt: datetime) -> str:
    """Very small ``date-fns`` ``formatDistanceToNow`` substitute (es)."""
    if dt is None:
        return "—"
    delta = datetime.now(tz=dt.tzinfo) - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"hace {seconds}s"
    if seconds < 3600:
        return f"hace {seconds // 60} min"
    if seconds < 86400:
        return f"hace {seconds // 3600} h"
    return f"hace {seconds // 86400} d"


templates.env.filters["es_datetime"] = _format_es_datetime
templates.env.filters["es_relative"] = _format_relative


PREFERRED_COMPONENTS = ["pantalla", "teclado", "raton", "bateria", "otros"]
COMPONENT_LABELS = {
    "pantalla": "Pantalla",
    "teclado": "Teclado",
    "raton": "Ratón",
    "bateria": "Batería",
    "otros": "Otros",
}


def _collect_components(reports: list[ReportResponse]) -> list[str]:
    """Mirror the React ``useMemo`` that builds the column list."""
    found: set[str] = set()
    for r in reports:
        for k in (r.verificacion_equipos or {}).keys():
            found.add(k)
    rest = sorted(k for k in found if k not in PREFERRED_COMPONENTS)
    preferred = [k for k in PREFERRED_COMPONENTS if k in found]
    return preferred + rest


MADRID = ZoneInfo("Europe/Madrid")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_day(s: str | None) -> date | None:
    """``YYYY-MM-DD`` → ``date``; cualquier otra cosa (o vacío) → ``None``."""
    if not s or not DAY_RE.match(s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _day_bounds(from_day: date | None, to_day: date | None) -> tuple[datetime | None, datetime | None]:
    """Convierte dos días (ambos inclusive, en hora de Madrid) en un intervalo
    ``[start, end)`` con zona horaria, listo para comparar contra ``timestamp``.

    Un día elegido en el calendario significa «ese día entero en el centro»,
    no «desde las 00:00 UTC»: por eso los límites se construyen en
    Europe/Madrid y no se recorta la zona como hace el filtro de ``/v1``.
    """
    start = datetime.combine(from_day, time.min, tzinfo=MADRID) if from_day is not None else None
    end = (
        datetime.combine(to_day + timedelta(days=1), time.min, tzinfo=MADRID) if to_day is not None else None
    )
    return start, end


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    partial: int | None = Query(None),
    limit: int | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    onlyErrors: str | None = Query(None),
    component: str | None = Query(None),
    onlyOperativo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    from_day = _parse_day(from_)
    to_day = _parse_day(to)
    if from_day and to_day and to_day < from_day:
        from_day, to_day = to_day, from_day
    has_range = from_day is not None or to_day is not None

    # Sin rango, el panel es «lo último que ha pasado»: 200 filas bastan y
    # el refresco cada 30 s sale barato. Con rango, la pregunta es «qué pasó
    # esos días», y ahí truncar en 200 es mentir; el tope alto existe solo
    # para que un rango de meses no pinte decenas de miles de filas.
    if limit is None:
        limit = reports_service.PANEL_RANGE_LIMIT if has_range else reports_service.PANEL_DEFAULT_LIMIT

    start, end = _day_bounds(from_day, to_day)
    filters = ReportFilters(
        only_errors=_parse_tri_bool(onlyErrors),
        component=component,
        only_operativo=_parse_tri_bool(onlyOperativo),
    )
    page = await reports_service.find_for_panel(db, start=start, end=end, limit=limit, filters=filters)
    reports = [ReportResponse.model_validate(r) for r in page.reports]
    components = _collect_components(reports)

    is_partial = partial is not None or "HX-Request" in request.headers
    template_name = "partials/reports_table.html" if is_partial else "index.html"

    ctx = {
        "role": getattr(request.state, "role", None),
        "auth_enabled": settings.auth_enabled,
        "reports": reports,
        "components": components,
        "component_labels": COMPONENT_LABELS,
        "page": page,
        "has_range": has_range,
        "filters": {
            "from": from_day.isoformat() if from_day else "",
            "to": to_day.isoformat() if to_day else "",
            "limit": limit if limit != reports_service.PANEL_DEFAULT_LIMIT and not has_range else "",
            "onlyErrors": onlyErrors == "true",
            "component": component or "",
            "onlyOperativo": onlyOperativo or "",
        },
    }
    return templates.TemplateResponse(request, template_name, ctx)
