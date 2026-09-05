"""Autenticación: guardia de sesión, roles y rotación de la clave.

Cada test nombra el ISC de ISA.md que cierra.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import session as session_module


async def _login(client: AsyncClient, password: str):
    return await client.post("/login", data={"password": password, "next": "/"})


# --- ISC-1 · el panel exige sesión ------------------------------------


async def test_panel_sin_sesion_redirige_a_login(client, seeded_access_password):
    response = await client.get("/")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


async def test_panel_con_sesion_responde_200(client, seeded_access_password):
    assert (await _login(client, seeded_access_password)).status_code == 303
    response = await client.get("/")
    assert response.status_code == 200
    assert "VX Reportes" in response.text


# --- ISC-2 · la API de lectura también está cerrada -------------------


async def test_get_report_sin_sesion_responde_401(client, seeded_access_password):
    assert (await client.get("/v1/report")).status_code == 401
    assert (await client.get("/v1/report/inexistente")).status_code == 401


async def test_get_report_con_sesion_responde_200(client, seeded_access_password):
    await _login(client, seeded_access_password)
    response = await client.get("/v1/report")
    assert response.status_code == 200
    assert response.json() == []


# --- ISC-3 · la ingesta del cliente Tauri sigue abierta ---------------


async def test_post_report_sin_sesion_sigue_creando(
    client, seeded_access_password, report_payload
):
    response = await client.post("/v1/report", json=report_payload)
    assert response.status_code == 201


async def test_post_report_exige_token_solo_si_esta_configurado(
    client, auth_settings, monkeypatch, report_payload
):
    monkeypatch.setattr(auth_settings, "ingest_token", "token-secreto")
    assert (await client.post("/v1/report", json=report_payload)).status_code == 401
    ok = await client.post(
        "/v1/report", json=report_payload, headers={"X-VX-Token": "token-secreto"}
    )
    assert ok.status_code == 201


# --- ISC-4, ISC-5, ISC-6 · login --------------------------------------


async def test_login_con_clave_de_acceso_abre_sesion_de_lectura(
    client, seeded_access_password
):
    assert (await _login(client, seeded_access_password)).status_code == 303
    assert (await client.get("/")).status_code == 200
    # rol viewer: sin acceso a administración
    assert (await client.get("/admin")).status_code == 403


async def test_login_con_clave_de_admin_abre_sesion_de_administracion(
    client, seeded_access_password
):
    assert (await _login(client, "admin-de-prueba")).status_code == 303
    assert (await client.get("/admin")).status_code == 200


async def test_login_con_clave_incorrecta_no_abre_sesion(
    client, seeded_access_password
):
    response = await _login(client, "no-es-la-clave")
    assert response.status_code == 401
    assert (await client.get("/")).status_code == 303


# --- ISC-7, ISC-8 · solo la clave de admin rota la de acceso ----------


async def test_rotar_sin_clave_de_admin_responde_403_y_no_cambia_nada(
    client, seeded_access_password
):
    await _login(client, "admin-de-prueba")
    response = await client.post(
        "/admin/rotate",
        data={
            "admin_password": "clave-equivocada",
            "new_password": "clave-nueva-larga",
            "new_password_confirm": "clave-nueva-larga",
        },
    )
    assert response.status_code == 403

    # la clave antigua sigue siendo válida en una sesión limpia
    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as otro:
        assert (await _login(otro, seeded_access_password)).status_code == 303


async def test_rotar_exige_confirmacion_y_longitud_minima(
    client, seeded_access_password
):
    await _login(client, "admin-de-prueba")
    corta = await client.post(
        "/admin/rotate",
        data={
            "admin_password": "admin-de-prueba",
            "new_password": "corta",
            "new_password_confirm": "corta",
        },
    )
    assert corta.status_code == 400

    dispar = await client.post(
        "/admin/rotate",
        data={
            "admin_password": "admin-de-prueba",
            "new_password": "clave-nueva-larga",
            "new_password_confirm": "otra-cosa-distinta",
        },
    )
    assert dispar.status_code == 400


# --- ISC-9 · rotar expulsa a las sesiones abiertas --------------------


async def test_rotar_invalida_las_sesiones_de_lectura_abiertas(
    client, seeded_access_password
):
    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as profe:
        await _login(profe, seeded_access_password)
        assert (await profe.get("/")).status_code == 200

        await _login(client, "admin-de-prueba")
        rotado = await client.post(
            "/admin/rotate",
            data={
                "admin_password": "admin-de-prueba",
                "new_password": "clave-nueva-larga",
                "new_password_confirm": "clave-nueva-larga",
            },
        )
        assert rotado.status_code == 200

        # la sesión del profesor, abierta con la clave antigua, ya no vale
        assert (await profe.get("/")).status_code == 303
        # y la sesión de administración sobrevive a su propia rotación
        assert (await client.get("/admin")).status_code == 200

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as nuevo:
        assert (await _login(nuevo, "clave-nueva-larga")).status_code == 303
        assert (await _login(nuevo, seeded_access_password)).status_code == 401


# --- ISC-10 · la clave nunca se guarda en claro -----------------------


async def test_la_clave_de_acceso_se_guarda_hasheada(client, seeded_access_password):
    async with session_module.SessionLocal() as db:
        result = await db.execute(
            text("SELECT value FROM app_settings WHERE key = 'access_password'")
        )
        stored = result.scalar_one()
    assert stored.startswith("scrypt$")
    assert seeded_access_password not in stored


# --- ISC-11 · superficie pública mínima -------------------------------


@pytest.mark.parametrize("path", ["/health", "/login"])
async def test_rutas_publicas_sin_sesion(client, seeded_access_password, path):
    assert (await client.get(path)).status_code == 200


async def test_logout_cierra_la_sesion(client, seeded_access_password):
    await _login(client, seeded_access_password)
    assert (await client.get("/")).status_code == 200
    assert (await client.get("/logout")).status_code == 303
    assert (await client.get("/")).status_code == 303


# --- ISC-13..ISC-16 · clave de administración delegada ----------------


async def _set_admin_password(client: AsyncClient, current: str, nueva: str):
    return await client.post(
        "/admin/admin-password",
        data={
            "current_password": current,
            "new_password": nueva,
            "new_password_confirm": nueva,
        },
    )


async def test_la_llave_maestra_crea_la_clave_de_admin_delegada(
    client, seeded_access_password
):
    """ISC-13: quien tiene la llave maestra le da una clave inicial a otro."""
    await _login(client, "admin-de-prueba")
    assert (await _set_admin_password(client, "admin-de-prueba", "clave-delegada")).status_code == 200

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as delegado:
        assert (await _login(delegado, "clave-delegada")).status_code == 303
        assert (await delegado.get("/admin")).status_code == 200


async def test_el_delegado_rota_su_propia_clave_sin_perder_la_sesion(
    client, seeded_access_password
):
    """ISC-14: administrar desde el navegador, sin tocar el servidor."""
    await _login(client, "admin-de-prueba")
    await _set_admin_password(client, "admin-de-prueba", "clave-delegada")

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as delegado:
        await _login(delegado, "clave-delegada")
        rotado = await _set_admin_password(
            delegado, "clave-delegada", "clave-delegada-2"
        )
        assert rotado.status_code == 200
        # su propia sesión sigue viva tras cambiarse la clave a sí mismo
        assert (await delegado.get("/admin")).status_code == 200

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as otro:
        assert (await _login(otro, "clave-delegada-2")).status_code == 303
        assert (await _login(otro, "clave-delegada")).status_code == 401


async def test_la_llave_maestra_sigue_entrando_pase_lo_que_pase(
    client, seeded_access_password
):
    """ISC-15: ninguna ruta de la interfaz puede dejar fuera al del servidor."""
    await _login(client, "admin-de-prueba")
    await _set_admin_password(client, "admin-de-prueba", "clave-delegada")

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as delegado:
        await _login(delegado, "clave-delegada")
        # el delegado cambia la clave otra vez, a algo que el maestro no sabe
        await _set_admin_password(delegado, "clave-delegada", "solo-la-se-yo")

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as maestro:
        assert (await _login(maestro, "admin-de-prueba")).status_code == 303
        assert (await maestro.get("/admin")).status_code == 200


async def test_cambiar_la_clave_delegada_no_cierra_las_sesiones_maestras(
    client, seeded_access_password
):
    """ISC-16: cada llave cierra sus sesiones, no las de la otra."""
    await _login(client, "admin-de-prueba")
    await _set_admin_password(client, "admin-de-prueba", "clave-delegada")

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as delegado:
        await _login(delegado, "clave-delegada")
        await _set_admin_password(delegado, "clave-delegada", "clave-delegada-2")
        # la sesión abierta con la llave maestra no se entera
        assert (await client.get("/admin")).status_code == 200
        # y la del delegado que rotó tampoco se cae
        assert (await delegado.get("/admin")).status_code == 200


async def test_sin_clave_actual_correcta_no_se_cambia_nada(
    client, seeded_access_password
):
    await _login(client, "admin-de-prueba")
    await _set_admin_password(client, "admin-de-prueba", "clave-delegada")

    fallo = await _set_admin_password(client, "no-es-la-clave", "intento-de-robo")
    assert fallo.status_code == 403

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as otro:
        assert (await _login(otro, "clave-delegada")).status_code == 303
        assert (await _login(otro, "intento-de-robo")).status_code == 401


async def test_un_lector_no_puede_tocar_la_clave_de_administracion(
    client, seeded_access_password
):
    await _login(client, seeded_access_password)
    assert (await _set_admin_password(client, "lo-que-sea", "clave-nueva-larga")).status_code == 403


async def test_la_clave_delegada_tambien_se_guarda_hasheada(
    client, seeded_access_password
):
    await _login(client, "admin-de-prueba")
    await _set_admin_password(client, "admin-de-prueba", "clave-delegada")
    async with session_module.SessionLocal() as db:
        result = await db.execute(
            text("SELECT value FROM app_settings WHERE key = 'admin_password'")
        )
        stored = result.scalar_one()
    assert stored.startswith("scrypt$")
    assert "clave-delegada" not in stored


# --- ISC-17..ISC-19 · interruptor de login ----------------------------


async def _toggle_login(client: AsyncClient, admin_password: str, enabled: bool):
    return await client.post(
        "/admin/login-toggle",
        data={"admin_password": admin_password, "enabled": "true" if enabled else "false"},
    )


async def test_quitar_el_login_abre_el_panel(client, seeded_access_password):
    """ISC-17: sin login, leer el panel no pide nada."""
    await _login(client, "admin-de-prueba")
    assert (await _toggle_login(client, "admin-de-prueba", False)).status_code == 200

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as anonimo:
        assert (await anonimo.get("/")).status_code == 200
        assert (await anonimo.get("/v1/report")).status_code == 200


async def test_sin_login_admin_sigue_cerrada(client, seeded_access_password):
    """ISC-18: quitar el login no regala la administración a nadie."""
    await _login(client, "admin-de-prueba")
    await _toggle_login(client, "admin-de-prueba", False)

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as anonimo:
        assert (await anonimo.get("/admin")).status_code == 303
        # y tampoco puede volver a activarlo ni cambiar claves
        assert (await _toggle_login(anonimo, "admin-de-prueba", True)).status_code == 303
        assert (
            await anonimo.post(
                "/admin/rotate",
                data={
                    "admin_password": "admin-de-prueba",
                    "new_password": "clave-nueva-larga",
                    "new_password_confirm": "clave-nueva-larga",
                },
            )
        ).status_code == 303


async def test_volver_a_pedir_clave(client, seeded_access_password):
    """ISC-19: el administrador puede reactivarlo, y vuelve a cerrarse."""
    await _login(client, "admin-de-prueba")
    await _toggle_login(client, "admin-de-prueba", False)
    assert (await _toggle_login(client, "admin-de-prueba", True)).status_code == 200

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as anonimo:
        assert (await anonimo.get("/")).status_code == 303


async def test_quitar_el_login_exige_la_clave_de_admin(client, seeded_access_password):
    await _login(client, "admin-de-prueba")
    assert (await _toggle_login(client, "clave-equivocada", False)).status_code == 403

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as anonimo:
        assert (await anonimo.get("/")).status_code == 303  # sigue cerrado


async def test_un_lector_no_puede_quitar_el_login(client, seeded_access_password):
    await _login(client, seeded_access_password)
    assert (await _toggle_login(client, "admin-de-prueba", False)).status_code == 403


# --- ISC-20 · claves públicas por defecto -----------------------------


async def test_las_claves_publicas_por_defecto_funcionan(client, auth_settings):
    """ISC-20: recién instalado, se entra con las claves del README."""
    from app.core.config import settings as app_settings
    from app.db import session as sm
    from app.services import auth as auth_service

    # arranque limpio: sin filas en app_settings, como tras instalar el paquete
    # con la plantilla .env tal cual sale de la caja
    app_settings.admin_password = "vxloginadmin"
    app_settings.initial_access_password = "vxlogindocente"
    async with sm.SessionLocal() as db:
        await auth_service.ensure_access_password(db)

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as profe:
        assert (await _login(profe, "vxlogindocente")).status_code == 303
        assert (await profe.get("/")).status_code == 200
        assert (await profe.get("/admin")).status_code == 403

    async with AsyncClient(
        transport=client._transport, base_url="http://test"
    ) as admin:
        assert (await _login(admin, "vxloginadmin")).status_code == 303
        assert (await admin.get("/admin")).status_code == 200
