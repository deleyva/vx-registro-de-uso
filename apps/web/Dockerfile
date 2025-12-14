# Dockerfile para Next.js Web
FROM node:20-alpine AS base

# Instalar pnpm
RUN npm install -g pnpm@9.14.2

# Stage de dependencias
FROM base AS dependencies
WORKDIR /app

# Copiar archivos de configuración
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY turbo.json ./
COPY packages/types/package.json ./packages/types/
COPY apps/web/package.json ./apps/web/

# Instalar dependencias
RUN pnpm install --frozen-lockfile

# Stage de build
FROM base AS build
WORKDIR /app

# Copiar dependencias
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/packages ./packages
COPY --from=dependencies /app/apps/web/node_modules ./apps/web/node_modules

# Copiar código fuente
COPY . .

# Build de Next.js
WORKDIR /app/apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# Stage de producción
FROM node:20-alpine AS production
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copiar archivos necesarios
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /app/apps/web/public ./apps/web/public

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "apps/web/server.js"]
