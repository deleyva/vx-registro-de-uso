# VX Control Center

Sistema de registro y monitoreo de equipos del IES Martina Bescós. Recibe reportes de verificación de un agente externo (MigrasFree) y los muestra en un panel web.

## Stack

- **Runtime**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (async, Mapped API)
- **DB**: PostgreSQL 16
- **Migrations**: Alembic
- **Templates**: Jinja2 + HTMX 2.0 + Tailwind v4
- **Package manager**: uv
- **Tests**: pytest + httpx

Single-container app (FastAPI serves both the `/v1/report*` API and the web panel). Designed to be deployed on the existing Docker host replacing the old Turborepo (NestJS + Next.js) monorepo.

## Architecture

```
┌──────────────┐     POST /v1/report      ┌────────────┐
│  MigrasFree  │ ────────────────────────>│            │
│   (agent)    │                          │            │
└──────────────┘                          │  FastAPI   │    ┌──────────┐
                                          │   :3001    │ ──>│ Postgres │
┌──────────────┐     GET /                │            │    │  :5433   │
│   Browser    │ ────────────────────────>│            │    └──────────┘
│  (panel web) │     HTMX                 │            │
└──────────────┘                          └────────────┘
```

Two host ports are mapped to the same container port `3001`:
- `3001:3001` — canonical API port, used by MigrasFree and Swagger (`/api/docs`).
- `3000:3001` — alias kept so old bookmarks to `http://host:3000/` still work.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/v1/report` | Receive verification report (snake_case payload, returns camelCase) |
| GET | `/v1/report` | List reports (filters: `limit`, `from`, `to`, `onlyErrors`, `component`, `onlyOperativo`) |
| GET | `/v1/report/{id}` | Single report by id |
| GET | `/` | Web panel (HTMX) |
| GET | `/reports/{id}/component/{component}` | Modal fragment for component detail |
| GET | `/health` | Liveness check (runs `SELECT 1`) |
| GET | `/api/docs` | Swagger UI |
| GET | `/api/openapi.json` | OpenAPI schema |

### POST `/v1/report` payload

```json
{
  "timestamp": "2026-04-09T07:59:26.463Z",
  "migasfree_cid": "12345",
  "usuario_grafico": "MOCK_USER",
  "empresa": "VITALINUX",                      // accepted silently, not stored
  "tipo_verificacion": "equipos_escritorio",   // accepted silently, not stored
  "verificacion_equipos": {
    "pantalla": { "estado": "correcto", "problema": null, "obligatorio": true },
    "raton":    { "estado": "defectuoso", "problema": "no responde", "obligatorio": true }
  },
  "resumen": {
    "total_componentes": 5,
    "equipo_operativo": false,
    "requiere_atencion": true
  }
}
```

Unknown fields are accepted silently (Pydantic `extra="ignore"`).

Response shape (camelCase):
```json
{
  "id": "kpv1jqy6b2...",
  "timestamp": "2026-04-09T07:59:26.463000Z",
  "migasfreeCid": "12345",
  "usuarioGrafico": "MOCK_USER",
  "verificacionEquipos": { ... },
  "resumen": { ... },
  "createdAt": "2026-04-09T13:14:22.123456Z"
}
```

## Environment variables

See `.env.example`.

| Var | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/vx_control` | Async driver for the app; `+asyncpg` is inserted automatically if missing. |
| `APP_PORT` | `3001` | Uvicorn bind port inside the container. |
| `ENVIRONMENT` | `development` | Free-form tag (`development`/`production`). |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001,http://100.99.123.84:3000` | Comma-separated list of allowed origins. |

## Local development

Prereqs: `uv` (>= 0.5), Docker.

```bash
# 1. install deps
uv sync

# 2. start a Postgres
docker run -d --name vx-postgres-dev \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=vx_control \
  -p 5433:5432 postgres:16-alpine

# 3. apply migrations
uv run alembic upgrade head

# 4. run server
uv run uvicorn app.main:app --reload --port 3001

# 5. run tests
uv run pytest -v

# 6. new migration (after editing models/)
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head

# 7. rebuild Tailwind (after editing templates/)
uv run tailwindcss -i src/app/static/css/tailwind.src.css -o src/app/static/css/tailwind.css --minify
```

## Docker (production)

```bash
# build + start
docker compose up --build -d

# logs
docker compose logs -f app

# stop
docker compose down

# stop + wipe DB volume
docker compose down -v
```

On startup the container runs `alembic upgrade head` before launching Uvicorn.

## Despliegue en servidor (.deb + systemd)

El paquete `.deb` instala el stack como un servicio systemd que **arranca solo al iniciar
el host**. Es el equivalente de servidor al autoarranque de `vx-login-app`: en lugar de un
`.desktop` en `/etc/xdg/autostart/`, aquí se instala un unit en `/etc/systemd/system/`.

Qué coloca el `.deb` al instalarse:

| Archivo | Destino |
|---|---|
| `deploy/docker-compose.prod.yml` | `/opt/vx-registro/docker-compose.yml` |
| `deploy/vx-registro.env.example` | `/opt/vx-registro/.env` (config, no se sobrescribe en upgrades) |
| `deploy/vx-registro.service` | `/etc/systemd/system/vx-registro.service` |

El `postinst` ejecuta `systemctl daemon-reload`, `systemctl enable vx-registro` y arranca
el servicio (si Docker está disponible). El stack de producción usa la imagen de GHCR
(`ghcr.io/deleyva/vx-registro-de-uso`), no construye en local.

**Requisitos del host:** Docker + el plugin `docker compose` v2.

```bash
# instalar
sudo dpkg -i vx-registro-de-uso_<version>_amd64.deb

# ajustar credenciales (Postgres, CORS, puerto…)
sudo nano /opt/vx-registro/.env
sudo systemctl restart vx-registro

# operación
sudo systemctl status vx-registro
docker compose -f /opt/vx-registro/docker-compose.yml logs -f
```

Al desinstalar (`sudo dpkg -r vx-registro-de-uso`) se para y deshabilita el servicio; el
`.env` y el volumen de datos de Postgres se conservan a propósito.

## Release

Las releases las genera GitHub Actions (`.github/workflows/release.yml`) al hacer push de
un tag `v*`. El workflow construye y publica la imagen Docker en GHCR (`:version` y
`:latest`), construye el `.deb` con [nfpm](https://nfpm.goreleaser.com/) y crea una GitHub
Release con el `.deb` adjunto.

```bash
just release 2.1.0   # bump pyproject.toml + commit + tag + push → dispara el workflow
just version         # ver versión actual
```

La versión vive en un único sitio: el campo `version` de `pyproject.toml`.

## Project layout

```
.
├── src/app/
│   ├── main.py              # FastAPI app, routers, CORS, static files
│   ├── core/
│   │   ├── config.py        # pydantic-settings
│   │   ├── ids.py           # cuid2 generator
│   │   └── logging.py
│   ├── db/
│   │   ├── base.py          # DeclarativeBase
│   │   └── session.py       # async_engine, get_db dependency
│   ├── models/
│   │   └── report.py        # Report ORM model (camelCase column names)
│   ├── schemas/
│   │   ├── camel.py         # CamelModel base (alias_generator)
│   │   └── reports.py       # CreateReportRequest + ReportResponse
│   ├── services/
│   │   └── reports.py       # create, find_all (in-memory filters), find_one
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   ├── reports_v1.py    # POST/GET /v1/report, GET /v1/report/{id}
│   │   └── web.py           # GET / (HTMX panel), GET /reports/{id}/component/{c}
│   ├── templates/           # Jinja2
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/
│   │       ├── reports_table.html
│   │       └── report_detail_modal.html
│   └── static/
│       ├── css/
│       │   ├── tailwind.src.css
│       │   └── tailwind.css     # compiled, committed
│       └── vendor/
│           └── htmx.min.js
├── migrations/               # Alembic
│   └── versions/
├── tests/
│   ├── conftest.py           # TRUNCATE-per-test isolation, NullPool engine
│   ├── test_health.py
│   ├── test_schemas_reports.py
│   └── test_reports_v1.py    # parity suite with NestJS
├── Dockerfile
├── docker-entrypoint.sh
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── .env.example
```
