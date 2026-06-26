# VX Control Center

Sistema de registro y monitoreo de equipos del IES Martina Bescós. Recibe reportes de verificación de un agente externo (MigrasFree) y los muestra en un panel web.

![alt text](image.png)

Clicando en cada icono de error, se ve qué es lo que falla.

## Stack

- **Runtime**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (async, Mapped API)
- **BD**: PostgreSQL 16
- **Migraciones**: Alembic
- **Plantillas**: Jinja2 + HTMX 2.0 + Tailwind v4
- **Gestor de paquetes**: uv
- **Tests**: pytest + httpx

Aplicación de un solo contenedor (FastAPI sirve tanto la API `/v1/report*` como el panel web). Diseñada para desplegarse en el host Docker existente, sustituyendo al antiguo monorepo Turborepo (NestJS + Next.js).

## Arquitectura

```
┌──────────────┐     POST /v1/report      ┌────────────┐
│  MigrasFree  │ ────────────────────────>│            │
│   (agente)   │                          │            │
└──────────────┘                          │  FastAPI   │    ┌──────────┐
                                          │   :3001    │ ──>│ Postgres │
┌──────────────┐     GET /                │            │    │  :5433   │
│  Navegador   │ ────────────────────────>│            │    └──────────┘
│  (panel web) │     HTMX                 │            │
└──────────────┘                          └────────────┘
```

Se mapean dos puertos del host al mismo puerto `3001` del contenedor:
- `3001:3001` — puerto canónico de la API, usado por MigrasFree y Swagger (`/api/docs`).
- `3000:3001` — alias mantenido para que los marcadores antiguos a `http://host:3000/` sigan funcionando.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/v1/report` | Recibir reporte de verificación (payload en snake_case, respuesta en camelCase) |
| GET | `/v1/report` | Listar reportes (filtros: `limit`, `from`, `to`, `onlyErrors`, `component`, `onlyOperativo`) |
| GET | `/v1/report/{id}` | Reporte individual por id |
| GET | `/` | Panel web (HTMX) |
| GET | `/reports/{id}/component/{component}` | Fragmento modal para detalle de componente |
| GET | `/health` | Comprobación de vida (ejecuta `SELECT 1`) |
| GET | `/api/docs` | Swagger UI |
| GET | `/api/openapi.json` | Esquema OpenAPI |

### Payload de POST `/v1/report`

```json
{
  "timestamp": "2026-04-09T07:59:26.463Z",
  "migasfree_cid": "12345",
  "usuario_grafico": "MOCK_USER",
  "empresa": "VITALINUX",                      // se acepta pero no se almacena
  "tipo_verificacion": "equipos_escritorio",   // se acepta pero no se almacena
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

Los campos desconocidos se aceptan silenciosamente (Pydantic `extra="ignore"`).

Formato de respuesta (camelCase):
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

## Variables de entorno

Ver `.env.example`.

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/vx_control` | Driver asíncrono para la app; `+asyncpg` se inserta automáticamente si falta. |
| `APP_PORT` | `3001` | Puerto de escucha de Uvicorn dentro del contenedor. |
| `ENVIRONMENT` | `development` | Etiqueta libre (`development`/`production`). |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Lista de orígenes permitidos separados por comas. |

## Desarrollo local

Requisitos previos: `uv` (>= 0.5), Docker.

```bash
# 1. instalar dependencias
uv sync

# 2. levantar un Postgres
docker run -d --name vx-postgres-dev \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=vx_control \
  -p 5433:5432 postgres:16-alpine

# 3. aplicar migraciones
uv run alembic upgrade head

# 4. arrancar servidor
uv run uvicorn app.main:app --reload --port 3001

# 5. ejecutar tests
uv run pytest -v

# 6. nueva migración (tras editar models/)
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head

# 7. recompilar Tailwind (tras editar templates/)
uv run tailwindcss -i src/app/static/css/tailwind.src.css -o src/app/static/css/tailwind.css --minify
```

## Docker (compose local)

Para levantar el stack en local **construyendo la imagen desde el código** (no desde GHCR),
con el `docker-compose.yml` de la raíz:

```bash
# build + arrancar
docker compose up --build -d

# logs
docker compose logs -f app

# parar
docker compose down

# parar + borrar volumen de BD
docker compose down -v
```

Al arrancar, el contenedor ejecuta `alembic upgrade head` antes de lanzar Uvicorn.

Hay **dos** ficheros compose, no los confundas:
- `docker-compose.yml` (raíz) — desarrollo/local, **construye** la imagen desde el `Dockerfile`.
- `deploy/docker-compose.prod.yml` — producción, **descarga** la imagen ya construida de GHCR.
  Es el que el `.deb` instala en el servidor (ver abajo).

## Despliegue en producción (.deb + systemd)

### Cómo encaja todo

```
  Desarrollo                 GitHub Actions                Servidor (host Docker)
 ─────────────              ────────────────              ────────────────────────
 just release X.Y.Z  ──┐
 (bump + tag + push)    │   el tag v* dispara el workflow:
                        └──> 1. build + push imagen → GHCR (:X.Y.Z y :latest)
                             2. build .deb con nfpm  ─┐  (en paralelo)
                             3. GitHub Release con el .deb adjunto
                                                      │
                          el .deb se descarga de la ──┘
                          Release y se instala:            sudo dpkg -i ...«.deb»
                                                            └─> systemd levanta el stack
                                                                que hace docker pull de GHCR
```

El `.deb` **no contiene la aplicación** — contiene el `docker-compose` de producción, el
`.env` y el unit de systemd. La aplicación viaja como imagen Docker en GHCR. Es el
equivalente de servidor al autoarranque de `vx-login-app`: en lugar de un `.desktop` en
`/etc/xdg/autostart/`, se instala un unit en `/etc/systemd/system/` que arranca el stack
al iniciar el host.

### Visibilidad de la imagen de GHCR

Como el repositorio es **público**, el paquete de contenedor que publica GitHub Actions
hereda esa visibilidad y es **público** automáticamente — el servidor puede hacer
`docker pull` sin autenticarse. No hay paso manual.

Si el repositorio pasara a privado, el paquete quedaría privado y habría que: o bien hacerlo
público en
`https://github.com/users/deleyva/packages/container/vx-registro-de-uso/settings`
(*Danger Zone* → *Change visibility*), o bien hacer `docker login ghcr.io` en el host con un
PAT con scope `read:packages`.

### Requisitos del host

Docker + el plugin `docker compose` v2. El `.deb` **no** los declara como dependencia
(los hosts suelen usar Docker CE del repo de Docker); el `postinst` comprueba que están y
avisa si faltan, pero no falla la instalación.

### Instalar / actualizar en el servidor

```bash
# descargar el .deb desde la GitHub Release y:
sudo dpkg -i vx-registro-de-uso_<version>_amd64.deb

# primera instalación: ajustar credenciales (Postgres, CORS, puerto, VX_IMAGE…)
sudo nano /opt/vx-registro/.env
sudo systemctl restart vx-registro
```

En **upgrades** el `.env` ya editado **se conserva** (está marcado como fichero de
configuración). Para actualizar a una versión nueva basta con `dpkg -i` del nuevo `.deb`, o
`sudo systemctl restart vx-registro` si solo cambió la imagen `:latest`.

### Qué coloca el `.deb`

| Archivo del repo | Destino en el host |
|---|---|
| `deploy/docker-compose.prod.yml` | `/opt/vx-registro/docker-compose.yml` |
| `deploy/vx-registro.env.example` | `/opt/vx-registro/.env.example` y `/opt/vx-registro/.env` (este último no se sobrescribe en upgrades) |
| `deploy/vx-registro.service` | `/etc/systemd/system/vx-registro.service` |

El `postinst` ejecuta `systemctl daemon-reload`, `systemctl enable vx-registro` y arranca el
servicio si Docker está disponible.

### Operación

```bash
sudo systemctl status vx-registro
docker compose -f /opt/vx-registro/docker-compose.yml logs -f
sudo systemctl restart vx-registro     # re-pull de la imagen + reinicio
```

Al desinstalar (`sudo dpkg -r vx-registro-de-uso`) se para y deshabilita el servicio; el
`.env` y el volumen de datos de Postgres se conservan a propósito.

## Publicar una nueva versión (release)

Las releases las genera GitHub Actions (`.github/workflows/release.yml`) al hacer push de un
tag `v*`. El workflow construye y publica la imagen Docker en GHCR (`:version` y `:latest`),
construye el `.deb` con [nfpm](https://nfpm.goreleaser.com/) y crea una GitHub Release con el
`.deb` adjunto.

```bash
just version         # ver versión actual
just release 2.1.0   # bump pyproject.toml + commit + tag + push → dispara el workflow
```

La versión vive en un único sitio: el campo `version` de `pyproject.toml`. El tag (`v2.1.0`)
es lo que el workflow usa para etiquetar la imagen y nombrar la Release.

## Estructura del proyecto

```
.
├── src/app/
│   ├── main.py              # App FastAPI, routers, CORS, archivos estáticos
│   ├── core/
│   │   ├── config.py        # pydantic-settings
│   │   ├── ids.py           # generador cuid2
│   │   └── logging.py
│   ├── db/
│   │   ├── base.py          # DeclarativeBase
│   │   └── session.py       # async_engine, dependencia get_db
│   ├── models/
│   │   └── report.py        # Modelo ORM Report (nombres de columna en camelCase)
│   ├── schemas/
│   │   ├── camel.py         # Base CamelModel (alias_generator)
│   │   └── reports.py       # CreateReportRequest + ReportResponse
│   ├── services/
│   │   └── reports.py       # create, find_all (filtros en memoria), find_one
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   ├── reports_v1.py    # POST/GET /v1/report, GET /v1/report/{id}
│   │   └── web.py           # GET / (panel HTMX), GET /reports/{id}/component/{c}
│   ├── templates/           # Jinja2
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/
│   │       ├── reports_table.html
│   │       └── report_detail_modal.html
│   └── static/
│       ├── css/
│       │   ├── tailwind.src.css
│       │   └── tailwind.css     # compilado, commiteado
│       └── vendor/
│           └── htmx.min.js
├── migrations/               # Alembic
│   └── versions/
├── tests/
│   ├── conftest.py           # aislamiento TRUNCATE-por-test, motor NullPool
│   ├── test_health.py
│   ├── test_schemas_reports.py
│   └── test_reports_v1.py    # suite de paridad con NestJS
├── Dockerfile
├── docker-entrypoint.sh
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── .env.example
```
