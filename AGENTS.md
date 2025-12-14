# AGENTS

## Propósito

Este documento define cómo trabajamos en este repositorio (roles, flujo de cambios, y convenciones) para mantener el proyecto consistente y fácil de evolucionar.

## Roles

- **API (NestJS)**
  - Endpoints públicos para la app de escritorio: `/v1/report`.
  - Swagger en `/api/docs`.
  - Persistencia con Prisma/PostgreSQL.
- **Web (Next.js)**
  - Panel web centrado en la lista de reportes.
  - Filtros y visualización por componentes.
- **DB (Prisma/Postgres)**
  - Esquema en `packages/database/prisma/schema.prisma`.
  - Migraciones vía `pnpm db:migrate`.

## Flujo de trabajo

- **Rama principal**: trabajo directo en local.
- **Cambios pequeños y verificables**: cada cambio debe dejar la app arrancable.
- **Validación rápida antes de cerrar el día**:
  - API: `pnpm --filter @vx/api dev`
  - Web: `pnpm --filter @vx/web dev`
  - Postgres: `pnpm docker:up postgres`
  - Smoke test: `curl http://localhost:3001/v1/report?limit=5`

## Convenciones

- **Rutas**
  - `/v1/*` para la app de escritorio.
  - `/api/*` para Swagger y utilidades internas.
- **Datos**
  - `verificacion_equipos` y `resumen` se guardan como JSON.
- **UI**
  - Ticks verde/rojo por componente.
  - Hover muestra tooltip; tap/click abre modal.

## Checklist para cambios en DB

- Editar `schema.prisma`.
- Ejecutar `pnpm db:migrate`.
- Ejecutar `pnpm db:generate`.
- Reiniciar la API.
