"""Exportación a CSV desde la cabecera de la tabla (iteración 7, 2026-10-15)."""

from __future__ import annotations

import copy
import csv
import io
import re

import pytest
from httpx import AsyncClient

from app.services import reports as reports_service

HX = {"HX-Request": "true"}


async def _post(client: AsyncClient, payload: dict, *, cid: str, ts: str, **changes) -> None:
    body = copy.deepcopy(payload)
    body["migasfree_cid"] = cid
    body["timestamp"] = ts
    body.update(changes)
    res = await client.post("/v1/report", json=body)
    assert res.status_code == 201, res.text


def _parse(content: bytes) -> list[list[str]]:
    assert content.startswith(b"\xef\xbb\xbf"), "falta el BOM UTF-8"
    return list(csv.reader(io.StringIO(content.decode("utf-8-sig")), delimiter=";"))


@pytest.mark.asyncio
async def test_botones_llevan_los_filtros_aplicados(client: AsyncClient, report_payload: dict) -> None:
    """ISC-33."""
    await _post(client, report_payload, cid="A", ts="2026-09-24T10:00:00Z")
    res = await client.get("/?from=2026-09-24&to=2026-09-25&onlyErrors=true&component=raton", headers=HX)
    hrefs = re.findall(r'href="(/export\.csv[^"]*)"', res.text)
    assert len(hrefs) == 2
    for mode, href in zip(("informes", "fallos"), hrefs, strict=True):
        href = href.replace("&amp;", "&")
        assert f"mode={mode}" in href
        for part in ("from=2026-09-24", "to=2026-09-25", "onlyErrors=true", "component=raton"):
            assert part in href
        assert "onlyOperativo" not in href


@pytest.mark.asyncio
async def test_csv_por_informe(client: AsyncClient, report_payload: dict) -> None:
    """ISC-34."""
    await _post(client, report_payload, cid="MALO", ts="2026-09-24T10:00:00Z", hostname="aula-01")
    ok = copy.deepcopy(report_payload)
    ok["verificacion_equipos"]["raton"] = {"estado": "correcto", "problema": None, "obligatorio": True}
    ok["resumen"] = {"equipo_operativo": True, "requiere_atencion": False}
    await _post(client, ok, cid="BUENO", ts="2026-09-24T11:00:00Z")

    res = await client.get("/export.csv?mode=informes&from=2026-09-24&to=2026-09-24")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="vx-informes_2026-09-24_2026-09-24.csv"' == res.headers["content-disposition"]
    rows = _parse(res.content)
    header, body = rows[0], rows[1:]
    assert header[:7] == ["Fecha", "Equipo", "CID", "Usuario", "Etiquetas", "Operativo", "Requiere atención"]
    assert "Ratón" in header and header[-1] == "Problemas"
    assert [r[2] for r in body] == ["BUENO", "MALO"]
    malo = body[1]
    assert malo[0] == "24/09/2026, 12:00:00"  # Madrid
    assert malo[1] == "aula-01"
    assert malo[header.index("Ratón")] == "defectuoso"
    assert malo[-1] == "Ratón: no responde"
    assert body[0][-1] == ""

    res = await client.get("/export.csv?mode=informes&onlyErrors=true")
    assert [r[2] for r in _parse(res.content)[1:]] == ["MALO"]


@pytest.mark.asyncio
async def test_csv_por_fallo_y_filtro_de_componente(client: AsyncClient, report_payload: dict) -> None:
    """ISC-35."""
    body = copy.deepcopy(report_payload)
    body["verificacion_equipos"]["pantalla"] = {"estado": "defectuoso", "problema": "rayas", "obligatorio": True}
    body["verificacion_equipos"]["bateria"] = {"estado": "no_verificado", "problema": None, "obligatorio": False}
    await _post(client, body, cid="X", ts="2026-09-24T10:00:00Z")

    rows = _parse((await client.get("/export.csv?mode=fallos")).content)
    assert rows[0] == ["Fecha", "Equipo", "CID", "Usuario", "Etiquetas", "Componente", "Estado", "Obligatorio", "Problema"]
    assert sorted((r[5], r[8]) for r in rows[1:]) == [("Pantalla", "rayas"), ("Ratón", "no responde")]

    rows = _parse((await client.get("/export.csv?mode=fallos&component=raton")).content)
    assert [(r[5], r[7], r[8]) for r in rows[1:]] == [("Ratón", "Sí", "no responde")]


@pytest.mark.asyncio
async def test_no_se_recorta_al_limite_del_panel(client: AsyncClient, report_payload: dict, monkeypatch) -> None:
    """ISC-36: la tabla enseña 200, el CSV trae los 201; por encima del tope, 422."""
    for i in range(201):
        await _post(client, report_payload, cid=f"C{i}", ts=f"2026-09-30T10:{i // 60:02d}:{i % 60:02d}Z")

    rows = _parse((await client.get("/export.csv?mode=informes")).content)
    assert len(rows) - 1 == 201

    monkeypatch.setattr(reports_service, "EXPORT_MAX_ROWS", 100)
    res = await client.get("/export.csv?mode=fallos")
    assert res.status_code == 422
    assert "Acorta el rango" in res.text
    panel = await client.get("/", headers=HX)
    assert "Acorta el rango para exportar" in panel.text
    assert "/export.csv" not in panel.text


@pytest.mark.asyncio
async def test_modo_desconocido(client: AsyncClient) -> None:
    res = await client.get("/export.csv?mode=pdf")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_neutraliza_formulas(client: AsyncClient, report_payload: dict) -> None:
    """ISC-38."""
    body = copy.deepcopy(report_payload)
    body["verificacion_equipos"]["raton"]["problema"] = "=HYPERLINK(\"http://x\")"
    await _post(client, body, cid="F", ts="2026-09-24T10:00:00Z", usuario_grafico="@alumno")
    rows = _parse((await client.get("/export.csv?mode=fallos")).content)
    assert rows[1][3] == "'@alumno"
    assert rows[1][8].startswith("'=")


@pytest.mark.asyncio
async def test_sin_sesion_no_exporta(client: AsyncClient, seeded_access_password) -> None:
    """ISC-37."""
    res = await client.get("/export.csv?mode=informes")
    assert res.status_code == 303
    assert res.headers["location"].startswith("/login")
