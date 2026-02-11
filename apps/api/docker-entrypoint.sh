#!/bin/sh
set -e

echo "[entrypoint] Running Prisma migrations..."
npx prisma migrate deploy --schema=/app/packages/database/prisma/schema.prisma

echo "[entrypoint] Starting API server..."
exec node dist/apps/api/src/main
