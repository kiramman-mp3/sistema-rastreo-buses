# Segunda auditoría integral y plan de implementación

Fecha del análisis: 2026-11-17. Base revisada: `develop` en `512bab6` (versión del módulo `16.0.1.6.0`, app `1.0.0`). Alcance: todo el código que corre en producción: módulo Odoo `addons/bus_tracking` (controladores, modelos, seguridad, vistas, plantillas, JS del panel y del portal, migraciones), app de tableta `apps/conductor-tablet`, despliegue (`docker-compose.prod.yml`, `proxy/Caddyfile`, `bi/grafana`, `scripts/`) y CI. La documentación se contrastó con el código. Quedan fuera los scripts de `qa/`, que no corren en producción.

La primera auditoría (2-nov) está en [`PLAN-AUDITORIA.md`](PLAN-AUDITORIA.md); todos sus hallazgos se cerraron. Esta revisa lo que se construyó después (fases R1 a R12, Fleet) y lo que la primera no cubrió.

Veredicto: **no está listo para producción general**. Sirve para un piloto vigilado con pocos buses una vez cerradas las fases 38 a 40. El código está bien probado; lo que falla es el despliegue, algunos flujos de datos de la tableta y lo que nunca se probó en condiciones reales.

## 0. Estado de las verificaciones

| Verificación | Resultado | Nota |
|---|---|---|
| Tablet: `npm run lint` | PASS | |
| Tablet: `npm run typecheck` | PASS | |
| Tablet: `npm test` (jest) | PASS: 27 suites, 167 tests | |
| Tablet: `npm audit --omit=dev` | 9 moderadas, 0 altas o críticas | `node-forge`, `minimatch`; `npm audit fix --force` sube Expo de versión mayor |
| Backend: `python -m compileall` | PASS | |
| Backend: XML bien formado | PASS | Todos los `.xml` del módulo |
| Backend: `qa/traducciones.py` | PASS | `es.po`: 0 sin traducir, 0 modelos inexistentes |
| Backend: suite de Odoo | **No ejecutada en esta auditoría** | Docker no estaba corriendo. Última evidencia: 544 de 544 el 5-nov (`docs/calidad/evidencias/odoo_test.log`) |
| Backend: flake8 | **No ejecutada** | No instalado en la máquina; el CI lo corre |

Severidad: **Crítica** (explotable hoy, o pérdida de datos o de servicio), **Alta** (falla un flujo principal o expone datos), **Media** (falla en casos reales menos frecuentes o deuda que ya cuesta), **Baja** (pulido, consistencia). *Inferido* quiere decir que se dedujo leyendo el código y no se reprodujo.

Los identificadores (X1, B1, W1…) son los de la sesión de auditoría y se mantienen para la trazabilidad con la bitácora y el registro de defectos.

## 1. Hallazgos

### 1.1 Críticos

| ID | Hallazgo | Dónde | Defecto |
|---|---|---|---|
| X1 | XSS guardado en el portal público. Leaflet inserta como HTML el texto de `bindTooltip` y el nombre de la parada llega sin escapar. El nombre puede venir de un GPX importado (cada punto con nombre se vuelve parada): un `<img src=x onerror=...>` se ejecuta a cada pasajero que abre la ruta. El editor de paradas del panel tiene el mismo fallo. | `static/src/portal/portal_map.js:50`, `static/src/js/stop_picker.js:56`, `models/bus_route_gpx.py:60` | DEF-051 |
| W1 | Un SOS en cola se puede perder. `flushIncidents` lee la cola, envía y guarda su copia antigua recortada, sin cerrojo. La pantalla del turno la llama cada 12 s y `fireSos` también: si el SOS entra en la cola mientras otro vaciado está enviando, ese vaciado lo sobrescribe. La tableta muestra "en cola" pero ya no existe. Dos vaciados a la vez envían el mismo incidente dos veces. | `apps/conductor-tablet/src/incidents/queue.ts:46-58`, `src/state/session.ts:254,265-310`, `app/shift.tsx:130,143,181` | DEF-052 |
| B1 | Las posiciones nunca se purgan en una instalación nueva. El cron lee `bus_tracking.retention_days` con 0 por defecto (0 = conservar todo); Ajustes muestra 30 pero sólo lo guarda si alguien pulsa *Guardar*. `init-prod.sh` no lo fija. La base de Traccar tampoco purga sus posiciones. | `models/bus_position.py:35`, `models/res_config_settings.py:28`, `scripts/init-prod.sh` | DEF-053 |
| B2 | La base de datos de producción no arranca tras un `down` + `up -d`. El servicio `db` tiene `profiles: ["local-db"]` y el ejemplo fija `COMPOSE_PROFILES=bi`; `init-prod.sh` lo levanta por nombre, pero un reinicio normal ya no. Además `.env.prod.example` apunta a Supabase mientras `init-prod.sh`, `backup.sh` y `restore.sh` sólo funcionan con la base local. | `docker-compose.prod.yml:14`, `.env.prod.example:11-21` | DEF-054 |
| B3 | El login del panel de Odoo no tiene límite de intentos ni segundo factor, y el usuario `admin` está expuesto a internet. Ya figuraba como limitación conocida. | `docs/guias/PRODUCCION.md` (limitaciones) | DEF-056 |
| B4 | El panel de Traccar es público en `TRACCAR_DOMAIN`, sin restricción de origen. Su valor por defecto en el compose es `traccar.20.119.213.192.nip.io`, que publica la IP del servidor. La guía decía que el panel no se exponía. | `docker-compose.prod.yml:135`, `proxy/Caddyfile` | DEF-055 |
| B5 | Nunca se probó en condiciones reales: servidor Linux, certificados de Let's Encrypt, GPS físico con un chofer durante una jornada, carga con muchos buses y `eas build` de producción. Los respaldos no salen del servidor. | `docs/guias/PRODUCCION.md` ("No se probó") | Pendiente de prueba |

### 1.2 Medios

| ID | Hallazgo | Dónde | Defecto |
|---|---|---|---|
| N1 | Falsa alerta "No signal" tras cada fin de turno. La regla no mira si hay turno: al cerrarse, Odoo descarta las posiciones y `last_fix_time` queda fijo, así que a los 10 minutos se abre la alerta y llega un push a los managers durante las siguientes 6 horas. Ningún test lo cubre. | `models/bus_alert.py:196-203` | DEF-057 |
| X2 | La tableta cierra el turno antes de vaciar la cola GPS: llama a `endShift()` y después a `stopGps()`, que es el que envía lo pendiente. Odoo ya no tiene turno y descarta esas posiciones (el último tramo y todo lo guardado sin señal, hasta 2 h). | `src/state/session.ts:316-341`, `src/gps/tracker.ts:110-133` | DEF-058 |
| W2 | Los incidentes guardados sin señal se borran si el turno ya cerró. El servidor exige turno activo (`409 no_shift`) y la tableta trata ese 409 como rechazo definitivo. Afecta al SOS. | `controllers/driver_api.py:336-338`, `src/state/session.ts:299-310` | DEF-059 |
| Z1 | *Inferido*: un manager de buses que no sea administrador de Odoo no puede crear choferes, cambiarles el grupo ni la contraseña. El menú *Choferes* abre `res.users`, cuya escritura exige `base.group_erp_manager`; `group_bus_manager` no lo hereda. Los tests usan `admin`. | `views/bus_driver_views.xml:67-75`, `security/security.xml:25`, `models/res_users.py:39-62` | DEF-060 |
| Y1 | Al cambiar de servidor (QR de configuración), la tableta conserva el token anterior y lo envía al servidor nuevo en la siguiente consulta. El aviso de cambio de servidor no lo dice. | `src/state/session.ts:99-105`, `app/scan.tsx:63-70` | DEF-061 |
| Y3 | Odoo acepta `http://` como dirección del GPS (`_check_gps_url`) y la tableta no comprueba el esquema (`buildOsmAndUrl` añade `http://` si falta). El identificador OsmAnd, única credencial del bus, viajaría sin cifrar. | `models/res_config_settings.py:101`, `src/gps/osmand.ts:21` | DEF-062 |
| S1 | El token de la credencial QR sigue guardado en claro en `driver_badge_link` y dentro del PNG (365 días). Desde DEF-012 sólo lo leen los managers, pero un volcado de la base o un respaldo filtrado sirve para entrar como el chofer. | `models/res_users.py:113-124` | Riesgo residual de DEF-012 |
| S2 | Las sesiones de la tableta no se revocan al cambiar la contraseña del chofer; sólo con *Cerrar sesión de la tableta*. | `models/res_users.py:59-62` | |
| S3 | El límite de intentos del login del chofer usa también la clave `login:<usuario>`: cualquiera puede bloquear a un chofer concreto con 10 intentos por minuto. El contador vive en memoria de cada worker. | `controllers/driver_api.py:18-19,96` | |
| S4 | El JWT de Grafana viaja en la URL del iframe (`auth_token`) y dura 8 h: queda en los logs del proxy y de Grafana. | `static/src/js/grafana.js:57-60`, `bi/grafana/grafana.env` | |
| S5 | La contraseña del administrador de Traccar se guarda en claro en `ir.config_parameter`. | `models/traccar_api.py:97-98` | |
| S6 | El usuario de la base de Odoo es superusuario de Postgres (patrón de la imagen oficial). | `docker-compose.prod.yml` | Ya documentado |
| D1 | `eas.json`: el perfil `production` tiene `ios.simulator: true` (no se instala en aparatos reales) y la URL de Odoo está fija al nombre por defecto de Azure. | `apps/conductor-tablet/eas.json` | |
| D2 | `npm audit`: 9 vulnerabilidades moderadas en dependencias de la app. | `apps/conductor-tablet/package-lock.json` | |

### 1.3 Robustez y rendimiento

| ID | Hallazgo | Dónde |
|---|---|---|
| N2 | *Inferido*: `_open_alert` hace búsqueda y luego creación sin capturar el `IntegrityError` del índice único. Si coinciden webhook y cron, la petición entera se revierte (500) y la posición se pierde hasta el reintento de Traccar. | `models/bus_alert.py:122-137`, `models/bus_vehicle.py:193` |
| N5 | *Inferido*: la auditoría de sincronización hace una búsqueda por cada posición de Traccar en 6 h. Con muchos buses reportando cada 5 s puede pasar el `limit_time_real` de 240 s y dejar vacío el indicador S2. | `models/bus_quality.py:77-89` |
| X3 | El latido de respaldo del GPS decide con `lastSent`, que no avanza sin señal: añade una posición extra cada 5 s. La cola, pensada para 2 h, se llena en una. | `src/gps/tracker.ts:93-105` |
| X7 | Las vistas `kpi_positions` (subconsulta por viaje) y `kpi_positions_daily` recorren toda `bus_position` en cada refresco de Grafana. | `models/bus_kpi_views.py:71-85` |
| N6 | Varias tablas crecen sin purga: `bus.position.reject`, `bus.sync.audit`, `bus.stop.arrival`, `bus.alert`, `bus.trip` (y sus paradas), `bus.incident`. | modelos |
| N7 | `/bus_tracking/track` devuelve hasta 24 h de posiciones sin límite de filas. | `controllers/main.py:141-145` |
| P1 | El push a managers se envía uno a uno, con 10 s de timeout cada uno, dentro del cron. | `models/bus_push.py:110-125` |

### 1.4 Bajos

| ID | Hallazgo | Dónde |
|---|---|---|
| N3 | `_trip_event` no tiene índice único: bajo concurrencia puede duplicar alertas de viaje. | `models/bus_alert.py:92-112` |
| N4 | La landing cuenta buses simulados; el portal de rutas no. | `controllers/landing.py:31` |
| X4 | `bootstrap-traccar.sh` tiene fijos `cd /home/azureuser/buses` y `-d buses`. | `scripts/bootstrap-traccar.sh` |
| X5 | `action_register_gps` no comprueba que sea manager: crea el dispositivo en Traccar y luego falla la escritura, dejando un dispositivo huérfano. | `models/bus_vehicle.py:284-292` |
| X6 | `grafana-role.sh` sustituye la contraseña con `sed`: `/` o `&` rompen el SQL. | `scripts/grafana-role.sh:16` |
| Y2 | Un QR de credencial cambia el servidor antes de comprobar el login; si falla, la tableta queda apuntando al otro servidor. | `src/state/session.ts:189-201` |
| Y4 | El simulador en producción: envía push de alertas simuladas, escribe minutos planificados en rutas reales si estaban en 0 y cierra viajes reales al llamar a `_cron_close_trips()`. | `models/bus_alert.py:222`, `models/trip_simulator.py:95-98,148` |
| Y5 | Los deep links `uta-buses://login?…` y `setup?…` no los lee ninguna pantalla: escanear con la cámara del sistema abre la app sin iniciar sesión. | `apps/conductor-tablet/app/*.tsx` |
| Z2 | El menú *Choferes* lo ven todos los usuarios de buses. | `views/menus.xml:29-30` |
| W3 | La cola de errores de diagnóstico tiene la misma carrera que W1. | `src/diagnostics/queue.ts:66-75` |
| W4 | El iframe de Grafana se recarga al renovar el token y pierde filtros y zoom. | `static/src/js/grafana.js:45` |
| X8 | La migración `16.0.1.2.0` reemplaza todos los grupos de los choferes internos. Sólo afecta a actualizaciones desde versiones anteriores. | `migrations/16.0.1.2.0/post-migrate.py:21` |
| O1 | `/bus_tracking/health` publica la versión del módulo. | `controllers/main.py:186-188` |
| O2 | La zona horaria está fija en UTC-5 (sólo Ecuador). | `models/bus_trip.py:19` |
| O3 | El CI no construye la app ni mide cobertura; `origin/main` va 2 commits detrás de `develop`. | `.github/workflows/ci.yml` |

### 1.5 Revisado y correcto

Tokens con hash y comparación del secreto en tiempo constante; webhook y `/web/database/*` bloqueados en el proxy; límites de tasa en el portal y el login de choferes; cookie de sesión con `Secure` y `SameSite`; GPX sin XXE (lxml sin entidades); service worker que sólo abre URLs del mismo origen; plantillas sin `t-raw` ni `widget="html"`; mapa en vivo con `escapeHtml`; cola GPS serializada con `exclusive()`; índices únicos parciales en turnos y alertas abiertas; `gitleaks` en el CI; timers del panel limpiados al desmontar; campos secretos de Ajustes con `password="True"`.

## 2. Decisiones que necesita el equipo

1. **Base de datos por defecto (B2). DECIDIDA el 2026-11-17: Supabase.** Odoo, Traccar y Grafana usan Postgres de Supabase; el contenedor `db` queda sólo para desarrollo y laboratorio (perfil `local-db`). Consecuencias:
   - `init-prod.sh`, `backup.sh`, `restore.sh` y `grafana-role.sh` dejan de usar `exec db` y hablan con Supabase desde un contenedor cliente de Postgres.
   - La conexión va por el *session pooler* (puerto 5432) o la conexión directa, nunca por el *transaction pooler* (6543): Odoo mantiene conexiones largas y usa `LISTEN/NOTIFY`. Todo con TLS (`sslmode=require`).
   - La versión de `pg_dump` y `pg_restore` debe ser igual o mayor que la del servidor de Supabase (confirmarla en la consola del proyecto).
   - El tamaño de la base pasa a ser un límite con costo: la retención (B1) es obligatoria y hay que purgar también las posiciones de Traccar, que viven en la misma cuenta. Elegir el plan de Supabase según la sección *Tamaño* de `docs/guias/PRODUCCION.md`.
   - Los respaldos propios (`backup.sh`) siguen siendo necesarios aunque Supabase tenga los suyos: los del proveedor dependen del plan y no incluyen el filestore de Odoo, que vive en el servidor.
   - S6 desaparece: el usuario `postgres` de Supabase no es superusuario.
2. **Acceso al panel (B3).** Recomendado: instalar `auth_totp` (2FA de Odoo Community, obligatorio para managers) y `fail2ban` en el host leyendo los `Login failed` del log de Odoo. La imagen oficial de Caddy no trae limitador de tasa.
3. **Panel de Traccar (B4).** Recomendado: quitarlo del proxy, porque Odoo lo administra por API. Alternativa: dejarlo con `remote_ip` restringido a la red de la universidad.
4. **Gestión de choferes (Z1).** Primero confirmar con un test con un manager que no sea administrador. Si falla: un asistente propio que crea y edita choferes con `sudo()` tras comprobar el grupo, en vez de abrir `res.users` directamente.
5. **Incidentes tras el cierre (W2).** Recomendado: el servidor acepta un incidente sin turno activo si su `reported_at` cae dentro del último turno del chofer cerrado hace menos de 2 h.
6. **Credencial QR (S1).** Recomendado: no guardar el enlace; mostrar el QR una sola vez al generarlo (asistente transitorio) y guardar sólo el hash. Imprimir la credencial pasa a ser un paso obligatorio al emitirla.

## 3. Fases

Numeración a continuación de la fase 37 (`PLAN-UI-MOVIL.md`). Cada fase es una rama desde `develop`, commits pequeños con Conventional Commits, pruebas en el mismo commit que el arreglo y `merge --no-ff`. Tamaño: S (horas), M (un día), L (varios días).

### Fase 38. `fix/xss-y-cola-sos` (X1, W1, W3) — S

- `fix: escape stop names in map tooltips` en el portal y el editor de paradas: pasar un nodo de texto (`document.createTextNode`) o escapar con la misma función que usa `live_map.js`.
- `fix: serialize the incident queue` con un `exclusive()` como el de `LocationQueue`; `push`, `flushIncidents` y `clear` pasan por él.
- `fix: serialize the error report queue` (mismo patrón).
- Pruebas: `incidents/queue.test.ts` y `diagnostics/queue.test.ts` (un `push` durante un vaciado lento no se pierde; dos vaciados a la vez no envían dos veces); `qa/` con Playwright: una parada llamada `<img src=x onerror=...>` no crea un `<img>` en el tooltip del portal.

### Fase 39. `fix/despliegue-produccion` (B1, B2, B4, X4, X6, S5) — M

- `fix: purge positions after 30 days unless configured` (valor por defecto 30 en el cron) y migración `16.0.1.7.0` que fija `bus_tracking.retention_days` si no existe.
- `feat: set up an external database from init-prod` (decisión 1): con `DB_HOST` distinto de `db`, no levantar `db`; crear el rol y la base `traccar` y comprobar la base de Odoo con `docker run --rm $POSTGRES_IMAGE psql` contra Supabase; escribir `db_sslmode = require` en `config/odoo.prod.conf`.
- `feat: back up and restore an external database` con `pg_dump` y `pg_restore` desde el mismo contenedor cliente; `restore.sh` sigue pidiendo `--yes` y comprueba antes que la versión del cliente sirva.
- `fix: run grafana-role against the external database by default` (con `PSQL` armado desde `.env.prod`).
- `chore: make the production env example match supabase` (session pooler, `GRAFANA_DB_SSLMODE=require`, `POSTGRES_IMAGE` con la versión del servidor, sin la IP en ningún dominio) y dejar claro en el compose que `db` es sólo para `local-db`.
- `fix: stop publishing the traccar panel` según la decisión 3; quitar el dominio con la IP del compose.
- `chore: purge traccar positions` con la opción de retención de Traccar (`database.historyDays`; confirmar la clave en la documentación de 6.16).
- `fix: use the env file and odoo db in bootstrap-traccar`.
- `fix: pass the grafana password to psql as a variable` en vez de `sed`.
- `feat: keep a traccar api token instead of the admin password` (pedir el token tras crear el administrador y no guardar la contraseña).
- `chore: write db_maxconn in the generated production config`.
- Pruebas: test del cron de purga sin parámetro; `init-prod.sh` desde cero contra un proyecto de Supabase vacío, `docker compose down && up -d`, `backup.sh` y `restore.sh --target-db` contra ese proyecto, en una VM Linux limpia.

### Fase 40. `fix/acceso-panel` (B3, S3, O1) — S

- `feat: require two-factor sign-in for managers` según la decisión 2 (`auth_totp` en `depends` o instalado por `init-prod.sh`).
- `docs: protect odoo sign-in with fail2ban` (filtro y jail de ejemplo en `docs/guias/PRODUCCION.md`).
- `fix: rate-limit driver sign-in per address and login together` para que no se pueda bloquear a un chofer desde otra IP.
- `fix: hide the module version from the public health check` (o dejarla sólo con un token).

### Fase 41. `fix/turnos-y-alertas` (N1, X2, W2, N2, N3, N4, Y4) — M

- `fix: only raise no-signal alerts for buses on a shift` y cerrar la alerta abierta al terminar el turno.
- `fix: send queued positions before ending the shift` en la tableta: `stopGps()` (que vacía la cola) antes de `client.endShift()`.
- `fix: accept incidents reported during a shift that just ended` según la decisión 5; la tableta deja de borrar un incidente por `no_shift` mientras ese plazo no venza.
- `fix: tolerate a concurrent alert instead of failing the position` (savepoint alrededor de la creación, y releer la existente).
- `fix: keep one trip event per trip, kind and stop` (índice único parcial).
- `fix: leave simulated buses out of the landing count`.
- `fix: keep the simulator away from real data` (sin push de alertas simuladas, sin escribir en rutas reales, cierre sólo de sus viajes).
- Pruebas: `test_alerts.py` (turno cerrado no da "No signal"), `test_driver_shift.py` (incidente con `reported_at` dentro de un turno recién cerrado), `session.test.ts` (orden de cierre), `test_ingest.py` (alerta concurrente), `test_trip_simulator.py` (sin push, ruta real intacta).

### Fase 42. `fix/tableta-servidor-y-gps` (Y1, Y2, Y3, X3, Y5) — S

- `fix: sign out when the server changes` (borrar token, detener GPS, volver al login) y avisarlo en el diálogo.
- `fix: switch server only after the badge is accepted`.
- `fix: require https for the gps address` en Odoo (salvo hosts locales) y en la tableta.
- `fix: base the gps heartbeat on the last fix, not the last send`.
- `feat: sign in from a badge link opened by the camera` o quitar el esquema del enlace si no se va a usar.
- Pruebas: `session.test.ts` (cambio de servidor sin token), `osmand.test.ts` (rechaza `http` externo), `runtime.test.ts` (sin duplicados sin señal), `test_driver_shift.py` (`gps_url` http rechazada).

### Fase 43. `fix/permisos-choferes` (Z1, Z2, X5, S1, S2) — M

- `test: a bus manager who is not an odoo admin manages drivers`: confirma o descarta Z1.
- Según el resultado y la decisión 4: `feat: manage drivers from a wizard`.
- `fix: show the drivers menu to managers only`.
- `fix: only managers register a gps device` (comprobación antes de llamar a Traccar).
- `fix: show the badge qr once and keep only its hash` según la decisión 6, con migración que borra `driver_badge_link` y `driver_badge_qr` existentes (los choferes deben recibir una credencial nueva).
- `fix: sign the tablets out when a driver's password changes`.
- Pruebas: `test_driver_staff.py`, `test_driver_badge.py`, `test_gps_setup.py`.

### Fase 44. `perf/carga-y-purga` (N5, N6, N7, X7, P1, W4) — M

- `perf: compare traccar and odoo positions in one query per bus` en la auditoría de sincronización.
- `feat: purge old rejects, audits, arrivals and closed events` con plazos en Ajustes (y en `docs/diseno/PRIVACIDAD.md`).
- `perf: cap the track endpoint` (submuestreo a un máximo de puntos).
- `perf: read daily positions from a summary table` (o vista materializada refrescada por cron) para Grafana, e índice por `(vehicle_id, fix_time)` en la vista por viaje.
- `perf: send pushes with a shorter timeout and a time budget per cron run`.
- `fix: renew the grafana token without reloading the dashboard` si Grafana lo permite; si no, documentar W4 y S4 como limitaciones.
- Prueba: `qa/rendimiento_volumen.py` con 1 000 000 de posiciones antes y después.

### Fase 45. `chore/build-y-dependencias` (D1, D2, O3) — S

- `fix: build real ios devices in the production profile` y leer `EXPO_PUBLIC_ODOO_URL` del entorno de EAS en vez de fijarla en `eas.json`.
- `chore: update dependencies flagged by npm audit` sin cambiar la versión mayor de Expo.
- `ci: export the tablet bundle` (`npx expo export --platform android`) para detectar roturas de build.
- `ci: report python coverage` (subir `coverage.xml` como artefacto).

### Fase 46. Pruebas reales y salida a producción (B5) — L

- VM Linux limpia: `init-prod.sh` con dominios reales y Let's Encrypt; `down` y `up`; respaldo, restauración en paralelo y copia fuera del servidor.
- Jornada real: dos tabletas, turno completo de ida y vuelta, corte de red, SOS sin señal, cierre de turno sin señal y cierre desde la oficina.
- Carga: webhook con 50 buses a 5 s durante una hora, midiendo el p95 del mapa y la auditoría.
- Suite de Odoo completa, `qa/ejecutar_todo.sh`, SonarQube, y actualizar `docs/calidad/` con las evidencias nuevas.
- `develop` → `main` con `merge --no-ff` y etiqueta `v1.0.0-rc1`; tras la jornada real sin defectos críticos, `v1.0.0`.

### Fase 47. `docs/cierre-auditoria-2` — S

- Cerrar DEF-051 a DEF-062 en `qa/datos_calidad.py` con su prueba, regenerar `docs/calidad` (`qa/generar_docs.py`) y actualizar `PRODUCCION.md` (limitaciones), `OPERACION.md`, `GUIA-CHOFER.md`, `BITACORA.md` y `ROADMAP.md`.

## 4. Orden y dependencias

```
38 (XSS, SOS) ──┐
39 (despliegue) ├─► 41 (turnos) ─► 43 (choferes) ─► 44 (carga) ─► 46 (real) ─► 47 (docs)
40 (acceso) ────┘        │
                         └─► 42 (tableta)        45 (build) ──────────────────┘
```

Las fases 38, 39 y 40 bloquean el piloto. La 42 y la 45 pueden ir en paralelo con las demás. La 46 exige todas las anteriores.

## 5. Matriz de pruebas nuevas

| Archivo | Casos | Hallazgos |
|---|---|---|
| `src/incidents/queue.test.ts`, `src/diagnostics/queue.test.ts` | push durante un vaciado lento, vaciados concurrentes | W1, W3 |
| `qa/` (Playwright) | nombre de parada con HTML en el portal y el editor | X1 |
| `tests/test_ingest.py` | purga sin parámetro, alerta concurrente | B1, N2 |
| `tests/test_alerts.py` | sin "No signal" tras cerrar el turno | N1 |
| `tests/test_driver_shift.py` | incidente tras el cierre dentro del plazo, `gps_url` http | W2, Y3 |
| `src/state/session.test.ts` | orden de cierre, cambio de servidor, credencial antes del cambio | X2, Y1, Y2 |
| `src/gps/runtime.test.ts` | latido sin duplicados | X3 |
| `tests/test_driver_staff.py`, `tests/test_driver_badge.py` | manager no admin, menú, QR de una sola vez, revocación por contraseña | Z1, Z2, S1, S2 |
| `tests/test_gps_setup.py` | registro de GPS sólo para managers | X5 |
| `tests/test_trip_simulator.py`, `tests/test_http.py` | simulador aislado, landing sin simulados, `track` acotado | Y4, N4, N7 |

## 6. Definición de terminado

Una fase está terminada cuando: cada hallazgo tiene su prueba y pasa; lint, typecheck, jest, flake8 y la suite de Odoo están en verde; el defecto correspondiente figura como cerrado en `qa/datos_calidad.py`; la bitácora tiene su entrada; y la rama se integró en `develop` con `merge --no-ff`.
