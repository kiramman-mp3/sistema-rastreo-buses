# Sistema de rastreo de buses (Odoo 16 + Traccar)

Módulo Odoo `bus_tracking` que muestra en un mapa en vivo los buses de un servidor Traccar, con rutas, paraderos y detección de llegada a paraderos.

## Arquitectura

```
GPS / app Traccar Client --> Traccar (:5055, :5023, ...) --webhook--> Odoo (/bus_tracking/traccar/webhook)
                                  ^                                        |
                                  +---- cron cada 1 min (REST /api) -------+
```

- **Webhook**: Traccar reenvía cada posición a Odoo (tiempo real).
- **Cron**: respaldo que consulta `/api/positions` cada minuto, por si el webhook falla.
- Las posiciones duplicadas se descartan (único por bus + hora GPS).

## Puesta en marcha

```bash
cp .env.example .env          # cambia WEBHOOK_SECRET y DB_PASSWORD
docker compose up -d
```

- Odoo: http://localhost:8069 (cambia `ODOO_PORT` en `.env` si el puerto está ocupado)
- Traccar: http://localhost:8082 (primer usuario que se registra queda como admin)

1. En Odoo crea una base de datos e instala la app **Bus Tracking (Traccar)** (activa el modo desarrollador y *Actualizar lista de aplicaciones*).
2. `Bus Tracking > Configuration > Settings`:
   - URL de Traccar: `http://traccar:8082`
   - Usuario/clave (o token API) de Traccar
   - *Webhook secret*: el mismo valor de `WEBHOOK_SECRET` en `.env`
   - **Test connection**.
3. Crea **Routes** con sus paradas (lat/lon y radio de llegada en metros).
4. Crea un bus por cada celular de chofer, asígnale su ruta y pulsa **Register GPS in Traccar**: Odoo crea el dispositivo en Traccar y muestra el identificador y un QR en la sección *Driver's phone*. (Si ya tenías dispositivos en Traccar, **Save and import devices** en Ajustes crea un bus por cada uno.)
5. En el celular sigue `docs/GUIA-CHOFER.md`. Para pruebas sin celular: `curl "http://localhost:5055/?id=<identificador>&lat=-33.45&lon=-70.66&speed=10"`.
6. `Bus Tracking > Live Map`.

En desarrollo el puerto 5055 (OsmAnd) va sin cifrar; en producción los celulares usan HTTPS (ver `docs/PRODUCCION.md`).

## Qué incluye

| Modelo | Uso |
|---|---|
| `bus.vehicle` | Bus, enlazado a `traccar_device_id`; guarda última posición y estado (moving / stopped / offline: sin datos hace 5 min) |
| `bus.route` / `bus.route.stop` | Rutas con paradas ordenadas y radio de llegada |
| `bus.position` | Historial de posiciones (se purga según *Keep positions (days)*) |
| `bus.stop.arrival` | Registro de llegadas a paradas (reporte de puntualidad) |
| `bus.route` (campo `public`) | Controla qué rutas ve el pasajero |
| `bus.alert` | Alertas de exceso de velocidad, bus sin señal y parada larga (umbrales en Ajustes) |
| `bus.activity.report` | Vista de actividad diaria por bus: kilómetros, minutos en movimiento y detenido |

Grupos: **User** (solo lectura + mapa) y **Manager** (todo; admin lo recibe al instalar).

## Personalización

El sistema está ajustado para la Universidad Técnica de Ambato (zona horaria de Ecuador, español de Ecuador, mapa en Ambato, límite urbano de 50 km/h). El nombre, el centro del mapa y el enlace de privacidad se cambian en `Configuración > Ajustes`; el logo y las fotos los aporta la universidad. Ver `docs/PERSONALIZACION.md`.

## Menú del panel

- **Mapa en vivo**.
- **Administración de Buses**: *Buses* (con el registro del GPS del celular), *Recorridos* (los viajes reales de cada bus, escritos por el sistema: salida al dejar la primera parada y llegada al entrar a la última; nadie los llena a mano) y *Rutas* (la ruta y sus paradas).
- **Quejas**: solo se leen y se cambian de estado; las crea el pasajero desde el portal público.
- **Reportes**: *Velocidad*, *Sin señal*, *Paradas largas*, *Desvíos de ruta* y *Llegada a paradas*.
- **Configuración**: *Ajustes* y *Notificaciones en este dispositivo*.

El desvío de ruta se mide contra la línea que une las paradas de la ruta, en orden. Las alertas nuevas llegan por push (notificaciones web) a los administradores suscritos desde *Notificaciones en este dispositivo*. No hay correo ni respuestas a quejas.

## Portal de pasajeros

Sin login: `/rutas` lista las rutas marcadas como *Visible to passengers* y `/rutas/<código>` muestra el mapa con sus buses en vivo (solo nombre, posición, rumbo y estado). Español e inglés con selector. La landing (`/`) lleva a este portal.

Quejas: `/quejas` es el formulario público (contacto opcional, con protección contra abuso). Llegan a `Bus Tracking > Quejas` con estados, responsable y nota interna; los datos de contacto solo los ven los administradores y se borran a los 90 días de resuelta la queja (ajustable).

## Producción

Para instalar en un servidor (HTTPS, secretos, respaldos, monitoreo) ve `docs/PRODUCCION.md`. El archivo `docker-compose.yml` de esta carpeta es solo para desarrollo.

## Notas

- La landing pública está en `/` y `/inicio`; el login y el backend tienen tema propio. Detalles y créditos en `docs/DISENO.md`.
- El mapa usa Leaflet (incluido en `static/lib`) y tiles de OpenStreetMap, por lo que necesita internet en el navegador.
- La conexión Odoo → Traccar y el reenvío Traccar → Odoo asumen la red de Docker (`traccar` y `odoo` como hostnames). Si separas los servidores, ajusta la URL en Settings y `FORWARD_URL` en `docker-compose.yml`.
- El reenvío de Traccar se configura con variables de entorno (`CONFIG_USE_ENVIRONMENT_VARIABLES`): `FORWARD_TYPE=json`, `FORWARD_URL` y `FORWARD_HEADER` (el secreto va en la cabecera `X-Webhook-Secret`). En versiones antiguas de Traccar (5.x) la clave era `forward.json`/`forward.enable`. Verificado con la imagen `traccar/traccar:latest` de octubre 2026.
- La interfaz del módulo viene en inglés con traducción al español (`i18n/es.po`): instala el idioma español en Odoo (`Ajustes > Idiomas`) y elígelo en tu perfil.

## Tests

```bash
docker compose up -d db
docker compose run --rm odoo odoo -d buses_test -i bus_tracking --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all
```

En Git Bash de Windows antepón `MSYS_NO_PATHCONV=1` al comando, o la ruta `/bus_tracking` se convierte en una ruta de Windows.
