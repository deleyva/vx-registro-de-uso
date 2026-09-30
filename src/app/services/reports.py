"""Reports service — port of NestJS ``ReportsService``.

The filtering logic is intentionally implemented **in Python**, after the
SQL query has been executed and the rows have been LIMITed. This mirrors
exactly what the original NestJS service does and is part of the parity
contract with MigrasFree. Do **not** move this filtering into SQL JSONB
expressions — even if it's technically more efficient — without explicitly
versioning the API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


@dataclass
class ReportFilters:
    from_: datetime | None = None
    to: datetime | None = None
    only_errors: bool | None = None
    component: str | None = None
    only_operativo: bool | None = None


def _clamp_limit(limit: int) -> int:
    return min(max(limit, 1), 500)


def _passes_filters(report: Report, filters: ReportFilters) -> bool:
    """Replicate the in-memory filter logic from ``reports.service.ts``."""

    # Date range against report.timestamp
    if filters.from_ is not None:
        if _strip_tz(report.timestamp) < _strip_tz(filters.from_):
            return False
    if filters.to is not None:
        if _strip_tz(report.timestamp) > _strip_tz(filters.to):
            return False

    # only_errors → resumen.requiere_atencion must be truthy
    if filters.only_errors:
        resumen: dict[str, Any] = report.resumen or {}
        if not bool(resumen.get("requiere_atencion")):
            return False

    # component → verificacion_equipos[component].estado must be "defectuoso"
    if filters.component:
        ve: dict[str, Any] = report.verificacion_equipos or {}
        entry = ve.get(filters.component)
        if not entry:
            return False
        if not isinstance(entry, dict) or entry.get("estado") != "defectuoso":
            return False

    # only_operativo → bool(resumen.equipo_operativo) must equal filter
    if filters.only_operativo is not None:
        resumen = report.resumen or {}
        operativo = bool(resumen.get("equipo_operativo"))
        if filters.only_operativo != operativo:
            return False

    return True


def _strip_tz(dt: datetime) -> datetime:
    """Return a naive datetime so range comparisons work regardless of tz."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


async def create(db: AsyncSession, payload: dict[str, Any]) -> Report:
    """Insert a Report row from a (already-validated) payload dict.

    Solo se almacenan los campos que el esquema declara; cualquier otro que
    llegue en el cuerpo ya se ha descartado al validar.
    """
    report = Report(
        timestamp=payload["timestamp"],
        migasfree_cid=payload["migasfree_cid"],
        usuario_grafico=payload["usuario_grafico"],
        etiquetas=payload.get("etiquetas"),
        verificacion_equipos=payload["verificacion_equipos"],
        resumen=payload["resumen"],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def find_all(
    db: AsyncSession,
    limit: int = 50,
    filters: ReportFilters | None = None,
) -> list[Report]:
    """List reports — limit-clamped at SQL level, filtered in Python."""
    take = _clamp_limit(limit)
    filters = filters or ReportFilters()

    stmt = select(Report).order_by(Report.created_at.desc()).limit(take)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [r for r in rows if _passes_filters(r, filters)]


PANEL_DEFAULT_LIMIT = 200
PANEL_RANGE_LIMIT = 2000
PANEL_MAX_LIMIT = 5000


@dataclass
class PanelPage:
    """Lo que el panel necesita para pintar la tabla y decir si está truncada."""

    reports: list[Report]
    total_in_range: int
    limit: int

    @property
    def truncated(self) -> bool:
        return self.total_in_range > self.limit


async def find_for_panel(
    db: AsyncSession,
    *,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    filters: ReportFilters | None = None,
) -> PanelPage:
    """Listado para el panel web: el rango de fechas se aplica en SQL.

    Esto NO es el contrato de ``/v1/report`` (ese sigue en ``find_all`` y filtra
    en Python después del LIMIT, por paridad con NestJS). El panel no tiene ese
    compromiso, y filtrar después de cortar hacía que «Desde/Hasta» solo
    buscase entre las 200 filas más recientes: pedir una semana atrás devolvía
    la tabla vacía aunque los datos estuvieran en la base.

    ``start`` es inclusivo y ``end`` exclusivo, ambos con zona horaria; el
    router los construye a partir de los días elegidos en Europe/Madrid. Los
    filtros JSONB (errores, componente, operativo) se siguen aplicando en Python
    sobre las filas devueltas, con la misma semántica que en la API.
    """
    take = min(max(limit, 1), PANEL_MAX_LIMIT)
    filters = filters or ReportFilters(only_errors=None, component=None, only_operativo=None)

    conditions = []
    if start is not None:
        conditions.append(Report.timestamp >= start)
    if end is not None:
        conditions.append(Report.timestamp < end)

    count_stmt = select(func.count()).select_from(Report).where(*conditions)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(Report)
        .where(*conditions)
        .order_by(Report.timestamp.desc(), Report.created_at.desc())
        .limit(take)
    )
    rows = list((await db.execute(stmt)).scalars().all())

    # El rango de fechas ya está resuelto en SQL; aquí solo quedan los JSONB.
    jsonb_only = ReportFilters(
        only_errors=filters.only_errors,
        component=filters.component,
        only_operativo=filters.only_operativo,
    )
    kept = [r for r in rows if _passes_filters(r, jsonb_only)]
    return PanelPage(reports=kept, total_in_range=total, limit=take)


async def find_one(db: AsyncSession, report_id: str) -> Report | None:
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
