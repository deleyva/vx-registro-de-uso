# Inicio Rápido - VX Control Center 🚀

Esta guía te llevará de 0 a tener el sistema completo funcionando en menos de 10 minutos.

## Prerequisitos

- Node.js 20+ y pnpm
- Docker y Docker Compose
- Git

## Paso 1: Instalación Inicial

```bash
# Clonar el repositorio (si aplica)
cd vx-registro-de-uso

# Instalar dependencias
pnpm install

# Copiar variables de entorno
cp .env.example .env

# Editar .env si necesitas cambiar algo (opcional)
nano .env
```

## Paso 2: Levantar con Docker

```bash
# Levantar todos los servicios
pnpm docker:up

# Espera 30 segundos a que todo inicie...
```

Esto levantará:
- PostgreSQL en puerto 5432
- API (NestJS) en puerto 3001
- Web (Next.js) en puerto 3000

## Paso 3: Configurar Base de Datos

```bash
# Ejecutar migraciones de Prisma
pnpm db:migrate
```

## Paso 4: Verificar que Funciona

Abre tu navegador:

- **Dashboard**: http://localhost:3000
- **API Swagger**: http://localhost:3001/api/docs

## Paso 5: Registrar tu Primer Equipo

### Opción A: Con el Script Automático

```bash
# Dar permisos de ejecución
chmod +x scripts/client-register.sh

# Ejecutar (detecta automáticamente tu sistema)
./scripts/client-register.sh
```

### Opción B: Con curl Manual

```bash
curl -X POST http://localhost:3001/api/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "mi-laptop",
    "ipAddress": "192.168.1.100",
    "macAddress": "00:1B:44:11:3A:B7",
    "osInfo": "macOS 14.0",
    "cpuInfo": "Apple M2 Pro",
    "ramTotal": 16,
    "diskTotal": 512
  }'
```

Guarda el `id` del response, lo necesitarás para enviar métricas.

## Paso 6: Enviar Métricas de Uso (Opcional)

```bash
# Configurar tu Device ID (del paso anterior)
export VX_DEVICE_ID="cly1234567890abcdefg"

# Ejecutar script de métricas
chmod +x scripts/client-usage.sh
./scripts/client-usage.sh
```

Para automatizar, configura cron:

```bash
chmod +x scripts/setup-cron.sh
./scripts/setup-cron.sh
```

## Arquitectura del Proyecto

```
vx-registro-de-uso/
├── apps/
│   ├── api/          → NestJS Backend (puerto 3001)
│   └── web/          → Next.js Frontend (puerto 3000)
├── packages/
│   ├── database/     → Prisma ORM (PostgreSQL)
│   └── types/        → Tipos compartidos TypeScript
├── scripts/          → Scripts de cliente para curl
└── docker-compose.yml
```

## Comandos Útiles

### Desarrollo Local (sin Docker)

```bash
# Terminal 1: Base de datos
docker-compose up postgres

# Terminal 2: API
cd apps/api
pnpm dev

# Terminal 3: Web
cd apps/web
pnpm dev
```

### Docker

```bash
# Levantar servicios
pnpm docker:up

# Ver logs
pnpm docker:logs

# Detener servicios
pnpm docker:down

# Rebuild completo
pnpm docker:down
docker-compose build --no-cache
pnpm docker:up
```

### Base de Datos

```bash
# Generar cliente de Prisma
pnpm db:generate

# Crear migración
pnpm db:migrate

# Abrir Prisma Studio (UI visual)
pnpm db:studio
```

## Endpoints de la API

### Devices

- `POST /api/devices/register` - Registrar equipo
- `GET /api/devices` - Listar equipos
- `GET /api/devices/:id` - Detalle de equipo
- `PATCH /api/devices/:id` - Actualizar equipo
- `DELETE /api/devices/:id` - Eliminar equipo
- `POST /api/devices/:id/heartbeat` - Actualizar última conexión

### Usage Logs

- `POST /api/usage` - Registrar métricas de uso
- `GET /api/usage` - Listar logs
- `GET /api/usage/device/:deviceId` - Logs por equipo

### Estadísticas

- `GET /api/stats/devices` - Estadísticas generales
- `GET /api/stats/usage` - Estadísticas de uso por equipo

## Solución de Problemas

### La API no responde

```bash
# Ver logs
docker logs vx-api

# Verificar que la BD está corriendo
docker logs vx-postgres
```

### El frontend muestra errores

```bash
# Verificar que apunta a la API correcta
cat apps/web/.env
# Debe contener: NEXT_PUBLIC_API_URL=http://localhost:3001
```

### No puedo conectarme a la base de datos

```bash
# Verificar puerto
docker ps | grep postgres

# Reiniciar solo la BD
docker-compose restart postgres
```

### Quiero empezar de cero

```bash
# Eliminar todo (contenedores y volúmenes)
docker-compose down -v

# Reinstalar
pnpm install
pnpm docker:up
pnpm db:migrate
```

## Próximos Pasos

1. **Configurar Tailscale**: Lee [docs/TAILSCALE_SETUP.md](./TAILSCALE_SETUP.md) para acceso remoto seguro
2. **Añadir más equipos**: Ejecuta `client-register.sh` en cada equipo
3. **Automatizar métricas**: Configura cron con `setup-cron.sh`
4. **Personalizar dashboard**: Modifica `apps/web/src/app/page.tsx`
5. **Añadir autenticación**: Implementa JWT en la API

## Documentación Adicional

- [README.md](../README.md) - Información general
- [Tailscale Setup](./TAILSCALE_SETUP.md) - Acceso remoto seguro
- [API Swagger](http://localhost:3001/api/docs) - Documentación interactiva

## Soporte

Si encuentras problemas:
1. Revisa los logs: `pnpm docker:logs`
2. Verifica que todos los puertos estén libres
3. Asegúrate de tener Docker corriendo

¡Disfruta de tu VX Control Center! 🎉
