"""Pure schema tests — no DB or HTTP layer."""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.camel import to_camel
from app.schemas.reports import CreateReportRequest, ReportResponse


def test_to_camel() -> None:
    assert to_camel("foo") == "foo"
    assert to_camel("foo_bar") == "fooBar"
    assert to_camel("migasfree_cid") == "migasfreeCid"
    assert to_camel("verificacion_equipos") == "verificacionEquipos"


def test_create_request_accepts_extra_fields_and_ignores_them() -> None:
    payload = {
        "timestamp": "2026-04-09T07:59:26.463Z",
        "migasfree_cid": "12345",
        "usuario_grafico": "MOCK",
        "empresa": "VITALINUX",
        "tipo_verificacion": "equipos_escritorio",
        "verificacion_equipos": {"pantalla": {"estado": "correcto"}},
        "resumen": {"equipo_operativo": True},
        "field_we_dont_know_about": "ignored",
    }
    parsed = CreateReportRequest.model_validate(payload)
    assert parsed.empresa == "VITALINUX"
    assert parsed.tipo_verificacion == "equipos_escritorio"
    # extra="ignore" — unknown fields silently dropped
    assert not hasattr(parsed, "field_we_dont_know_about")


def test_response_serialization_uses_camel_keys() -> None:
    resp = ReportResponse(
        id="abc",
        timestamp=datetime(2026, 4, 9, 7, 59, 26, tzinfo=UTC),
        migasfree_cid="12345",
        usuario_grafico="MOCK",
        verificacion_equipos={"pantalla": {"estado": "correcto"}},
        resumen={"equipo_operativo": True},
        created_at=datetime(2026, 4, 9, 8, 0, 0, tzinfo=UTC),
    )
    dumped = resp.model_dump(by_alias=True)
    assert set(dumped.keys()) == {
        "id",
        "timestamp",
        "migasfreeCid",
        "usuarioGrafico",
        "verificacionEquipos",
        "resumen",
        "createdAt",
    }
