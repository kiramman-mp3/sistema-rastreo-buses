# Sistema de rastreo de buses (Odoo 16 + Traccar)

Módulo Odoo `bus_tracking` que muestra en un mapa en vivo los buses de un servidor Traccar, con rutas, paraderos y detección de llegada a paraderos.

## Arquitectura

```
Tableta (Buses UTA) --OsmAnd--> Traccar (:5055) --webhook--> Odoo (/bus_tracking/traccar/webhook)
                                      ^                              |
                                      +---- cron cada 1 min (REST /api)
Login, turnos e incidentes: tableta --> Odoo (/bus_tracking/driver/*)
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
4. Crea un bus por tableta, asígnale su ruta y pulsa **Register GPS in Traccar** (Odoo crea el dispositivo). El id OsmAnd llega a la app al iniciar el turno, no se pega a mano.
5. Crea el usuario del chofer (interno + grupo Driver) y sigue `docs/GUIA-CHOFER.md`. App: `apps/conductor-tablet`. Para pruebas sin tableta: `curl "http://localhost:5055/?id=<identificador>&lat=-33.45&lon=-70.66&speed=10"`.
6. `Bus Tracking > Live Map`. Menús **Turnos** e **Incidentes** para el personal.

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

- **Mapa en vivo**: buses en vivo, filtros con contador (en ruta, detenidos, sin señal, con alerta) y una cola de **Atención** con SOS, incidentes, alertas y mensajes nuevos. Un SOS aparece como banda roja hasta que alguien lo marca como atendido; la tableta del chofer ve quién lo atendió.
- **Operación**: *Incidentes* (kanban: sin atender / atendido), *Mensajes de pasajeros* (kanban por estado) y *Turnos*.
- **Flota**: *Buses* (GPS en Traccar), *Recorridos*, *Rutas* y *Choferes*.
- **Reportes**: *Velocidad*, *Sin señal*, *Paradas largas*, *Desvíos de ruta* y *Llegada a paradas*.
- **Configuración**: *Ajustes* y *Notificaciones en este dispositivo*.

El desvío de ruta se mide contra la línea que une las paradas de la ruta, en orden. Las alertas nuevas llegan por push (notificaciones web) a los administradores suscritos desde *Notificaciones en este dispositivo*. No hay correo ni respuestas a quejas.

## Portal de pasajeros

Sin login. La portada (`/`) muestra la línea con más buses en vivo sobre sus paradas, el buscador por parada y todas las líneas. `/rutas` lista las rutas marcadas como *Visible to passengers* (`/rutas?q=pillaro` busca por parada, sin importar tildes) y `/rutas/<código>` muestra la línea de paradas y el mapa: el pasajero toca **su parada** y la página dice cuántas paradas le faltan al bus más cercano (cuenta paradas, nunca promete minutos). Solo se publican nombre, posición, rumbo, estado y el tramo de la línea donde va el bus; nunca placa, chofer ni velocidad. Español e inglés con selector y un borrador de kichwa. Teléfono y correo de contacto solo aparecen si se configuran en *Ajustes*. Identidad y reglas de diseño en `docs/DISENO.md`.

Quejas: `/quejas` es el formulario público (contacto opcional, con protección contra abuso). Llegan a `Bus Tracking > Quejas` con estados, responsable y nota interna; los datos de contacto solo los ven los administradores y se borran a los 90 días de resuelta la queja (ajustable).

## Calidad

Política, reglas, casos de prueba, resultados, defectos, Pareto, Ishikawa y cumplimiento de las ISO están en `docs/calidad/` (índice en `docs/calidad/README.md`). Para repetir las pruebas en vivo y la auditoría: `sh qa/ejecutar_todo.sh`. El guion para defender el proyecto está en `docs/GUION_DEFENSA.md`.

## Desarrollo local con datos y capturas

```bash
cp .env.example .env                      # ODOO_PORT=8070 si el 8069 está ocupado
docker compose up -d --build db odoo
MSYS_NO_PATHCONV=1 docker compose run --rm odoo odoo -d buses -i bus_tracking --load-language=es_EC --without-demo=all --stop-after-init --no-http
docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo < scripts/dev_seed.py
```

`scripts/dev_seed.py` crea 4 líneas de Ambato con paradas aproximadas, 6 buses, los choferes `chofer1` (con turno abierto) y `chofer2`, y algunas quejas; cada nueva ejecución mueve los buses. Solo para desarrollo.

- Capturas del portal y del panel: `python qa/capturas_ui.py --out <carpeta>` (Playwright).
- Capturas de la tableta: `cd apps/conductor-tablet && EXPO_PUBLIC_ODOO_URL=http://localhost:8070 npx expo start --web --port 8081`, luego `python qa/capturas_tablet.py --out <carpeta>`.
- Contraste de los colores: `python qa/contraste.py`. Accesibilidad del portal (axe): `python qa/accesibilidad.py`.
- Con una sola base de datos las páginas públicas funcionan sin sesión; si hay bases de prueba creadas, bórralas o Odoo no sabrá cuál usar.

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
