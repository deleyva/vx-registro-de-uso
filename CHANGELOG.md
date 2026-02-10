# CHANGELOG

## 2026-02-10

### Fixes & Infraestructura

- **Docker**: Se solucionaron errores de build y ejecución en los contenedores de API y Web.
    - Se añadió `.dockerignore` para evitar contaminación del contexto de build con binarios de macOS.
    - Se corrigió la resolución de módulos en el Dockerfile de la API (simulando hoisting de `@prisma/client` y parcheando paths).
    - Se aseguró la creación de directorios necesarios (`apps/web/public`).
- **TypeScript**: Se corrigieron errores de compilación (TS2742) en `reports.controller.ts` añadiendo tipos de retorno explícitos.
- **Prisma**: Se ajustó la generación del cliente Prisma dentro del Dockerfile para asegurar su disponibilidad en `node_modules` raíz del contenedor.

## 2025-12-14

### Cambios

- Se corrigieron archivos base del monorepo (turbo/tsconfig) para arrancar en local.
- Se estabilizó Next.js para imports de tipos (`import type`) y alias `@/*`.
- Se configuró NestJS con prefijo global `/api` y Swagger en `/api/docs`.
- Se añadió el endpoint **POST /v1/report** con persistencia en PostgreSQL (Prisma) guardando `verificacion_equipos` y `resumen` como JSON.
- Se añadieron endpoints de consulta: **GET /v1/report** y **GET /v1/report/:id**.
- Se añadieron filtros en la API para `GET /v1/report`: `from`, `to`, `onlyErrors`, `component`.
- Se simplificó la API para centrarse en reportes (se quitaron módulos antiguos del AppModule).
- Se rediseñó el dashboard para centrarse en reportes con filtros y ticks por componente.
- Se corrigió el warning de hydration mismatch con `suppressHydrationWarning` (atributos inyectados por extensiones).
- Se unificó la cabecera de filtros y la tabla en una única caja.
- Se añadió `AGENTS.md` con roles, flujo de trabajo, convenciones y checklist para cambios de DB.
- Se completó `README.md` con guía de ejecución local usando `pnpm`, variables de entorno, endpoints y ejemplos de `curl`.
- Se ajustaron ejemplos `curl` del README para que sean copy/paste friendly y para que el script de 10 reportes use el mismo payload que el ejemplo real.
- Se ajustó `ReportsTable` para poder renderizarse sin header (prop `showHeader`) y así integrarse dentro del contenedor unificado.

### Validación

- API: `curl http://localhost:3001/v1/report?limit=5`
- Swagger: `http://localhost:3001/api/docs`
- Web: `http://localhost:3000`

### Próximos pasos

- Añadir paginación real (cursor/offset) para `GET /v1/report`.
- Optimizar filtrado de JSON (derivar campos indexables o materializar estados por componente).
- Mejorar UX: detalle completo del reporte (vista por ID) y navegación.
- Endurecer validación del DTO (enumeraciones de estado, shape de verificación) manteniendo compatibilidad.
