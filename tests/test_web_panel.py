"""Panel web: filtro de fechas real y refresco que conserva los filtros.

Iteración 6 (2026-09-30). El panel pedía las 200 últimas filas y filtraba
después, así que «Desde/Hasta» solo veía dos días de historial; y el refresco
periódico pedía `/?partial=1` sin parámetros, borrando cualquier filtro. Estos
tests fijan el comportamiento nuevo del panel; el contrato de `/v1/report` no
se toca (ver `test_reports_v1.py`).
"""

from __future__ import annotations

import copy
import re

import pytest
from httpx import AsyncClient

HX = {"HX-Request": "true"}


async def _post(client: AsyncClient, payload: dict, *, cid: str, ts: str) -> None:
    body = copy.deepcopy(payload)
    body["migasfree_cid"] = cid
    body["timestamp"] = ts
    res = await client.post("/v1/report", json=body)
    assert res.status_code == 201, res.text


def _rows(html: str) -> int:
    return len(re.findall(r"<tr class=\"hover:bg-gray-50", html))


@pytest.mark.asyncio
async def test_rango_de_fechas_alcanza_mas_alla_de_las_200_ultimas(
    client: AsyncClient, report_payload: dict
) -> None:
    """ISC-23: un informe de hace tres días se encuentra aunque haya 201 más
    recientes; sin rango, el panel sigue enseñando solo lo último."""
    await _post(client, report_payload, cid="VIEJO", ts="2026-09-27T10:00:00Z")
    for i in range(201):
        await _post(client, report_payload, cid=f"HOY{i}", ts=f"2026-09-30T10:{i // 60:02d}:{i % 60:02d}Z")

    res = await client.get("/?from=2026-09-27&to=2026-09-27", headers=HX)
    assert res.status_code == 200
    assert "VIEJO" in res.text
    assert _rows(res.text) == 1

    res = await client.get("/", headers=HX)
    assert _rows(res.text) == 200
    assert "VIEJO" not in res.text


@pytest.mark.asyncio
async def test_limites_del_dia_en_hora_de_madrid(client: AsyncClient, report_payload: dict) -> None:
    """ISC-24: 23:30 de Madrid del día 24 (21:30Z) entra en `to=24`; 00:30 de
    Madrid del 25 (22:30Z del 24) no."""
    await _post(client, report_payload, cid="TARDE24", ts="2026-09-24T21:30:00Z")
    await _post(client, report_payload, cid="PRONTO25", ts="2026-09-24T22:30:00Z")

    res = await client.get("/?from=2026-09-24&to=2026-09-24", headers=HX)
    assert "TARDE24" in res.text
    assert "PRONTO25" not in res.text

    res = await client.get("/?from=2026-09-25&to=2026-09-25", headers=HX)
    assert "PRONTO25" in res.text
    assert "TARDE24" not in res.text


@pytest.mark.asyncio
async def test_rango_invertido_se_ordena_y_un_solo_extremo_vale(
    client: AsyncClient, report_payload: dict
) -> None:
    await _post(client, report_payload, cid="DIA20", ts="2026-09-20T10:00:00Z")
    await _post(client, report_payload, cid="DIA22", ts="2026-09-22T10:00:00Z")
    await _post(client, report_payload, cid="DIA24", ts="2026-09-24T10:00:00Z")

    res = await client.get("/?from=2026-09-22&to=2026-09-20", headers=HX)
    assert _rows(res.text) == 2
    assert "DIA24" not in res.text

    res = await client.get("/?from=2026-09-22", headers=HX)
    assert _rows(res.text) == 2

    res = await client.get("/?to=2026-09-21", headers=HX)
    assert _rows(res.text) == 1


@pytest.mark.asyncio
async def test_truncado_avisa_con_el_total_del_rango(client: AsyncClient, report_payload: dict) -> None:
    """ISC-30: si el rango tiene más informes que el límite, la tabla lo dice."""
    for i in range(3):
        await _post(client, report_payload, cid=f"R{i}", ts=f"2026-09-25T1{i}:00:00Z")

    res = await client.get("/?from=2026-09-25&to=2026-09-25&limit=2", headers=HX)
    assert _rows(res.text) == 2
    assert "El rango tiene 3 informes" in res.text
    assert "solo se muestran los 2 más recientes" in res.text

    res = await client.get("/?from=2026-09-25&to=2026-09-25", headers=HX)
    assert "El rango tiene" not in res.text


@pytest.mark.asyncio
async def test_los_filtros_jsonb_siguen_aplicando_en_el_panel(
    client: AsyncClient, report_payload: dict
) -> None:
    ok = copy.deepcopy(report_payload)
    ok["verificacion_equipos"]["raton"] = {"estado": "correcto", "problema": None, "obligatorio": True}
    ok["resumen"] = {"total_componentes": 5, "equipo_operativo": True, "requiere_atencion": False}
    await _post(client, ok, cid="SANO", ts="2026-09-25T10:00:00Z")
    await _post(client, report_payload, cid="ROTO", ts="2026-09-25T11:00:00Z")

    res = await client.get("/?from=2026-09-25&to=2026-09-25&onlyErrors=true", headers=HX)
    assert "ROTO" in res.text and "SANO" not in res.text

    res = await client.get("/?from=2026-09-25&to=2026-09-25&component=raton", headers=HX)
    assert "ROTO" in res.text and "SANO" not in res.text

    res = await client.get("/?from=2026-09-25&to=2026-09-25&onlyOperativo=true", headers=HX)
    assert "SANO" in res.text and "ROTO" not in res.text


@pytest.mark.asyncio
async def test_pagina_completa_y_refresco_conservan_los_filtros(
    client: AsyncClient, report_payload: dict
) -> None:
    """ISC-25, ISC-27, ISC-29: sin `partial=1` en el formulario; el contenedor
    se refresca incluyendo el formulario y sin disparo en `load`; la página
    completa pinta el rango elegido en los campos ocultos."""
    await _post(client, report_payload, cid="X", ts="2026-09-25T10:00:00Z")

    res = await client.get("/?from=2026-09-24&to=2026-09-26")
    assert res.status_code == 200
    html = res.text
    assert 'id="filters-form"' in html
    assert 'name="partial"' not in html
    assert 'hx-include="#filters-form"' in html
    assert 'hx-trigger="every 30s"' in html
    assert 'hx-get="/?partial=1"' not in html
    assert 'name="from" id="drp-from" value="2026-09-24"' in html
    assert 'name="to" id="drp-to" value="2026-09-26"' in html
    assert 'id="drp-grid"' in html

    res = await client.get("/?limit=500")
    assert 'name="limit" value="500"' in res.text

    res = await client.get("/?from=2026-09-24&to=2026-09-26", headers=HX)
    assert "<form" not in res.text
    assert "X" in res.text


@pytest.mark.asyncio
async def test_estaticos_llevan_huella_de_contenido(client: AsyncClient) -> None:
    """La hoja de estilos y HTMX se piden con `?v=<hash>` del contenido, para que
    un despliegue no deje al navegador con la copia vieja en caché (2026-10-01:
    el calendario salía sin estilos por eso). La URL versionada sirve el fichero."""
    html = (await client.get("/")).text
    urls = re.findall(r'(?:href|src)="(/static/[^"]+)"', html)
    assert any(u.startswith("/static/css/tailwind.css?v=") for u in urls), urls
    assert any(u.startswith("/static/vendor/htmx.min.js?v=") for u in urls), urls
    for url in urls:
        assert re.search(r"\?v=[0-9a-f]{10}$", url), url
        assert (await client.get(url)).status_code == 200, url
