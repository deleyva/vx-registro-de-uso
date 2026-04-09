"""Pytest fixtures.

We run against the real Postgres dev database. Each test starts with an
empty ``reports`` table — we ``TRUNCATE`` between tests rather than wrap
in a SAVEPOINT, because the asyncpg driver does not allow concurrent
operations on a single connection (which the SAVEPOINT pattern requires
when the FastAPI request handler also wants to commit).

The TRUNCATE approach is simple, deterministic, and fast enough for a
test suite of this size.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Make sure the test process points at the dev DB before importing the app.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/vx_control",
)

from app.db import session as session_module  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _override_engine_for_tests():
    """Replace the application engine + sessionmaker with test-scoped ones.

    This guarantees the app and the test fixtures share the exact same
    underlying connection pool — important so that the data the test
    inserts via the app's session is visible to the test's own asserts
    (and vice versa) and gets cleaned up between tests.
    """
    test_engine = create_async_engine(TEST_DB_URL, future=True, poolclass=NullPool)
    test_sessionmaker = session_module.async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    original_engine = session_module.engine
    original_sessionmaker = session_module.SessionLocal
    session_module.engine = test_engine
    session_module.SessionLocal = test_sessionmaker
    try:
        yield test_engine
    finally:
        await test_engine.dispose()
        session_module.engine = original_engine
        session_module.SessionLocal = original_sessionmaker


@pytest_asyncio.fixture(autouse=True)
async def _truncate_reports(_override_engine_for_tests) -> AsyncIterator[None]:
    """Empty the reports table before AND after every test."""
    engine = _override_engine_for_tests
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE TABLE "reports" RESTART IDENTITY CASCADE'))
    yield
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE TABLE "reports" RESTART IDENTITY CASCADE'))


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTPX async client wired against the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def report_payload() -> dict:
    return {
        "timestamp": "2026-04-09T07:59:26.463Z",
        "migrasfree_cid": "12345",
        "usuario_grafico": "MOCK_USER_DELEYVA",
        "empresa": "VITALINUX",
        "tipo_verificacion": "equipos_escritorio",
        "verificacion_equipos": {
            "pantalla": {"estado": "correcto", "problema": None, "obligatorio": True},
            "teclado": {"estado": "correcto", "problema": None, "obligatorio": True},
            "raton": {"estado": "defectuoso", "problema": "no responde", "obligatorio": True},
            "bateria": {"estado": "correcto", "problema": None, "obligatorio": False},
            "otros": {"estado": "correcto", "problema": None, "obligatorio": False},
        },
        "resumen": {
            "total_componentes": 5,
            "equipo_operativo": False,
            "requiere_atencion": True,
        },
    }
