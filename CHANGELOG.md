# CHANGELOG

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

### Validación

- API: `curl http://localhost:3001/v1/report?limit=5`
- Swagger: `http://localhost:3001/api/docs`
- Web: `http://localhost:3000`

### Próximos pasos

- Añadir paginación real (cursor/offset) para `GET /v1/report`.
- Optimizar filtrado de JSON (derivar campos indexables o materializar estados por componente).
- Mejorar UX: detalle completo del reporte (vista por ID) y navegación.
- Endurecer validación del DTO (enumeraciones de estado, shape de verificación) manteniendo compatibilidad.
