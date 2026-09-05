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
| GET/POST | `/login` | Pantalla de acceso |
| GET/POST | `/logout` | Cerrar sesión |
| GET | `/admin` | Panel de administración (solo administración) |
| POST | `/admin/rotate` | Cambia la clave de acceso del profesorado |
| POST | `/admin/admin-password` | Crea o cambia la clave de administración |
| POST | `/admin/login-toggle` | Quita o vuelve a pedir el login del panel |

Todo lo anterior exige sesión **salvo** `POST /v1/report`, `/health`, `/login`,
`/logout`, `/favicon.ico` y `/static/*`. El administrador puede quitar el login, y
entonces el panel y los GET quedan abiertos, pero `/admin` no. Ver
[Acceso al panel](#acceso-al-panel).

### Payload de POST `/v1/report`

```json
{
  "timestamp": "2026-04-09T07:59:26.463Z",
  "migasfree_cid": "12345",
  "usuario_grafico": "MOCK_USER",
  "etiquetas": "aula-musica planta-1",     // opcional; los clientes antiguos no lo envían
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

Los campos desconocidos se aceptan silenciosamente (Pydantic `extra="ignore"`), así
que un equipo con una versión antigua del cliente sigue reportando aunque mande campos
que ya no existen. Es lo que pasa con `empresa` y `tipo_verificacion`: nunca se
almacenaron, y desde septiembre de 2026 ni siquiera se declaran.

**`etiquetas`** son las etiquetas de migasfree del equipo. Las obtiene el cliente
`vx-login-app` con `vx-migasfree-tags -g` (sin sudo, igual que el CID) y las envía como
una cadena, separadas por espacios. El panel las muestra en su propia columna. Es un
campo **opcional**: los equipos con una versión anterior del cliente no lo mandan y
siguen reportando igual; en esos informes la columna sale vacía. Si el comando falla en
un equipo, el informe se envía de todas formas con las etiquetas vacías.

Formato de respuesta (camelCase):
```json
{
  "id": "kpv1jqy6b2...",
  "timestamp": "2026-04-09T07:59:26.463000Z",
  "migasfreeCid": "12345",
  "usuarioGrafico": "MOCK_USER",
  "etiquetas": "aula-musica planta-1",
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
| `AUTH_ENABLED` | `true` | Ponlo a `false` solo en desarrollo: deja panel y API de lectura abiertos. |
| `ADMIN_PASSWORD` | `vxloginadmin` | Llave maestra. Vale siempre y solo se cambia aquí. |
| `INITIAL_ACCESS_PASSWORD` | `vxlogindocente` | Clave del profesorado en el primer arranque. Después manda la guardada en base de datos. |
| `SESSION_SECRET` | *(vacío)* | Firma de la cookie. La genera el instalador, única por servidor. Vacía => las sesiones mueren en cada reinicio. |
| `SESSION_MAX_AGE` | `43200` | Duración de la sesión en segundos (12 h). |
| `COOKIE_SECURE` | `false` | Ponlo a `true` cuando el panel vaya por HTTPS. |
| `INGEST_TOKEN` | *(vacío)* | Si se rellena, `POST /v1/report` exige la cabecera `X-VX-Token`. |

## Acceso al panel

**Claves de fábrica** (públicas a propósito: esto va en la red local del centro y
tiene que funcionar nada más instalarlo):

| | Clave | Para qué |
|---|---|---|
| Profesorado | `vxlogindocente` | ver los informes |
| Administración | `vxloginadmin` | ver los informes **y** cambiar ajustes |

![Pantalla de acceso](docs/img/login.jpg)

Con la clave de profesorado solo se ve la tabla. Con la de administración aparece
además el enlace «Administración».

![Panel](docs/img/panel-admin.jpg)

### Lo que puede hacer el administrador

Todo desde `/admin`, y **solo él**: cada formulario vuelve a pedir la clave de
administración, así que un ordenador con la sesión abierta olvidada no sirve para
cambiar nada.

![Administración](docs/img/admin-crear-clave.jpg)

1. **Cambiar la clave del profesorado.** Al cambiarla, quien estuviera dentro con la
   anterior queda fuera.
2. **Cambiar la clave de administración.** La nueva se guarda en la base de datos y
   se cambia desde el navegador, sin tocar el servidor.
3. **Quitar el login.** El panel queda abierto: cualquiera que llegue a la dirección
   ve los informes sin teclear nada. **`/admin` sigue pidiendo la clave**, que es
   cómo se vuelve a activar.

![Login quitado](docs/img/admin-login-quitado.jpg)

Si un profesor escribe `/admin` a mano:

![Sin permiso](docs/img/sin-permiso.jpg)

### La llave maestra

`ADMIN_PASSWORD` en el `.env` del servidor vale siempre, aunque se cambie la de
administración desde el navegador. Solo se cambia editando ese fichero y
reiniciando, así que nadie puede dejarte fuera desde la interfaz.

### Lo que NO pide clave

`POST /v1/report` sigue abierto: los equipos del centro tienen el cliente instalado
por `.deb` y exigirles credencial los dejaría sin reportar. También `/health` y
`/static/*`.

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

#### Claves tras instalar

El `.env` queda con las claves de fábrica (`vxloginadmin` / `vxlogindocente`) y en
permisos `600 root:root`. Entra en el panel con la de administración y cámbialas desde
`/admin`.

`SESSION_SECRET` sí lo genera `postinst.sh`, único de esa máquina. Ese no es público ni
hay que teclearlo: es la firma de las cookies, y publicarlo permitiría falsificar
sesiones de administrador sin conocer ninguna clave.

El comportamiento al actualizar, comprobado en un contenedor Debian sobre los cuatro
casos que se dan en la práctica:

| Situación del `.env` | Qué hace |
|---|---|
| No existían las variables (`.env` de una versión anterior) | las añade al final, con valores generados |
| Ya tenían valor | **no las toca** |
| Declaradas pero vacías (`ADMIN_PASSWORD=`) | rellena la línea, sin duplicarla |
| Sin salto de línea final | añade el salto antes, para no pegar la variable a la última línea |

`POSTGRES_PASSWORD` **no se genera nunca**, ni siquiera vacía: cambiarla en un servidor
con el volumen ya inicializado no cambia la contraseña real de Postgres, y dejaría a la
aplicación sin poder conectar. Esa sigue siendo manual.

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
│   │   ├── authguard.py     # middleware de sesión: qué rutas son públicas
│   │   ├── config.py        # pydantic-settings
│   │   ├── ids.py           # generador cuid2
│   │   ├── logging.py
│   │   └── security.py      # hashing scrypt (biblioteca estándar)
│   ├── db/
│   │   ├── base.py          # DeclarativeBase
│   │   └── session.py       # async_engine, dependencia get_db
│   ├── models/
│   │   ├── app_setting.py   # claves de acceso y administración, hasheadas
│   │   └── report.py        # Modelo ORM Report (nombres de columna en camelCase)
│   ├── schemas/
│   │   ├── camel.py         # Base CamelModel (alias_generator)
│   │   └── reports.py       # CreateReportRequest + ReportResponse
│   ├── services/
│   │   ├── auth.py          # verificación, rotación y sellos de sesión
│   │   └── reports.py       # create, find_all (filtros en memoria), find_one
│   ├── routers/
│   │   ├── auth.py          # /login, /logout, /admin
│   │   ├── health.py        # GET /health
│   │   ├── reports_v1.py    # POST/GET /v1/report, GET /v1/report/{id}
│   │   └── web.py           # GET / (panel HTMX), GET /reports/{id}/component/{c}
│   ├── templates/           # Jinja2
│   │   ├── admin.html
│   │   ├── base.html
│   │   ├── forbidden.html
│   │   ├── index.html
│   │   ├── login.html
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
├── docs/img/                 # capturas usadas en este README
├── ISA.md                    # estado del proyecto: qué se afirma y con qué evidencia
├── tests/
│   ├── conftest.py           # aislamiento TRUNCATE-por-test, motor NullPool
│   ├── test_auth.py          # sesiones, roles y rotación de claves
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
