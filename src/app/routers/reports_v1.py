"""``/v1/report*`` — public API consumed by the MigrasFree desktop client.

These endpoints intentionally use only ``str`` query parameters for the
tri-bool filters (``onlyErrors``, ``onlyOperativo``) so that FastAPI's
automatic ``bool`` coercion (which accepts ``"1"``, ``"yes"``, etc.) does
NOT diverge from the NestJS controller, which only treats the literal
strings ``"true"`` and ``"false"`` as booleans.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.reports import CreateReportRequest, ReportResponse
from app.services import reports as reports_service
from app.services.reports import ReportFilters

router = APIRouter(prefix="/v1/report", tags=["reports"])


def _parse_tri_bool(s: str | None) -> bool | None:
    """Parse the tri-state booleans MigrasFree sends as raw strings."""
    if s == "true":
        return True
    if s == "false":
        return False
    return None


def _parse_iso(s: str | None) -> datetime | None:
    """Parse ISO-8601 strings, returning None on failure (parity)."""
    if not s:
        return None
    try:
        # Python 3.11+ accepts trailing Z
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ReportResponse,
    summary="Registrar un reporte de verificación",
)
async def create_report(
    body: CreateReportRequest,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    payload = body.model_dump()
    # empresa and tipo_verificacion are accepted but never persisted
    payload.pop("empresa", None)
    payload.pop("tipo_verificacion", None)
    report = await reports_service.create(db, payload)
    return ReportResponse.model_validate(report)


@router.get(
    "",
    response_model=list[ReportResponse],
    summary="Listar reportes de verificación",
)
async def list_reports(
    limit: int = 50,
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    onlyErrors: str | None = Query(None),
    component: str | None = Query(None),
    onlyOperativo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[ReportResponse]:
    filters = ReportFilters(
        from_=_parse_iso(from_),
        to=_parse_iso(to),
        only_errors=_parse_tri_bool(onlyErrors),
        component=component,
        only_operativo=_parse_tri_bool(onlyOperativo),
    )
    rows = await reports_service.find_all(db, limit=limit, filters=filters)
    return [ReportResponse.model_validate(r) for r in rows]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Obtener un reporte por ID",
)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    report = await reports_service.find_one(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
    return ReportResponse.model_validate(report)
