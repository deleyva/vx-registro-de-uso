"""Exportación a CSV de lo que muestra el panel.

Dos formas del mismo dato:

* ``informes`` — una fila por informe, como la tabla, con el estado de cada
  componente y una columna que junta los problemas.
* ``fallos`` — una fila por componente defectuoso, con su ``problema``. Es la que
  se le pasa al técnico.

El fichero lleva BOM y separador ``;`` para que Excel en castellano y LibreOffice
lo abran con acentos y columnas correctos sin tocar nada.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.models.report import Report

MODES = ("informes", "fallos")

# Mismo criterio que la tabla: estos dos estados se pintan en verde.
OK_STATES = ("correcto", "no_verificado")

# Un valor que empieza así lo interpreta la hoja de cálculo como fórmula. El
# `problema` lo escribe quien usa el equipo, así que no es de fiar.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _yes_no(value: Any) -> str:
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    return ""


def _is_fault(item: Any) -> bool:
    return isinstance(item, dict) and item.get("estado") not in OK_STATES


def _components_in(reports: list[Report], preferred: list[str]) -> list[str]:
    found: set[str] = set()
    for r in reports:
        found.update((r.verificacion_equipos or {}).keys())
    return [k for k in preferred if k in found] + sorted(k for k in found if k not in preferred)


def build_csv(
    reports: list[Report],
    *,
    mode: str,
    component: str | None,
    preferred: list[str],
    labels: dict[str, str],
    fmt_dt: Callable[[datetime], str],
) -> str:
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    label = lambda k: labels.get(k, k)  # noqa: E731

    if mode == "fallos":
        w.writerow(["Fecha", "Equipo", "CID", "Usuario", "Etiquetas", "Componente", "Estado", "Obligatorio", "Problema"])
        for r in reports:
            for key, item in (r.verificacion_equipos or {}).items():
                if component and key != component:
                    continue
                if not _is_fault(item):
                    continue
                w.writerow(
                    [
                        fmt_dt(r.timestamp),
                        _safe(r.hostname),
                        _safe(r.migasfree_cid),
                        _safe(r.usuario_grafico),
                        _safe(r.etiquetas),
                        label(key),
                        _safe(item.get("estado")),
                        _yes_no(item.get("obligatorio")),
                        _safe(item.get("problema")),
                    ]
                )
        return buf.getvalue()

    components = _components_in(reports, preferred)
    w.writerow(
        ["Fecha", "Equipo", "CID", "Usuario", "Etiquetas", "Operativo", "Requiere atención"]
        + [label(c) for c in components]
        + ["Problemas"]
    )
    for r in reports:
        ve: dict[str, Any] = r.verificacion_equipos or {}
        resumen: dict[str, Any] = r.resumen or {}
        problems = [
            f"{label(k)}: {item.get('problema') or item.get('estado')}" for k, item in ve.items() if _is_fault(item)
        ]
        w.writerow(
            [
                fmt_dt(r.timestamp),
                _safe(r.hostname),
                _safe(r.migasfree_cid),
                _safe(r.usuario_grafico),
                _safe(r.etiquetas),
                _yes_no(resumen.get("equipo_operativo")),
                _yes_no(resumen.get("requiere_atencion")),
            ]
            + [_safe((ve.get(c) or {}).get("estado") if isinstance(ve.get(c), dict) else "") for c in components]
            + [_safe(" | ".join(problems))]
        )
    return buf.getvalue()
