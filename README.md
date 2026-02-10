# VX Control Center

## Objetivo del proyecto

El objetivo del proyecto es crear un sistema que permita registrar los reportes de verificación de equipos en el VX Control Center.

## Arquitectura

Monorepo (Turborepo + pnpm) con:

-   **API**: NestJS + Prisma (PostgreSQL)
-   **Web**: Next.js (App Router)
-   **DB**: Prisma schema en `packages/database/prisma/schema.prisma`

El foco actual del producto es **Reportes**.

## Requisitos

-   Node.js `>= 20`
-   pnpm `>= 9`
-   Docker (para PostgreSQL o para ejecutar todo el stack)

## Estructura

```text
apps/
  api/   # NestJS
  web/   # Next.js
packages/
  database/  # Prisma + migraciones
  types/     # Tipos compartidos
```

## Setup rápido (local)

### 1) Instalar dependencias

Este monorepo usa **pnpm workspaces**. Para evitar inconsistencias, usa `pnpm` (no `npm`/`npx`).

```bash
pnpm install
```

### 2) Levantar PostgreSQL (Docker)

```bash
pnpm docker:up postgres
```

Postgres queda expuesto en `localhost:5433`.

### 3) Variables de entorno

El repo usa `DATABASE_URL` (API/Prisma) y `NEXT_PUBLIC_API_URL` (Web).

-   **API**: `DATABASE_URL` debe apuntar a tu Postgres local.
-   **Web**: `NEXT_PUBLIC_API_URL` debe apuntar a la API.

Valores típicos para local:

```bash
# API
DATABASE_URL="postgresql://postgres:postgres@localhost:5433/vx_control?schema=public"
PORT=3001

# WEB
NEXT_PUBLIC_API_URL="http://localhost:3001"
```

Nota: en `docker-compose.yml` aparecen valores de referencia para producción/containers.

### 4) Migraciones y Prisma Client

```bash
pnpm db:migrate
pnpm db:generate
```

## Ejecutar en desarrollo

En terminales separadas:

```bash
pnpm --filter @vx/api dev
```

```bash
pnpm --filter @vx/web dev
```

## Ejecutar todo con Docker (Full Stack)

Para levantar la aplicación completa (API, Web y Base de Datos) en contenedores:

```bash
docker compose up --build
```

Esto desplegará:

-   **Web**: <http://localhost:3000>
-   **API**: <http://localhost:3001>
-   **PostgreSQL**: Puerto `5432` (interno), expuesto en `5433` (externo).


### URLs

-   **Web**: <http://localhost:3000>
-   **API**: <http://localhost:3001>
-   **Swagger**: <http://localhost:3001/api/docs>

## Endpoints principales

-   **Crear reporte**: `POST /v1/report`
-   **Listar reportes**: `GET /v1/report?limit=20&from=YYYY-MM-DD&to=YYYY-MM-DD&onlyErrors=true&component=pantalla`
-   **Detalle de reporte**: `GET /v1/report/:id`

## Ejemplos con curl

### Crear 1 reporte

```bash
curl -X POST http://localhost:3001/v1/report \
  -H 'Content-Type: application/json' \
  -d '{"timestamp":"2025-12-14T07:59:26.463Z","verificacion_equipos":{"pantalla":{"estado":"correcto","problema":null,"obligatorio":true},"teclado":{"estado":"correcto","problema":null,"obligatorio":true},"raton":{"estado":"defectuoso","problema":"La rueda no funciona","obligatorio":false},"bateria":{"estado":"correcto","problema":null,"obligatorio":false},"otros":{"estado":"defectuoso","problema":"ventiladores hacen ruído.","obligatorio":false}},"resumen":{"total_componentes":5,"componentes_obligatorios":2,"componentes_opcionales":3,"componentes_verificados":5,"componentes_correctos":3,"componentes_defectuosos":2,"equipo_operativo":false,"requiere_atencion":true},"migrasfree_cid":"12345","usuario_grafico":"MOCK_USER_DELEYVA"}'
```

### Crear 10 reportes de prueba (macOS / zsh)

Ejecuta esto en tu terminal (necesita API corriendo en `localhost:3001`):

```bash
for i in $(seq 1 10); do
  ts=$(date -u -v-${i}H +%Y-%m-%dT%H:%M:%S.000Z)
  cid=$((10000+i))
  user="USER_${i}"

  pantalla_estado=correcto
  teclado_estado=correcto
  bateria_estado=correcto
  raton_estado=$([ $((i % 3)) -eq 0 ] && echo defectuoso || echo correcto)
  otros_estado=$([ $((i % 4)) -eq 0 ] && echo defectuoso || echo correcto)

  correctos=0
  defectuosos=0
  for st in "$pantalla_estado" "$teclado_estado" "$raton_estado" "$bateria_estado" "$otros_estado"; do
    if [ "$st" = "defectuoso" ]; then defectuosos=$((defectuosos + 1)); else correctos=$((correctos + 1)); fi
  done

  equipo_operativo=$([ $defectuosos -eq 0 ] && echo true || echo false)
  requiere_atencion=$([ $defectuosos -eq 0 ] && echo false || echo true)

  payload=$(cat <<JSON
{"timestamp":"$ts","verificacion_equipos":{"pantalla":{"estado":"$pantalla_estado","problema":null,"obligatorio":true},"teclado":{"estado":"$teclado_estado","problema":null,"obligatorio":true},"raton":{"estado":"$raton_estado","problema":$([ "$raton_estado" = "defectuoso" ] && echo '"La rueda no funciona"' || echo null),"obligatorio":false},"bateria":{"estado":"$bateria_estado","problema":null,"obligatorio":false},"otros":{"estado":"$otros_estado","problema":$([ "$otros_estado" = "defectuoso" ] && echo '"ventiladores hacen ruido."' || echo null),"obligatorio":false}},"resumen":{"total_componentes":5,"componentes_obligatorios":2,"componentes_opcionales":3,"componentes_verificados":5,"componentes_correctos":$correctos,"componentes_defectuosos":$defectuosos,"equipo_operativo":$equipo_operativo,"requiere_atencion":$requiere_atencion},"migrasfree_cid":"$cid","usuario_grafico":"$user"}
JSON
)

  curl -sS -X POST http://localhost:3001/v1/report \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    >/dev/null
done

echo "OK: 10 reportes creados"
```

## Troubleshooting

-   Si la Web no muestra nada, verifica que `NEXT_PUBLIC_API_URL` apunte a la API.
-   Si Prisma falla conectando, revisa `DATABASE_URL` (puerto `5433` en local).
-   Swagger no lista `/v1/*` (solo `/api/*`). Los endpoints `/v1/report` son públicos para el cliente de escritorio.
