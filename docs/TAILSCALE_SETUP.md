# Configuración de Tailscale para Acceso Remoto Seguro 🔐

Esta guía explica cómo configurar Tailscale para acceder de forma segura a tu VX Control Center desde cualquier lugar.

## ¿Qué es Tailscale?

Tailscale crea una red privada (VPN) entre tus dispositivos de forma automática. Es la forma más sencilla y segura de acceder a tu servidor sin abrir puertos ni configurar firewalls.

## Instalación

### En tu Servidor (donde corre Docker)

**macOS:**
```bash
brew install tailscale
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

**Linux (manual):**
```bash
# Añadir repositorio de Tailscale
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.gpg | sudo apt-key add -
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.list | sudo tee /etc/apt/sources.list.d/tailscale.list

# Instalar
sudo apt-get update
sudo apt-get install tailscale

# Iniciar
sudo tailscale up
```

### En tus Dispositivos Cliente

Instala Tailscale en cualquier dispositivo desde donde quieras acceder:

- **macOS/iOS**: https://tailscale.com/download/mac
- **Windows**: https://tailscale.com/download/windows
- **Android**: Google Play Store
- **Linux**: Mismo comando que arriba

## Configuración Inicial

### 1. Conectar tu Servidor

En el servidor donde corre Docker:

```bash
sudo tailscale up
```

Esto abrirá tu navegador para autenticarte. Inicia sesión con tu cuenta de Google, GitHub o Microsoft.

### 2. Obtener tu IP de Tailscale

Una vez conectado, obtén la IP que Tailscale le asignó a tu servidor:

```bash
tailscale ip -4
```

Ejemplo de salida: `100.101.102.103`

### 3. Probar la Conexión

Desde otro dispositivo con Tailscale instalado y autenticado en la misma cuenta:

```bash
# Ping al servidor
ping 100.101.102.103

# Acceder al dashboard
open http://100.101.102.103:3000

# Acceder a la API
curl http://100.101.102.103:3001/api/devices
```

## URLs de Acceso

Una vez configurado Tailscale, puedes acceder desde cualquier dispositivo conectado:

```
Dashboard: http://[TU-IP-TAILSCALE]:3000
API:       http://[TU-IP-TAILSCALE]:3001
Swagger:   http://[TU-IP-TAILSCALE]:3001/api/docs
```

## HTTPS con Tailscale (Opcional pero Recomendado)

Tailscale puede generar certificados HTTPS automáticamente usando MagicDNS.

### 1. Habilitar MagicDNS

En tu cuenta de Tailscale (https://login.tailscale.com/admin/dns):

1. Ve a **DNS**
2. Habilita **MagicDNS**
3. Habilita **HTTPS Certificates**

### 2. Obtener tu Hostname

```bash
tailscale status
```

Busca tu hostname. Será algo como: `mi-servidor.tail-scale-123.ts.net`

### 3. Configurar Caddy como Reverse Proxy

Crea un `Caddyfile` en la raíz del proyecto:

```caddyfile
# Dashboard
vx-dashboard.tail-scale-123.ts.net {
    reverse_proxy localhost:3000
}

# API
vx-api.tail-scale-123.ts.net {
    reverse_proxy localhost:3001
}
```

Reemplaza `tail-scale-123.ts.net` con tu dominio real de Tailscale.

### 4. Añadir Caddy a Docker Compose

Añade este servicio al `docker-compose.yml`:

```yaml
caddy:
  image: caddy:2-alpine
  container_name: vx-caddy
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
    - caddy_config:/config
  networks:
    - vx-network
  depends_on:
    - web
    - api

volumes:
  caddy_data:
  caddy_config:
```

### 5. Reiniciar con HTTPS

```bash
pnpm docker:down
pnpm docker:up
```

Ahora puedes acceder con HTTPS:

```
https://vx-dashboard.tail-scale-123.ts.net
https://vx-api.tail-scale-123.ts.net/api/docs
```

## Configurar Variables de Entorno

Actualiza tu `.env`:

```env
# Si usas Caddy con HTTPS
NEXT_PUBLIC_API_URL=https://vx-api.tail-scale-123.ts.net

# Si usas solo Tailscale IP
NEXT_PUBLIC_API_URL=http://100.101.102.103:3001
```

## Consejos de Seguridad

### 1. Usar ACLs (Access Control Lists)

Tailscale permite definir quién puede acceder a qué. En https://login.tailscale.com/admin/acls:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["tag:server:3000", "tag:server:3001"]
    }
  ],
  "tagOwners": {
    "tag:server": ["autogroup:admin"]
  }
}
```

### 2. Etiquetar tu Servidor

```bash
# En la consola de Tailscale, etiqueta tu servidor con 'server'
# Esto facilita la gestión de ACLs
```

### 3. Compartir con Equipos

Puedes invitar a otros usuarios a tu red Tailscale sin que tengan acceso a toda tu infraestructura.

## Ventajas de Tailscale vs Exponer Puertos

| Aspecto | Puerto Abierto (tradicional) | Tailscale |
|---------|------------------------------|-----------|
| **Seguridad** | Vulnerable a internet público | Red privada cifrada |
| **Configuración** | Firewall, port forwarding, etc. | 1 comando |
| **IP Dinámica** | Necesitas DynDNS | IP estable automática |
| **Certificados** | Necesitas Let's Encrypt manual | MagicDNS automático |
| **Acceso** | Cualquiera puede intentar | Solo dispositivos autorizados |

## Solución de Problemas

### El servidor no aparece en Tailscale

```bash
# Reiniciar Tailscale
sudo tailscale down
sudo tailscale up

# Ver estado
tailscale status

# Ver logs
sudo journalctl -u tailscaled -f
```

### No puedo acceder aunque Tailscale está conectado

1. Verifica que ambos dispositivos estén en la misma cuenta
2. Verifica que el servidor Docker esté corriendo: `docker ps`
3. Prueba con curl primero: `curl http://[IP]:3001/api/devices`
4. Verifica las ACLs en la consola de Tailscale

### Firewall bloquea la conexión

Si tienes firewall activo, permite Tailscale:

```bash
# Linux (ufw)
sudo ufw allow in on tailscale0

# macOS (no suele ser necesario)
```

## Acceso desde Móvil

1. Instala la app de Tailscale (iOS/Android)
2. Inicia sesión con tu cuenta
3. Abre el navegador y ve a `http://[IP-TAILSCALE]:3000`
4. Añade a favoritos para acceso rápido

## Resumen de Comandos

```bash
# Instalar Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Conectar
sudo tailscale up

# Ver IP
tailscale ip -4

# Ver estado
tailscale status

# Desconectar
sudo tailscale down
```

## Recursos Adicionales

- [Documentación oficial de Tailscale](https://tailscale.com/kb/)
- [Guía de ACLs](https://tailscale.com/kb/1018/acls/)
- [MagicDNS y HTTPS](https://tailscale.com/kb/1153/enabling-https/)
