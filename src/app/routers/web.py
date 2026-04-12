"""Web panel — server-rendered HTMX dashboard.

Renders the same data the React frontend used to fetch over HTTP.
A request is treated as an HTMX partial render when either:
  * the ``HX-Request`` header is present, OR
  * the query parameter ``?partial=1`` is supplied.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.routers.reports_v1 import _parse_iso, _parse_tri_bool
from app.schemas.reports import ReportResponse
from app.services import reports as reports_service
from app.services.reports import ReportFilters

router = APIRouter(tags=["web"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _format_es_datetime(dt: datetime) -> str:
    """Spanish-style date format, converted to Europe/Madrid."""
    if dt is None:
        return "—"
    from zoneinfo import ZoneInfo
    madrid = ZoneInfo("Europe/Madrid")
    utc = ZoneInfo("UTC")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=utc)
    dt = dt.astimezone(madrid)
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


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    partial: int | None = Query(None),
    limit: int = Query(200),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    onlyErrors: str | None = Query(None),
    component: str | None = Query(None),
    onlyOperativo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    filters = ReportFilters(
        from_=_parse_iso(from_),
        to=_parse_iso(to),
        only_errors=_parse_tri_bool(onlyErrors),
        component=component,
        only_operativo=_parse_tri_bool(onlyOperativo),
    )
    rows = await reports_service.find_all(db, limit=limit, filters=filters)
    reports = [ReportResponse.model_validate(r) for r in rows]
    components = _collect_components(reports)

    is_partial = partial is not None or "HX-Request" in request.headers
    template_name = (
        "partials/reports_table.html" if is_partial else "index.html"
    )

    ctx = {
        "reports": reports,
        "components": components,
        "component_labels": COMPONENT_LABELS,
        "filters": {
            "from": from_ or "",
            "to": to or "",
            "onlyErrors": onlyErrors == "true",
            "component": component or "",
            "onlyOperativo": onlyOperativo or "",
        },
    }
    return templates.TemplateResponse(request, template_name, ctx)
