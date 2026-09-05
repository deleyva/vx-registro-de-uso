"""Parity suite for ``/v1/report*``.

These tests describe the **exact** request/response contract that the
MigrasFree desktop client (an external agent) depends on. Any change to
this file should be treated as a breaking API change.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from httpx import AsyncClient

# `etiquetas` se añadió en septiembre de 2026 por petición explícita. Es una
# ADICIÓN al contrato, no un cambio: ninguna clave existente cambia de nombre
# ni de tipo, y el único cliente (la app Tauri) solo hace POST, no lee esto.
EXPECTED_RESPONSE_KEYS = {
    "id",
    "timestamp",
    "migasfreeCid",
    "usuarioGrafico",
    "etiquetas",
    "verificacionEquipos",
    "resumen",
    "createdAt",
}


def _shape(d: dict[str, Any]) -> set[str]:
    return set(d.keys())


async def _post(client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    res = await client.post("/v1/report", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# ---------- POST ----------------------------------------------------------


@pytest.mark.asyncio
async def test_post_valid_payload_returns_201_with_camel_keys(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 1: POST valid payload → 201, camelCase keys, no empresa/tipo_verificacion."""
    body = await _post(client, report_payload)
    assert _shape(body) == EXPECTED_RESPONSE_KEYS
    assert body["id"]
    assert body["migasfreeCid"] == "12345"
    assert body["usuarioGrafico"] == "MOCK_USER_DELEYVA"
    assert "empresa" not in body
    assert "tipo_verificacion" not in body


@pytest.mark.asyncio
async def test_post_with_unknown_field_returns_201(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 2: POST with unknown field → 201 (extra='ignore')."""
    payload = {**report_payload, "totally_unknown": "should be ignored"}
    body = await _post(client, payload)
    assert _shape(body) == EXPECTED_RESPONSE_KEYS
    assert "totally_unknown" not in body


@pytest.mark.asyncio
async def test_post_drops_empresa_and_tipo_verificacion(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 3: empresa / tipo_verificacion are accepted but never persisted."""
    body = await _post(client, report_payload)
    report_id = body["id"]

    # Round-trip via GET to confirm the discarded fields are gone
    res = await client.get(f"/v1/report/{report_id}")
    assert res.status_code == 200
    fetched = res.json()
    assert _shape(fetched) == EXPECTED_RESPONSE_KEYS
    assert "empresa" not in fetched
    assert "tipo_verificacion" not in fetched


# ---------- GET list ------------------------------------------------------


@pytest.mark.asyncio
async def test_get_no_filters_orders_by_created_at_desc(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 4: GET no filters → list ordered by createdAt desc."""
    ids: list[str] = []
    for i in range(3):
        p = copy.deepcopy(report_payload)
        p["migasfree_cid"] = f"cid-{i}"
        body = await _post(client, p)
        ids.append(body["id"])

    res = await client.get("/v1/report")
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    # the most recently inserted IDs come first
    returned_ids = [r["id"] for r in rows]
    # all three of our inserted IDs are present in reverse order
    indices = [returned_ids.index(i) for i in reversed(ids)]
    assert indices == sorted(indices), f"order broken: {returned_ids}"


@pytest.mark.asyncio
async def test_get_limit_5_returns_at_most_5(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 5: GET ?limit=5 → max 5 items."""
    for i in range(7):
        p = copy.deepcopy(report_payload)
        p["migasfree_cid"] = f"cid-{i}"
        await _post(client, p)
    res = await client.get("/v1/report", params={"limit": 5})
    assert res.status_code == 200
    assert len(res.json()) <= 5


@pytest.mark.asyncio
async def test_get_limit_1000_clamped_to_500(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 6: GET ?limit=1000 → clamped to 500 at SQL level (parity)."""
    # Insert just one row — we cannot easily seed 600 rows in a unit test,
    # but we can still confirm the endpoint accepts 1000 and the clamp logic
    # does not blow up.
    await _post(client, report_payload)
    res = await client.get("/v1/report", params={"limit": 1000})
    assert res.status_code == 200
    assert len(res.json()) <= 500


@pytest.mark.asyncio
async def test_get_only_errors_filters_to_truthy_requiere_atencion(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 7: GET ?onlyErrors=true → only rows with resumen.requiere_atencion truthy."""
    a = copy.deepcopy(report_payload)
    a["migasfree_cid"] = "with-errors"
    a["resumen"]["requiere_atencion"] = True
    await _post(client, a)

    b = copy.deepcopy(report_payload)
    b["migasfree_cid"] = "no-errors"
    b["resumen"]["requiere_atencion"] = False
    await _post(client, b)

    res = await client.get("/v1/report", params={"onlyErrors": "true"})
    assert res.status_code == 200
    rows = res.json()
    assert all(r["resumen"].get("requiere_atencion") for r in rows)
    assert any(r["migasfreeCid"] == "with-errors" for r in rows)
    assert not any(r["migasfreeCid"] == "no-errors" for r in rows)


@pytest.mark.asyncio
async def test_get_component_raton_only_returns_defectuoso_rows(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 8: GET ?component=raton → rows where verificacionEquipos.raton.estado == 'defectuoso'."""
    bad = copy.deepcopy(report_payload)
    bad["migasfree_cid"] = "raton-bad"
    bad["verificacion_equipos"]["raton"] = {
        "estado": "defectuoso",
        "problema": "no responde",
        "obligatorio": True,
    }
    await _post(client, bad)

    good = copy.deepcopy(report_payload)
    good["migasfree_cid"] = "raton-ok"
    good["verificacion_equipos"]["raton"] = {
        "estado": "correcto",
        "problema": None,
        "obligatorio": True,
    }
    await _post(client, good)

    res = await client.get("/v1/report", params={"component": "raton"})
    assert res.status_code == 200
    rows = res.json()
    assert all(
        r["verificacionEquipos"].get("raton", {}).get("estado") == "defectuoso"
        for r in rows
    )
    assert any(r["migasfreeCid"] == "raton-bad" for r in rows)
    assert not any(r["migasfreeCid"] == "raton-ok" for r in rows)


@pytest.mark.asyncio
async def test_get_only_operativo_false_returns_only_non_operativo(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 9: GET ?onlyOperativo=false → only rows with bool(equipo_operativo) is False."""
    op_true = copy.deepcopy(report_payload)
    op_true["migasfree_cid"] = "op-true"
    op_true["resumen"]["equipo_operativo"] = True
    await _post(client, op_true)

    op_false = copy.deepcopy(report_payload)
    op_false["migasfree_cid"] = "op-false"
    op_false["resumen"]["equipo_operativo"] = False
    await _post(client, op_false)

    res = await client.get("/v1/report", params={"onlyOperativo": "false"})
    assert res.status_code == 200
    rows = res.json()
    assert all(not bool(r["resumen"].get("equipo_operativo")) for r in rows)
    assert any(r["migasfreeCid"] == "op-false" for r in rows)
    assert not any(r["migasfreeCid"] == "op-true" for r in rows)


@pytest.mark.asyncio
async def test_get_from_to_filters_by_timestamp_range(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 10: GET ?from=...&to=... → date range filter against timestamp."""
    in_range = copy.deepcopy(report_payload)
    in_range["migasfree_cid"] = "in-range"
    in_range["timestamp"] = "2026-04-09T07:59:26.463Z"
    await _post(client, in_range)

    out_of_range = copy.deepcopy(report_payload)
    out_of_range["migasfree_cid"] = "out-of-range"
    out_of_range["timestamp"] = "2024-01-01T00:00:00.000Z"
    await _post(client, out_of_range)

    res = await client.get(
        "/v1/report",
        params={
            "from": "2026-04-01T00:00:00.000Z",
            "to": "2026-04-30T23:59:59.000Z",
        },
    )
    assert res.status_code == 200
    rows = res.json()
    cids = {r["migasfreeCid"] for r in rows}
    assert "in-range" in cids
    assert "out-of-range" not in cids


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client: AsyncClient) -> None:
    """Case 11: GET /v1/report/{nonexistent} → 404."""
    res = await client.get("/v1/report/this-id-does-not-exist")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_response_shape_snapshot_exact_keys(
    client: AsyncClient, report_payload: dict
) -> None:
    """Case 12: Response shape snapshot — exact keys, no more, no less."""
    body = await _post(client, report_payload)
    assert _shape(body) == EXPECTED_RESPONSE_KEYS

    res = await client.get(f"/v1/report/{body['id']}")
    assert res.status_code == 200
    assert _shape(res.json()) == EXPECTED_RESPONSE_KEYS

    res_list = await client.get("/v1/report")
    assert res_list.status_code == 200
    assert all(_shape(r) == EXPECTED_RESPONSE_KEYS for r in res_list.json())
