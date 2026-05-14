# CLAUDE.md — vx-registro-de-uso

Guidance for Claude Code when working on this repository.

## What this project is

VX Control Center — a single Python app (FastAPI + SQLAlchemy async + Jinja2/HTMX) that receives verification reports from an external agent called **MigrasFree** and shows them on a web panel. It replaced an earlier NestJS + Next.js Turborepo monorepo on 2026-04-09.

## Critical parity constraints

**The MigrasFree agent is external and cannot be changed.** The `/v1/report*` contract must stay byte-for-byte compatible with the old NestJS API:

- Routes: `POST /v1/report`, `GET /v1/report`, `GET /v1/report/{id}`
- Request body: snake_case (`timestamp`, `migasfree_cid`, `usuario_grafico`, `verificacion_equipos`, `resumen`, optional `empresa`, `tipo_verificacion`)
- Response body: camelCase (`id`, `timestamp`, `migasfreeCid`, `usuarioGrafico`, `verificacionEquipos`, `resumen`, `createdAt`)
- Status codes: `201` on create, `200` on list/get, `404` on missing id
- **`empresa` and `tipo_verificacion` are intentionally accepted and then dropped.** Do NOT add columns to store them. This matches the old NestJS behavior exactly. If this ever needs to change, update the `Report` model, add a migration, and update the response schema in lockstep.
- **Unknown fields in POST body are silently ignored** (`model_config = {"extra": "ignore"}` on `CreateReportRequest`). This is defensive against future MigrasFree changes.
- **Query params `onlyErrors` and `onlyOperativo` are parsed via `_parse_tri_bool`**, which only treats the literal strings `"true"`/`"false"` as bools and returns `None` otherwise. Do NOT refactor to FastAPI's automatic `bool` coercion — it accepts `"1"`, `"yes"`, etc. and diverges from NestJS.

## Important conventions

### Database column naming

The database uses **literal camelCase** column names (inherited from Prisma) while Python attributes use snake_case. Always pass the column name as the first positional argument of `mapped_column`:

```python
migasfree_cid: Mapped[str] = mapped_column("migasfreeCid", String, nullable=False)
```

Alembic autogenerate respects these overrides. After editing `models/report.py`, always hand-review the generated migration to confirm it uses `migasfreeCid`, `usuarioGrafico`, `verificacionEquipos`, `createdAt` — not the snake_case forms.

### JSONB, not JSON

`verificacionEquipos` and `resumen` use `sqlalchemy.dialects.postgresql.JSONB`, not generic `JSON`. Keep it that way — we rely on JSONB for future indexing.

### Filtering is in memory, not SQL

`services/reports.py` `find_all()` intentionally does `ORDER BY createdAt DESC + LIMIT` at the SQL level and then filters `from`/`to`/`only_errors`/`component`/`only_operativo` in Python. This is a known bug-for-bug parity with the old NestJS service — a filter can return 0 rows even when matching rows exist beyond the `limit` window. **Do not "fix" this by moving filters into SQL** without explicit approval — the change would diverge from the old API's observed behavior. Tracked as tech debt.

### Config normalization

`Settings.database_url` accepts any Postgres URL; `Settings.async_database_url` and `Settings.sync_database_url` normalize to `+asyncpg` (app) and `+psycopg2` (Alembic) automatically. Always use these properties, never `database_url` directly.

### CORS origins

Always comes from `CORS_ORIGINS` env var as a comma-separated string. The `Annotated[list[str], NoDecode]` annotation on the field is load-bearing: it prevents pydantic-settings from trying to JSON-decode the value, so the `field_validator(..., mode="before")` can parse the CSV format.

### Test isolation

`tests/conftest.py` uses a per-test `TRUNCATE TABLE reports RESTART IDENTITY CASCADE` autouse fixture with a `NullPool` async engine. The asyncpg driver can't handle concurrent operations on a single connection, so the standard SAVEPOINT-rollback pattern doesn't work with FastAPI handlers that call `await session.commit()`. TRUNCATE is the pragmatic alternative. Tests run in ~80ms each.

### Tailwind v4, not v3

`pytailwindcss` ships Tailwind v4 only. v4 is CSS-first — there is no `tailwind.config.js` anymore (the file in the repo is a docs marker). Configuration lives in `src/app/static/css/tailwind.src.css` via `@import "tailwindcss";` and `@source "../../templates/**/*.html";`. After editing templates, recompile:

```bash
uv run tailwindcss -i src/app/static/css/tailwind.src.css -o src/app/static/css/tailwind.css --minify
```

**Always commit the compiled `tailwind.css`** so the Docker build doesn't depend on the runtime binary.

### cuid2 for IDs

IDs are generated via `app.core.ids.create_id()` which uses `cuid2` (not UUID). Column type is `String`, not `UUID`. This preserves parity with the old Prisma `cuid()` default.

## Commands

```bash
# deps
uv sync
uv sync --dev

# run server (dev)
uv run uvicorn app.main:app --reload --port 3001

# run server (explicit venv)
uv run uvicorn --host 0.0.0.0 --port 3001 app.main:app

# tests
uv run pytest                      # quiet
uv run pytest -v                   # verbose
uv run pytest tests/test_reports_v1.py::test_post_valid_payload_returns_201_with_camel_keys -v

# lint
uv run ruff check .
uv run ruff check . --fix

# migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe change"
uv run alembic history
uv run alembic downgrade -1

# tailwind recompile
uv run tailwindcss -i src/app/static/css/tailwind.src.css -o src/app/static/css/tailwind.css --minify

# docker
docker compose up --build -d
docker compose logs -f app
docker compose down
docker compose down -v             # also wipes DB volume

# dev postgres (when not running compose)
docker run -d --name vx-postgres-dev \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=vx_control \
  -p 5433:5432 postgres:16-alpine
docker rm -f vx-postgres-dev
```

## How to add an endpoint

1. If new data: update `models/report.py` (or new model in `models/`), create a migration with `uv run alembic revision --autogenerate -m "..."`, hand-review it, apply with `alembic upgrade head`.
2. Add request/response schemas in `schemas/` inheriting from `CamelModel` for responses.
3. Add business logic in `services/`.
4. Add the router in `routers/` and register it in `main.py`.
5. Write tests in `tests/` — at minimum a happy path + one error case + a response shape snapshot.
6. Run `uv run pytest -v` before committing.

## How to add a migration

```bash
# after editing models/report.py
uv run alembic revision --autogenerate -m "add foo column"
# OPEN the generated file under migrations/versions/ and verify:
#   - new columns use literal camelCase names (not snake_case)
#   - no accidental table drops
#   - both upgrade() and downgrade() look correct
uv run alembic upgrade head
```

## Deployment & releases

Production runs as a Docker stack on a server host, started on boot by a **systemd** unit —
NOT on each workstation. See the README "Despliegue en producción" section for the full flow.

- **Two compose files**: `docker-compose.yml` (root, dev — `build:` from source) vs
  `deploy/docker-compose.prod.yml` (prod — `image:` from GHCR). Keep the `postgres` service
  in sync between them by hand.
- **Release = git tag `v*`**. `just release X.Y.Z` bumps `pyproject.toml` (the single version
  source), commits, tags, and pushes. The tag triggers `.github/workflows/release.yml`:
  parallel jobs build+push the GHCR image and build the `.deb` via `deploy/nfpm.yaml`, then a
  `release` job publishes a GitHub Release with the `.deb`.
- **The `.deb` ships infra, not the app** — compose file + `.env` + systemd unit, landing in
  `/opt/vx-registro/` and `/etc/systemd/system/`. The app itself is the GHCR image the unit
  pulls. Maintainer scripts are in `deploy/scripts/`.
- **GHCR image visibility**: the repo is public, so the Actions-published container package
  inherits public visibility automatically — no manual step. If the repo ever goes private,
  the package must be made public (or the host needs `docker login ghcr.io`).
- When changing the install layout, the path `/opt/vx-registro/` is hardcoded across
  `deploy/nfpm.yaml`, `deploy/vx-registro.service`, `deploy/scripts/*`, and the README — it's
  a packaging contract, change all of them together.

## Latent work not yet ported

The old NestJS monorepo had these modules in source that were **not mounted in `app.module.ts`** and therefore not exposed in production. They are **intentionally not ported** to this Python rewrite:

- `apps/api/src/devices/*` — device registry, hostname/ipAddress/macAddress tracking
- `apps/api/src/usage/*` — usage logs (cpu/ram/disk usage)
- `apps/api/src/stats/*` — aggregation endpoints

If any of these become needed:
1. Read the original TypeScript in the tag `pre-python-rewrite` (`git show pre-python-rewrite:apps/api/src/devices/devices.service.ts`)
2. Port models first (they were in `packages/database/prisma/schema.prisma` as `Device`, `UsageLog`, `User`)
3. Add migrations, services, routers, tests (see "How to add an endpoint" above)

## History

- **2026-04-09**: Full rewrite from TypeScript (NestJS 10 + Next.js 15 + Prisma 6) to Python (FastAPI + SQLAlchemy 2.0 + Jinja2/HTMX). Old history and code are recoverable via git tag `pre-python-rewrite`.
