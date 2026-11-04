# Configuraciones de Odoo

Archivos de configuración del servidor ERP Odoo 16 para los distintos entornos de ejecución.

---

## Archivos

* **[`odoo.conf`](odoo.conf)**: Configuración para el entorno de desarrollo local mediante `docker-compose.yml`. Configurado para conectarse al contenedor `db` con credenciales de desarrollo.
* **`odoo.prod.conf`** *(generado en despliegue)*: Configuración para el entorno de producción en Azure VM (`docker-compose.prod.yml`). Incluye:
  * `proxy_mode = True`: Reconocimiento de cabeceras HTTPS reenviadas por el proxy perimetral Caddy (`X-Forwarded-Proto`, `X-Forwarded-For`).
  * `workers = 2`: Modo multiproceso para aislar peticiones HTTP de usuarios y crons periódicos de fondo.
  * `db_maxconn = 10`: Tamaño del pool de conexiones `psycopg2` para evitar saturación (`PoolError`) ante ráfagas concurrentes del webhook de Traccar y crons.
  * `limit_time_cpu = 120` y `limit_time_real = 240`: Límites de tiempo para evitar bloqueos por transacciones largas.
