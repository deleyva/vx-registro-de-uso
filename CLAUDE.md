# CLAUDE.md — vx-registro-de-uso

Guidance for Claude Code when working on this repository.

## What this project is

VX Control Center — a single Python app (FastAPI + SQLAlchemy async + Jinja2/HTMX) that receives verification reports from an external agent called **MigrasFree** and shows them on a web panel. It replaced an earlier NestJS + Next.js Turborepo monorepo on 2026-04-09.

## Critical parity constraints

**El cliente que envía informes es `~/vx-login-app` (Tauri + Rust), no un agente de
terceros** — CORRECCIÓN del 2026-09-04. Este fichero afirmaba que era externo e
intocable; es falso, es del mismo autor y tiene su propio pipeline de release. Lo que
sí es cierto es la consecuencia práctica: está desplegado por `.deb` en cada equipo
del centro, así que **cambiar su contrato obliga a redesplegar todos los equipos**. Por
eso el contrato `/v1/report*` se trata como congelado y `POST /v1/report` sigue sin
autenticar. Ese cliente **solo hace POST**: no lee nada por HTTP (verificado por grep
sobre `script.js` y `src-tauri/src/main.rs`), y por eso los GET sí se pudieron cerrar.

El contrato `/v1/report*` debe seguir siendo byte-for-byte compatible con la API NestJS
antigua:

- Routes: `POST /v1/report`, `GET /v1/report`, `GET /v1/report/{id}`
- Request body: snake_case (`timestamp`, `migasfree_cid`, `usuario_grafico`, `verificacion_equipos`, `resumen`, opcional `etiquetas`)
- Response body: camelCase (`id`, `timestamp`, `migasfreeCid`, `usuarioGrafico`, `etiquetas`, `verificacionEquipos`, `resumen`, `createdAt`)
- Status codes: `201` on create, `200` on list/get, `404` on missing id
- **`empresa` y `tipo_verificacion` se eliminaron del esquema el 2026-09-05.** Nunca se almacenaron, así que declararlos solo sugería que hacían algo. Los clientes que aún los envíen siguen recibiendo 201, porque `extra="ignore"` descarta lo no declarado sin error. No los vuelvas a añadir sin una columna detrás.
- **Unknown fields in POST body are silently ignored** (`model_config = {"extra": "ignore"}` on `CreateReportRequest`). This is defensive against future MigrasFree changes.
- **Query params `onlyErrors` and `onlyOperativo` are parsed via `_parse_tri_bool`**, which only treats the literal strings `"true"`/`"false"` as bools and returns `None` otherwise. Do NOT refactor to FastAPI's automatic `bool` coercion — it accepts `"1"`, `"yes"`, etc. and diverges from NestJS.

## Autenticación

Instalada el 2026-09-04. El diseño y el porqué están en el README (sección
«Autenticación») y las afirmaciones verificadas en `ISA.md`. Lo que hay que saber para
no romperlo:

- **`core/authguard.py` decide qué pasa sin credencial**, y la lista es corta a
  propósito: `POST /v1/report`, `/health`, `/login`, `/logout`, `/favicon.ico` y
  `/static/*`. Todo lo demás exige sesión, incluidos los GET de `/v1/report*` y la
  documentación OpenAPI. **No añadas rutas a esa lista sin pensarlo**: el incidente que
  motivó todo esto es que los GET devolvían el histórico completo sin credencial.
- **Tres llaves**, no dos: clave de acceso y clave de administración en `app_settings`
  (hasheadas), más la llave maestra en `ADMIN_PASSWORD`. La maestra solo se lee, nunca
  se escribe desde código. Esa asimetría es el invariante: garantiza que nadie pueda
  dejar fuera a quien administra el servidor desde la interfaz. No la rompas añadiendo
  una ruta que la modifique.
- **Las claves de fábrica son públicas y están en el repositorio a propósito**
  (`vxloginadmin` / `vxlogindocente`, en `core/config.py`). Decisión explícita del
  autor el 2026-09-04: el despliegue es la red local del centro y la prioridad es que
  funcione al instalarlo. No las sustituyas por generación aleatoria. `SESSION_SECRET`
  es la excepción y sí se genera por servidor: no es una clave que nadie teclee, y
  publicarla permitiría falsificar sesiones sin conocer ninguna clave.
- **El administrador puede quitar el login** (`auth_required` en `app_settings`,
  conmutado desde `/admin`). Eso abre el panel y los GET de la API, pero **nunca**
  `/admin`: `_is_admin_route()` en el guardia deja esas rutas fuera del atajo. Si tocas
  esa función, comprueba que sigue siendo la única forma de volver a activar el login.
- **El sello de sesión no es decorativo.** Cada sesión guarda de qué llave salió y la
  marca temporal de esa llave; el guardia la compara en cada petición contra el estado
  actual. Es lo que hace que rotar una clave expulse a quien entró con la anterior. Se
  consulta la fila en cada petición protegida, sin caché, y es deliberado: una caché con
  TTL retrasaría la revocación, que es justo lo que la rotación debe garantizar.
- **El hashing es `hashlib.scrypt`**, no passlib ni bcrypt. Fue una decisión para no
  añadir dependencias: la única que suma la autenticación es `itsdangerous`, que exige
  `SessionMiddleware`.
- **El orden de `add_middleware` en `main.py` es carga útil.** Starlette ejecuta el
  último añadido como el más externo. El orden actual (guardia → sesión → CORS) es el
  único que resuelve el preflight antes de nada, descifra la cookie antes de mirar el
  rol, y decide antes de llegar a la ruta.
- **La suite corre con `AUTH_ENABLED=false`** (fijado en `conftest.py`) salvo
  `tests/test_auth.py`, que lo activa por fixture. Así los 16 tests de paridad con
  NestJS siguen siendo exactamente los mismos que antes.

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
- **Los secretos del panel los genera `deploy/scripts/postinst.sh` en el host, nunca la
  CI.** El `.deb` va adjunto a una Release pública: cualquier valor que la CI escribiese
  en la plantilla del `.env` sería descargable e idéntico en todas las instalaciones. La
  función `ensure_var` es idempotente a propósito — nunca pisa una variable que ya tenga
  valor — y `POSTGRES_PASSWORD` queda deliberadamente fuera, porque cambiarla en un host
  con el volumen ya inicializado deja la aplicación sin conexión.
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

## Estado del proyecto

`ISA.md` en la raíz es el registro de qué afirma este proyecto y con qué evidencia se
cerró cada afirmación. Al añadir funcionalidad, añade criterios ahí en vez de abrir
documentos paralelos, y rellena su sección `## Verification` con la evidencia real
(salida de comando, sonda HTTP, captura), nunca con «debería funcionar».

## History

- **2026-09-04** (tarde): claves de fábrica públicas, interruptor para quitar el login, y campo `etiquetas` en los informes — el cliente Tauri las obtiene con `vx-migasfree-tags -g`, sin sudo. `etiquetas` es una ADICIÓN al contrato `/v1/report`, aprobada explícitamente; los tests de paridad se actualizaron para incluirla.
- **2026-09-04**: Autenticación de sesión con tres llaves (acceso, administración delegada, llave maestra). Se cierran los GET de `/v1/report*`; la ingesta sigue abierta. Se añade `ISA.md`. Se quitan de `config.py` y `docker-compose.yml` unas IP privadas escritas en claro, que **siguen en el historial de git** porque el repo es público.
- **2026-04-09**: Full rewrite from TypeScript (NestJS 10 + Next.js 15 + Prisma 6) to Python (FastAPI + SQLAlchemy 2.0 + Jinja2/HTMX). Old history and code are recoverable via git tag `pre-python-rewrite`.
