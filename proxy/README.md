# Proxy Perimetral y Seguridad de Red (Caddy 2)

Configuración del servidor proxy inverso perimetral basado en **Caddy v2**, encargado de la terminación TLS automática (Let's Encrypt), enrutamiento de peticiones y refuerzo de seguridad HTTP.

---

## Enrutamiento y Dominios

Caddy gestiona tres subdominios independientes a través de variables de entorno definidas en `.env.prod`:

1. **`{$DOMAIN}` (Portal y Panel de Odoo)**:
   * Termina HTTPS y reenvía tráfico web general a `odoo:8069`.
   * Enruta tráfico de tiempo real y longpolling a `odoo:8072` (`/longpolling/*`, `/websocket`).
   * Bloquea el acceso externo a `/web/database/*` y `/bus_tracking/traccar/webhook` (responde HTTP 404 por seguridad perimetral; el webhook solo se consume dentro de la red Docker interna).
   * Añade atributos de seguridad `Secure; SameSite=Lax` a las cookies de sesión de Odoo.
   * Aplica caché HTTP (`max-age=604800`) a los recursos estáticos de `bus_tracking`.

2. **`{$GPS_DOMAIN}` (Ingesta GPS OsmAnd)**:
   * Recibe paquetes HTTP/HTTPS desde las tabletas y celulares de los choferes en el puerto 443.
   * Reenvía internamente al puerto `5055` de Traccar (`traccar:5055`).

3. **`{$TRACCAR_DOMAIN}` (Panel Web Traccar)**:
   * Proporciona acceso protegido por HTTPS al panel web de administración de Traccar (`traccar:8082`).

---

## Cabeceras de Seguridad Inyectadas

* `Strict-Transport-Security`: HSTS forzado con precarga de subdominios (`max-age=31536000`).
* `X-Content-Type-Options: nosniff`
* `X-Frame-Options: SAMEORIGIN`
* `Referrer-Policy: strict-origin-when-cross-origin`
* `Permissions-Policy: "geolocation=(self), camera=(), microphone=()"`
