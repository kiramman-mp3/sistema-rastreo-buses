# Despliegue en el homelab

Cómo corre hoy la demostración pública (`https://buses.madebyjohan.xyz`). Es el despliegue vigente desde el 21-nov-2026; la guía genérica para un servidor con IP pública (con Caddy y Let's Encrypt, y la VM de Azure que se usó antes) sigue en [`PRODUCCION.md`](PRODUCCION.md). Los datos de esta página se tomaron del servidor (`~/apps/buses`, `~/infra`) el 21-nov-2026; los secretos viven solo allí, nunca en el repositorio.

## Qué hay en el servidor

Un equipo Linux (Debian 13, Docker 29) que aloja varios proyectos. Cada uno vive en `~/apps/<proyecto>/` con su carpeta `app/` (clon del repositorio) y su propio `compose.yaml`. Lo compartido está en `~/infra/`.

| Pieza | Contenedor | Qué hace |
|---|---|---|
| Túnel de Cloudflare | `cloudflared` (en `~/infra/compose.yaml`) | Recibe el tráfico público de los dominios y lo manda por la red Docker `edge` a `buses-web:80`. El TLS lo pone Cloudflare |
| Proxy | `buses-web` (Caddy 2) | Sirve HTTP (`auto_https off`) y confía en `X-Forwarded-Proto` del túnel. Pone las cabeceras de seguridad y el caché de estáticos |
| Odoo | `buses-odoo` (imagen `buses-odoo:16.0`, construida desde `docker/odoo`) | Módulo `bus_tracking`, desde `app/addons` montado de solo lectura |
| Traccar | `buses-traccar` (`traccar/traccar:6.16.0`) | Recibe el GPS (OsmAnd, puerto 5055) y reenvía cada posición a Odoo por webhook |
| Base de datos | `buses-db` (`postgres:17`) | Bases `buses` (Odoo) y `traccar`, en el volumen `db-data` |

Dominios del túnel:

| Dominio | Destino | Uso |
|---|---|---|
| `buses.madebyjohan.xyz` | `buses-web` → Odoo (8069; `/websocket` y `/longpolling` al 8072) | Panel, portal de pasajeros y API de la tableta |
| `gps-buses.madebyjohan.xyz` | `buses-web` → Traccar (5055) | A donde las tabletas envían la posición |

### Diferencias con `docker-compose.prod.yml`

El `compose.yaml` del homelab parte de `docker-compose.prod.yml`, con estos cambios:

- Postgres es local (contenedor `buses-db`), no Supabase.
- No hay ACME ni puertos 80 y 443 publicados: el único camino de entrada es el túnel, por la red `edge`.
- El Caddyfile se adaptó (`proxy/Caddyfile` es el de producción con TLS propio). Sigue bloqueando con 404 el webhook (`/bus_tracking/traccar/webhook`) y el gestor de bases (`/web/database/*`), que solo se alcanzan por la red interna.
- `odoo.conf` del servidor: `dbfilter = ^buses$`, `list_db = False`, `proxy_mode = True`, 2 *workers*, un hilo de cron y límites de memoria de 1 GB (suave) y 1,25 GB (duro).

## Despliegue continuo

Un cron revisa GitHub cada 5 minutos (`~/infra/cd/deploy.sh`, entrada `*/5 * * * *`). Para este proyecto mira la rama **`main`**; `develop` nunca se despliega.

Qué hace cuando `main` tiene commits nuevos:

1. Baja el commit (`git fetch --depth=1`) y actualiza `app/` con `git reset --hard`. Si `app/` tiene cambios locales sin commit, **no despliega** y deja la marca `FAILED-buses`.
2. Reconstruye y levanta los contenedores (`docker compose up -d --build --remove-orphans`).
3. Si cambió algo dentro de `addons/`, detiene Odoo, ejecuta `odoo -d buses -u bus_tracking --stop-after-init` (corre las migraciones de `addons/bus_tracking/migrations/`) y vuelve a levantar todo.
4. Espera hasta 3 minutos a que `https://buses.madebyjohan.xyz/web/login` responda 2xx o 3xx.
5. Si algo falla, vuelve al commit anterior, lo levanta de nuevo y deja `FAILED-buses` con el commit que falló.

Solo corre un despliegue a la vez (`flock`). Para no esperar al cron:

```bash
ssh homelab '~/infra/cd/deploy.sh --dry-run buses'   # muestra qué se desplegaría, sin tocar nada
ssh homelab '~/infra/cd/deploy.sh buses'             # despliega ya
```

El registro está en `~/infra/cd/logs/deploy.log` (el detalle de cada compilación, en `logs/buses.log`) y se rota cada semana.

Por esto, **integrar en `main` equivale a publicar**: sigue el flujo de ramas del `CLAUDE.md` y haz el `merge` a `main` solo con `develop` probado.

## Respaldos

No hay un respaldo automático programado en este servidor (el cron solo tiene el despliegue y la rotación de logs). Antes de un cambio que toque datos, se vuelca la base a mano:

```bash
ssh homelab 'docker exec buses-db pg_dump -U odoo buses | gzip > ~/backups/buses-pre-<motivo>-<fecha>.sql.gz'
```

Los respaldos quedan en `~/backups/` del mismo servidor, así que no protegen de perder el equipo. El respaldo diario con `scripts/backup.sh` del repositorio está pensado para el servidor de [`PRODUCCION.md`](PRODUCCION.md).

## Datos de demostración para los reportes

La base del homelab tiene datos reales (una línea, dos buses) y, desde el 21-nov-2026, datos simulados para mostrar los reportes. El script [`scripts/demo_reportes.py`](../../scripts/demo_reportes.py) agrega las líneas L1 a L4, cuatro choferes (`chofer1` a `chofer4`), 21 días de viajes simulados por línea (con sus multas) y 24 quejas. No toca lo real: los viajes salen de buses simulados («Sim L1»…) y se marcan `simulated`.

```bash
ssh homelab 'docker exec -i buses-odoo sh -c "odoo shell -d buses --no-http --db_host db --db_user odoo --db_password \"\$PASSWORD\" --log-level=error"' < scripts/demo_reportes.py
```

Repetirlo agrega viajes en días anteriores y no duplica los de un día que ya tiene. Los choferes de demostración tienen la contraseña igual a su usuario: **cámbiala o desactívalos** si el sitio va a seguir público.

## Operación diaria

| Tarea | Comando |
|---|---|
| Ver los contenedores | `ssh homelab 'docker ps --format "{{.Names}} {{.Status}}" \| grep buses'` |
| Ver el registro de Odoo | `ssh homelab 'docker logs --tail 100 buses-odoo'` |
| Ver el último despliegue | `ssh homelab 'tail -20 ~/infra/cd/logs/deploy.log'` |
| Saber si un despliegue falló | `ssh homelab 'ls ~/infra/cd/logs/FAILED-buses'` |
| Comprobar que hay GPS entrando | `https://buses.madebyjohan.xyz/bus_tracking/health` (200 `ok` o 503 `stale`) |

## Lo que no está resuelto

- No hay respaldo automático ni copia fuera del equipo.
- La salida a producción real (fase 46 de [`PLAN-AUDITORIA-2.md`](../arquitectura/PLAN-AUDITORIA-2.md): jornada con tabletas) sigue pendiente; este despliegue es la demostración.
- El túnel de Cloudflare es un tercero en el camino de los datos: el GPS pasa por su red antes de llegar a Traccar.
