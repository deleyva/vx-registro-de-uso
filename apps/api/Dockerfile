# Dockerfile para NestJS API
FROM node:20-alpine AS base

# Instalar pnpm
RUN npm install -g pnpm@9.14.2

# Stage de dependencias
FROM base AS dependencies
WORKDIR /app

# Copiar archivos de configuración
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY turbo.json ./
COPY packages/database/package.json ./packages/database/
COPY packages/types/package.json ./packages/types/
COPY apps/api/package.json ./apps/api/

# Instalar dependencias
RUN pnpm install --frozen-lockfile

# Stage de build
FROM base AS build
WORKDIR /app

# Copiar dependencias
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/packages ./packages
COPY --from=dependencies /app/apps/api/node_modules ./apps/api/node_modules

# Copiar código fuente
COPY . .

# Generar cliente de Prisma
RUN cd packages/database && pnpm prisma generate

# Compilar la aplicación
WORKDIR /app/apps/api
RUN pnpm build

# Stage de producción
FROM node:20-alpine AS production
WORKDIR /app

# Instalar pnpm
RUN npm install -g pnpm@9.14.2

# Copiar node_modules y build
COPY --from=build /app/apps/api/dist ./dist
COPY --from=build /app/apps/api/node_modules ./node_modules
COPY --from=build /app/apps/api/package.json ./
COPY --from=build /app/packages ./packages

# Variables de entorno por defecto
ENV NODE_ENV=production
ENV API_PORT=3001
ENV API_HOST=0.0.0.0

EXPOSE 3001

CMD ["node", "dist/main"]
