# Auditoría integral y plan de implementación

Fecha del análisis: 2026-11-02. Base revisada: `develop` en `17781a9`. Alcance: módulo Odoo `addons/bus_tracking` (modelos, controladores, seguridad, vistas, JS del panel y del portal), app de tableta `apps/conductor-tablet`, scripts y despliegue (`scripts/`, `docker-compose*.yml`, `proxy/`), CI (`.github/workflows/ci.yml`) y toda la documentación de `docs/` y `README.md`.

Cómo se hizo: lectura del código completo (salvo los recursos generados: Leaflet incrustado, `package-lock.json`, PDF), ejecución de las verificaciones disponibles y contraste de cada afirmación de la documentación con el código.

## 0. Estado de las verificaciones

| Verificación | Resultado | Nota |
|---|---|---|
| Tablet: `npx jest` | PASS: 13 suites, 56 tests | Sin pruebas de `gps/runtime.ts`, `gps/tracker.ts`, hooks ni pantallas |
| Tablet: `npx tsc --noEmit` | PASS | |
| Tablet: `npx expo lint` | PASS | CI no lo ejecuta (OPS-02) |
| Backend: `python -m compileall` | PASS | |
| Backend: suite Odoo (`--test-tags /bus_tracking`) | **No ejecutada** | Requiere crear y borrar una base temporal; queda pendiente. Hay 213 métodos `test_*` en 16 archivos; la documentación habla de 216, 232 y 247 (DOC-02) |

Severidad: **Crítica** (explotable hoy o pérdida de datos/servicio), **Alta** (falla un flujo principal o expone datos), **Media** (falla en casos reales menos frecuentes o deuda que ya cuesta), **Baja** (pulido, consistencia).

## 1. Hallazgos

### 1.1 Seguridad

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| SEC-01 | Crítica | `action_generate_driver_badge` y `action_revoke_driver_badge` no comprueban permisos y escriben con `sudo()`. Cualquier usuario interno (los choferes lo son, SEC-05) puede llamarlos por RPC sobre **otro** usuario. El botón sólo está oculto en la vista. | `models/res_users.py:97-124`, `views/bus_driver_views.xml:22-28` |
| SEC-02 | Crítica | El token de la credencial QR se guarda **en claro** en `res.users.driver_badge_link` (y dentro del PNG `driver_badge_qr`), campos sin `groups`. Cualquier usuario interno puede leer el enlace de otro chofer y entrar como él. Contradice el diseño de `bus.driver.token`, que sólo guarda el hash. | `models/res_users.py:14-15, 107-114`, `models/bus_driver_token.py:16-17` |
| SEC-03 | Crítica | Contraseña del administrador de Odoo de producción escrita en un script versionado en un repositorio público de GitHub. Aunque se borre del archivo, sigue en el historial: hay que **rotarla**. | `scripts/clean-azure-db.sh:33` |
| SEC-04 | Alta | El token de la credencial (365 días) funciona como token de sesión en todos los endpoints porque `_user_for` no filtra `device_label`; un `logout` hecho con él revoca la credencial. Además `login_badge` acepta también un token de sesión y lo canjea por otro nuevo de 30 días, así que una sesión robada se renueva para siempre. La tableta, si `login_badge` responde 404, guarda la credencial como sesión. | `models/bus_driver_token.py:43-55`, `controllers/driver_api.py:110-112`, `apps/conductor-tablet/src/state/session.ts:184-188` |
| SEC-05 | Alta | Los choferes se crean como usuarios internos (`base.group_user`): pueden entrar a `/web` y leer contactos y usuarios de toda la empresa. Sólo necesitan la API de la tableta. | `models/res_users.py:36-45, 71-83` |
| SEC-06 | Alta | Odoo acepta posiciones de un bus sin turno activo. Si la tableta sigue enviando tras cerrar o revocar el turno (TAB-01, TAB-02), se siguen guardando. La guía promete "posición solo con turno abierto" y no se cumple en el servidor. | `models/bus_vehicle.py:172-185`, `docs/GUIA-CHOFER.md:39` |
| SEC-07 | Alta | La tableta guarda el token de sesión **siempre** también en `AsyncStorage` (texto plano, incluido en las copias de seguridad de Android) y lo lee de ahí como respaldo: `SecureStore` no protege nada. | `apps/conductor-tablet/src/state/secureStore.ts:20-59` |
| SEC-08 | Media | Cualquier QR que no sea una credencial se acepta como dirección del servidor sin confirmar, y la credencial puede cambiar el servidor; se admite `http:`. Un QR malicioso desvía la contraseña del chofer y el GPS a otro host. | `apps/conductor-tablet/app/scan.tsx:39-41`, `src/state/session.ts:173-175`, `src/config/odooUrl.ts:12` |
| SEC-09 | Media | `/bus_tracking/track` acepta `hours` sin límite ni validación: un valor enorme da `OverflowError` (500) y uno grande vuelca todo el historial; `vehicle_id` no numérico da 500. | `controllers/main.py:97-105` |
| SEC-10 | Media | El secreto del webhook se acepta también por parámetro de URL (queda en los logs de acceso). | `controllers/main.py:109-114` |
| SEC-11 | Media | `RateLimiter` nunca olvida claves: con muchas IP distintas la memoria de cada worker crece sin límite. | `controllers/portal.py:48-69` |
| SEC-12 | Baja | Clave de teselas de CARTO escrita en cuatro sitios; dependencia de un tercero no documentada (el README dice OpenStreetMap). | `static/src/js/live_map.js:11`, `static/src/js/stop_picker.js:10`, `static/src/portal/portal_map.js:24`, `apps/conductor-tablet/src/map/html.ts:59` |
| SEC-13 | Baja | `.env.prod.example` trae el identificador real del proyecto de Supabase en vez de un marcador. | `.env.prod.example:13-19` |
| SEC-14 | Baja | La app pide `RECORD_AUDIO` sin usarlo y repite permisos con y sin prefijo. | `apps/conductor-tablet/app.json:21-34` |

### 1.2 Backend (Odoo)

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| BE-01 | Alta | Carrera webhook/cron: `_apply_position` comprueba duplicados con `search_count` y luego inserta. Si llegan a la vez, la restricción única lanza `IntegrityError`: el webhook responde 500 (sólo captura `ValueError`/`ValidationError`) y Traccar reintenta; en el cron se aborta la transacción de todos los buses. | `models/bus_vehicle.py:113-131, 190-199`, `controllers/main.py:122-126` |
| BE-02 | Alta | El envío push sólo captura `WebPushException`. Un error de red (`ConnectionError`, `Timeout`) aborta `_cron_push` antes de marcar `notified`: los mismos avisos se reenvían cada minuto a los dispositivos que sí los recibieron y una suscripción rota bloquea toda la cola. | `models/bus_push.py:84-105`, `models/bus_alert.py:179-195`, `models/bus_incident.py:63-80` |
| BE-03 | Alta | La "próxima parada" de la tableta es la primera parada sin llegada **desde el inicio del turno**. Tras la primera vuelta todas tienen llegada y la cabina muestra "sin próxima parada" el resto del turno (hasta 14 h); el regreso no se contempla. | `controllers/driver_api.py:207-216`, `apps/conductor-tablet/src/shift/progress.ts:11-21` |
| BE-04 | Alta | Si `bus_tracking.gps_url` está vacío, `shift/start` responde éxito con `gps_url: ""`; la tableta descarta credenciales sin URL y el GPS nunca arranca, con la cabina en "Esperando señal" sin explicación. `dev_seed.py` y `clean-azure-db.sh` no lo configuran. | `controllers/driver_api.py:180-185`, `apps/conductor-tablet/src/gps/store.ts:16-25`, `scripts/dev_seed.py` |
| BE-05 | Media | Un SOS o incidente sin atender desaparece de la cola *Atención* del mapa a las 24 h. Un SOS debe seguir visible hasta que alguien lo atienda. | `models/bus_incident.py:47-51` |
| BE-06 | Media | `bus.route.stop` no valida radio (> 0) ni rango de latitud/longitud fuera del selector de mapa; `bus.route.color` no valida el formato hexadecimal en el modelo. | `models/bus_route.py:14-16, 79-84` |
| BE-07 | Media | El asistente de grabación de trazado no valida que *Desde* sea anterior a *Hasta*. | `models/bus_route_record.py:18-30` |
| BE-08 | Media | La alerta de desvío decodifica el JSON del trazado (hasta 1.500 puntos) y crea un `PathMeasure` en **cada** posición de cada bus. Conviene cachear por ruta. | `models/bus_alert.py:124-136`, `models/bus_route.py:31-47` |
| BE-09 | Media | `traccar_api._call` llama `resp.json()` sin capturar `ValueError`; una página HTML de error (proxy) rompe el cron, que sólo captura `UserError`. | `models/traccar_api.py:55`, `models/bus_vehicle.py:201-209` |
| BE-10 | Media | `/driver/me` lista buses sin GPS registrado (fallan al iniciar turno con `no_gps`) y `shift/start` acepta rutas archivadas o una ruta distinta a la del bus sin aviso. | `controllers/driver_api.py:126-170` |
| BE-11 | Baja | `int()` directo sobre parámetros del sistema: un valor no entero rompe alertas, salud y retención. | `models/bus_alert.py:77-79`, `controllers/main.py:133`, `models/bus_complaint.py:72-73` |
| BE-12 | Baja | Traducciones: textos fuente en español en `res_users.py` y `bus_driver_views.xml` (el resto del módulo usa inglés + `es.po`); `es.po` cita seis modelos que ya no existen (`bus_activity_report`, `bus_service`, `bus_service_leg`, `bus_roster_import`, `bus_complaint_reply`, `bus_notification`), le faltan los nuevos (`bus_run`, `bus_driver_token`, `bus_route_record`) y tiene 24 entradas vacías. | `i18n/es.po`, `i18n/bus_tracking.pot` |
| BE-13 | Baja | Una queja enviada en menos de 3 s se descarta en silencio. Si llega precargada desde la portada (`texto`), una persona real puede enviarla así de rápido y la pierde creyendo que se envió. | `controllers/complaints.py:107-110` |
| BE-14 | Baja | El nombre del bus no es único y el mapa público identifica los buses por nombre: dos buses homónimos se funden en un marcador. | `models/bus_vehicle.py:23`, `static/src/portal/portal_map.js:121-154` |
| BE-15 | Baja | *Cerrar sesión de la tableta* borra también la credencial QR, pero la imagen sigue en la ficha del chofer. | `models/bus_shift.py:46-54` |

### 1.3 Panel de Odoo (mapa en vivo, selector de paradas)

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| PAN-01 | Media | El selector de paradas tiene textos en español sin `_t` y, al guardar, la ficha de la ruta no recarga la lista de paradas. | `static/src/js/stop_picker.js:99, 112-114, 120` |
| PAN-02 | Media | El mapa en vivo sólo redibuja rutas si cambia la lista de ids: paradas o trazados editados no aparecen hasta recargar. | `static/src/js/live_map.js:287-293` |
| PAN-03 | Baja | `acknowledge()` y `showTrack()` no manejan errores: un fallo de red queda como rechazo no atendido y sin aviso. | `static/src/js/live_map.js:494-520` |
| PAN-04 | Baja | Los marcadores filtrados quedan al 18 % de opacidad pero siguen recibiendo clic y foco de teclado. | `static/src/js/live_map.js:398-406` |
| PAN-05 | Baja | En el mapa público el título del marcador de bus no se actualiza (`options.title` no toca el DOM). | `static/src/portal/portal_map.js:132` |

### 1.4 Portal de pasajeros

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| PORT-01 | Alta | El feed limita 60 peticiones por minuto e IP y cada página consulta cada 10 s: con unas 10 pestañas detrás de la misma IP (Wi-Fi del campus, CGNAT del operador) los pasajeros ven "demasiadas consultas". La respuesta ya se cachea 5 s, así que el límite puede ser mucho mayor o aplicarse sólo a fallos de caché. | `controllers/portal.py:18-19, 218-243`, `static/src/portal/site.js:10` |
| PORT-02 | Media | "Te faltan N paradas" supone que el bus recorre las paradas en orden ascendente; un bus de regreso se cuenta como si viniera. | `static/src/portal/site.js:126-146`, `controllers/portal.py:121-137` |
| PORT-03 | Baja | El docstring de `portal_i18n.py` dice que no hay kichwa, pero existe el borrador `qu`. | `models/portal_i18n.py:1-5, 287` |

### 1.5 App de tableta

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| TAB-01 | Alta | Si el servidor responde `no_shift` (la oficina cerró el turno, el cron lo cerró por viejo o se revocó la tableta), la pantalla vuelve a *Elegir bus* pero **no detiene el GPS** ni borra sus credenciales: la tableta sigue enviando posiciones. | `apps/conductor-tablet/app/shift.tsx:94-98` |
| TAB-02 | Alta | *Terminar turno* falla si el servidor ya no tiene el turno (409) o no hay red: muestra "sin red" y el GPS sigue encendido; el chofer no puede cerrar. | `app/shift.tsx:117-131`, `src/state/session.ts:276-281` |
| TAB-03 | Media | Tras un SOS guardado sin red y luego entregado, la cabina sigue diciendo "SOS guardado" hasta que la oficina lo atiende: el estado local tiene prioridad sobre el del servidor. | `app/shift.tsx:72-82` |
| TAB-04 | Media | Los incidentes en cola se descartan ante cualquier error que no sea de red (409, 500): un SOS puede perderse sin aviso. Tampoco se conserva la hora real: el servidor usa la hora de entrega. | `src/state/session.ts:265-274`, `src/incidents/queue.ts:44-58` |
| TAB-05 | Media | `sendFix` no tiene tiempo límite: una conexión colgada bloquea la tarea en segundo plano y toda la cola. | `src/gps/runtime.ts:37-48` |
| TAB-06 | Media | Al terminar el turno se borra la cola de posiciones sin intentar enviarla; el máximo de 360 puntos (1 h a 10 s) no cuadra con la antigüedad máxima de 2 h. | `src/gps/tracker.ts:45-56`, `src/gps/queue.ts:10-11` |
| TAB-07 | Media | Dos ejecuciones simultáneas de la tarea leen y escriben la cola sin exclusión: puntos duplicados o perdidos. | `src/gps/queue.ts:56-85`, `src/gps/runtime.ts:50-88` |
| TAB-08 | Media | Mensajes de error engañosos: el login muestra "credenciales incorrectas" ante 429 o 500, e *Iniciar turno* muestra "conflicto" ante cualquier error que no sea `no_gps`. | `app/login.tsx:41-45`, `app/select.tsx:53-57` |
| TAB-09 | Baja | El bus y la ruta preseleccionados se calculan una sola vez al montar; si la lista llega después (arranque sin red), quedan vacíos. | `app/select.tsx:20-22` |
| TAB-10 | Baja | `LastSent.error` nunca se rellena: el diagnóstico no puede decir por qué no se envía (p. ej. Traccar rechaza el id). | `src/gps/runtime.ts:79-86` |
| TAB-11 | Baja | El texto de la notificación del servicio GPS está fijo en español, fuera del i18n. | `src/gps/tracker.ts:37-42` |

### 1.6 Operación, scripts y CI

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| OPS-01 | Crítica | `clean-azure-db.sh` borra las bases de producción sin pedir confirmación y después llama a métodos que **no existen** (`setup_server`, `setup_admin_user`, `disable_registration`): falla tras el borrado, deja Traccar sin configurar, `gps_url` vacío (BE-04) y descarta la contraseña de Traccar que genera. Además asume una base local cuando `.env.prod.example` propone Supabase. | `scripts/clean-azure-db.sh:15-58` |
| OPS-02 | Alta | CI no ejecuta la suite de Odoo ni el linter de la tableta; `flake8` sólo busca errores de sintaxis; usa Python 3.10 cuando la imagen tiene 3.9. | `.github/workflows/ci.yml` |
| OPS-03 | Media | Traccar va con `latest` en desarrollo y por defecto en producción (Ishikawa ya lo señala). | `docker-compose.yml:31`, `.env.prod.example:34` |
| OPS-04 | Baja | Mailpit está en el compose de desarrollo, pero Odoo no está configurado para usarlo y el sistema no envía correo. | `docker-compose.yml:44-49`, `README.md` |

### 1.7 Documentación

| ID | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| DOC-01 | Media | README: la tabla de modelos cita `bus.activity.report` (no existe) y omite `bus.shift`, `bus.incident`, `bus.run`, `bus.complaint`, `bus.driver.token`, `bus.push.subscription` y `bus.route.record`; no explica el menú *Choferes* ni la credencial QR; dice OpenStreetMap (son teselas de CARTO); describe Mailpit como buzón de correos. | `README.md:48-58, 100-104` |
| DOC-02 | Media | Conteos de tests desactualizados y contradictorios (216, 232, 247); hay 213 métodos de prueba. Cifras de calidad y del guion de defensa del 28-oct. | `docs/PLAN-APP-CHOFER.md:42, 63`, `docs/PLAN.md:228`, `docs/calidad/04-*.md`, `docs/GUION_DEFENSA.md` |
| DOC-03 | Media | La guía del chofer promete cosas que el sistema no cumple hoy (SEC-06, TAB-01) y no tiene una fila para "GPS esperando" por falta de `gps_url` ni explica qué pasa con la credencial al revocar la tableta. | `docs/GUIA-CHOFER.md` |
| DOC-04 | Baja | Referencias a líneas que ya no existen (`traccar_api.py:84-85`). | `docs/PLAN-APP-CHOFER.md:162` |
| DOC-05 | Media | `PRODUCCION.md` no menciona `clean-azure-db.sh` ni `bootstrap-traccar.sh`, ni cómo rotar secretos, ni deja claro si la base es local o Supabase. | `docs/PRODUCCION.md` |
| DOC-06 | Media | El registro de defectos y la autoevaluación ISO no recogen estos hallazgos; falta la entrada de la bitácora. | `docs/calidad/05-*.md`, `docs/calidad/09-*.md`, `docs/BITACORA.md` |

## 2. Decisiones del equipo

1. **SEC-03**: rotar ya la contraseña del administrador (obligatorio). ¿Reescribir también el historial de Git para quitarla? Hacerlo obliga a `push --force` y a que todos vuelvan a clonar; sin rotar la contraseña no sirve de nada. **Decidido (2026-11-02): quitarla del historial.** Hecho en local en `main` y `develop` (el script ahora pide `ADMIN_PASSWORD`); falta el `push --force` de ambas ramas, que hace el equipo.
2. **SEC-05**: ¿choferes como usuarios de portal (sin acceso a `/web`) o internos con el backend bloqueado? Recomendado: portal; la API ya usa `sudo()` donde hace falta. **Decidido (2026-11-02): portal.** Hecho en la fase 1, con migración `16.0.1.2.0` para los choferes existentes.
3. **SEC-06**: posiciones de un bus sin turno: ¿descartarlas o guardarlas marcadas y fuera del mapa? Recomendado: descartarlas, con un ajuste para desactivarlo en pruebas con `curl`. **Decidido (2026-11-02): descartarlas.**
4. **TAB-02**: terminar turno sin red: ¿se apaga el GPS y se encola el cierre, o se exige red? Recomendado: apagar el GPS, encolar el cierre y que el cron de turnos viejos haga de red de seguridad. **Decidido (2026-11-02): la opción recomendada.**

## 3. Plan de implementación

Cada fase es una rama desde `develop` que se integra con `merge --no-ff` cuando pasa sus verificaciones. Cada viñeta es al menos un commit, con su prueba en el mismo commit o en el siguiente `test:`. Las fases 1 a 3 van primero porque son seguridad y flujos de operación; las demás pueden ir en paralelo.

### Fase 0. Acciones fuera del código (hoy)
- Rotar la contraseña del admin de Odoo de producción y revisar accesos recientes (SEC-03).
- Decidir los puntos de la sección 2.

### Fase 1. `fix/credenciales-chofer` (SEC-01, SEC-02, SEC-04, SEC-05, SEC-13, BE-15) — hecha
- `fix: require managers to issue or revoke driver badges`: comprobar `group_bus_manager` en ambos métodos.
- `fix: keep the badge link and QR readable only by managers`: `groups='bus_tracking.group_bus_manager'` en `driver_badge_qr`/`driver_badge_link`; mejor aún, no guardar el enlace: generarlo al emitir y mostrarlo una sola vez en un asistente.
- `fix: stop badge tokens from working as session tokens`: `_user_for` excluye `badge_qr`; `login_badge` sólo acepta credenciales; el logout nunca revoca la credencial.
- `fix: revoke the badge image together with its token`.
- `chore: replace the real Supabase project id with placeholders`.
- Pruebas nuevas (`test_driver_badge.py`): un chofer o un usuario normal no puede emitir, revocar ni leer credenciales ajenas; una credencial no abre `/driver/me`; `login_badge` rechaza un token de sesión; el logout con sesión no toca la credencial.

### Fase 2. `fix/ingesta-y-avisos` (BE-01, BE-02, BE-09, BE-11, SEC-06, SEC-09, SEC-10) — hecha
- `fix: ignore concurrent duplicate positions instead of failing`: `INSERT ... ON CONFLICT DO NOTHING` o `savepoint` + `IntegrityError`; el webhook responde 200 ante duplicados.
- `fix: keep the push queue moving when a push service is unreachable`: capturar `requests.RequestException` por suscripción y marcar `notified` por registro.
- `fix: report non-JSON answers from Traccar as a clear error`.
- `fix: parse numeric settings safely` (helper común para `int` con valor por defecto).
- `feat: drop positions from buses without an active shift` (según decisión 3, con parámetro).
- `fix: bound the track request to 24 hours and validate its arguments`.
- `refactor: deprecate the webhook secret in the query string` (log de aviso; quitarlo en la versión siguiente).
- Pruebas: dos inserciones simultáneas no dan 500 (simular el `IntegrityError` con `patch`); un `ConnectionError` no repite avisos ya enviados; cron sobrevive a HTML; parámetro `"abc"` usa el valor por defecto; posición sin turno descartada; `hours=10**9` y `vehicle_id="x"` dan error controlado.

### Fase 3. `fix/turno-tableta` (BE-03, BE-04, BE-10, TAB-01 a TAB-10, SEC-07, SEC-08, SEC-14) — hecha
Backend:
- `fix: compute the next stop from the current trip, not the whole shift`: usar el `bus.run` en curso (o la última llegada a un extremo) como inicio y respetar el sentido del regreso.
- `fix: refuse to start a shift when the gps address is not configured` (409 `no_gps_url`) y validar el formato en Ajustes; `dev_seed.py` configura `gps_url`.
- `feat: tell the tablet which buses have gps and refuse archived routes`.
- `feat: accept the time an incident was reported` (`reported_at` opcional, validado y acotado).

Tableta:
- `fix: stop the gps when the server closed the shift` (`Session.dropShift()` usado por `shift.tsx`).
- `fix: let the driver end a shift the server already closed or without signal` (según decisión 4).
- `fix: show the sos as delivered once the server has it`.
- `fix: keep queued incidents on server errors and send their real time`.
- `fix: give up on a stuck gps request after ten seconds`.
- `fix: try to send the saved positions before clearing them at the end of a shift` y alinear límites de la cola.
- `fix: serialize gps queue updates` (cerrojo en memoria + escritura atómica).
- `fix: explain rate limits and server errors on sign-in and shift start`.
- `fix: preselect the bus and route once the list arrives`.
- `feat: record why the last gps send failed` y mostrarlo en *Diagnóstico GPS*.
- `fix: keep the session token only in the secure store` (migración: leer `AsyncStorage` una vez, mover y borrar).
- `fix: only accept https servers and confirm a server change from a qr`.
- `chore: drop the microphone permission and duplicated permissions`.
- Pruebas: `session.test.ts` (no_shift detiene GPS, fin de turno con 409, credencial no se guarda como sesión, cambio de servidor pide https); `runtime.test.ts` nuevo (timeout, error guardado, cola con ejecuciones concurrentes); `secureStore.test.ts` (no escribe en `AsyncStorage`); `progress.test.ts` (segunda vuelta). Backend: `test_driver_shift.py` (segunda vuelta, `no_gps_url`, ruta archivada, `reported_at`).

### Fase 4. `fix/portal-y-panel` (PORT-01, PORT-02, PAN-01 a PAN-05, BE-05, BE-14, SEC-11, SEC-12) — hecha (PAN-01: Odoo 16 ya recarga la ficha al cerrar el selector; sólo faltaba traducirlo)
- `fix: let a whole campus follow a line without hitting the rate limit` (límite sólo en fallos de caché o subirlo a unas 600/min; medirlo con `qa/auditoria.py`).
- `fix: forget idle addresses in the rate limiter`.
- `feat: count stops in the direction the bus travels` (enviar el sentido del viaje en el feed, sin exponer ids).
- `fix: keep an unattended sos in the attention queue until someone sees it`.
- `fix: make bus names unique` (o identificar por índice opaco en el feed).
- `fix: translate the stop picker and reload the route after saving`.
- `fix: redraw the live map when stops or tracks change`.
- `fix: report failures when marking as seen or loading a track`.
- `fix: keep filtered markers out of clicks and the tab order`.
- `fix: update the bus marker title on the public map`.
- `refactor: read the tile address from one setting` y documentar CARTO y su atribución.
- Pruebas: `test_portal.py` (20 consultas seguidas desde una IP con caché válida no dan 429; sentido del viaje), `test_driver_staff.py` (SOS de 30 h sigue en la cola), restricción de nombre único; recorrido de teclado actualizado en `docs/calidad/12-validacion-ux.md`.

### Fase 5. `fix/validaciones-modelo` (BE-06, BE-07, BE-08, BE-13) — hecha (caché del trazado: 1,53 s → 0,76 s por 1.000 posiciones con un trazado de 1.500 puntos)
- `fix: validate stop coordinates, radius and route colour in the model`.
- `fix: refuse a recording period that ends before it starts`.
- `perf: cache the measured route line per route` (invalidar con `write_date`).
- `fix: ask to wait instead of silently dropping a very fast complaint`.
- Pruebas para cada restricción; prueba de rendimiento simple (1.000 posiciones con trazado de 1.500 puntos, comparar antes y después en la bitácora).

### Fase 6. `chore/traducciones` (BE-12, TAB-11, PORT-03)
- `refactor: write driver texts in English and translate them in es.po`.
- `chore: regenerate the pot and es.po from the module` (quitar los seis modelos borrados, completar las 24 vacías).
- `fix: translate the gps service notification`.
- `docs: describe the kichwa draft correctly`.
- Prueba: script de `qa/` que falla si `es.po` tiene entradas vacías o referencias a modelos inexistentes.

### Fase 7. `ci/pipeline-completo` y `chore/scripts-produccion` (OPS-01 a OPS-04, SEC-05)
- `ci: run the odoo test suite against postgres` (servicio `postgres:15` + contenedor `odoo:16.0` con `pywebpush`).
- `ci: lint the tablet app` y `ci: run flake8 with the full rule set on python 3.9` (corregir lo que salga en commits `style:` aparte).
- `fix: rewrite the azure reset script on top of init-prod` con confirmación explícita, sin secretos y guardando la contraseña de Traccar generada; o eliminarlo si no se usa.
- `chore: pin the traccar image`.
- `chore: remove mailpit from the dev stack` (o configurarlo de verdad).
- `feat: create drivers as portal users` (según decisión 2) con migración para los existentes y prueba de que un chofer no entra a `/web`.

### Fase 8. `docs/actualizacion-auditoria` (DOC-01 a DOC-06)
- README: modelos reales, menú *Choferes* y credencial QR, teselas CARTO, quitar Mailpit, `gps_url` como paso obligatorio de la puesta en marcha.
- `GUIA-CHOFER.md`: qué pasa al revocar la tableta, fila "GPS esperando: el administrador no configuró la dirección del GPS".
- `PRODUCCION.md`: scripts de reinicio y bootstrap, rotación de secretos, base local o Supabase.
- `PLAN-APP-CHOFER.md` y `PLAN.md`: conteos reales y referencias de líneas vigentes.
- `docs/calidad/`: nuevos defectos DEF-011 en adelante (uno por hallazgo Crítico/Alto, con causa raíz), regenerar métricas con `qa/ejecutar_todo.sh`, actualizar `09-cumplimiento-iso.md` (seguridad: confidencialidad y autenticidad) y `GUION_DEFENSA.md`.
- `BITACORA.md`: entrada de esta auditoría y de cada fase cerrada.

### Fase 9. Cierre
- Suite completa de Odoo en base limpia, `jest`, `tsc`, `lint`, `qa/ejecutar_todo.sh`, `qa/accesibilidad.py`, capturas.
- Prueba en una tableta real: turno completo de dos vueltas, corte de red, SOS sin señal, cierre del turno desde la oficina.
- `develop` → `main` con `merge --no-ff` cuando todo esté en verde.

## 4. Matriz de pruebas nuevas

| Archivo | Casos nuevos | Hallazgos |
|---|---|---|
| `tests/test_driver_badge.py` | permisos de emisión/revocación, lectura de campos, credencial ≠ sesión, `login_badge` sólo credenciales | SEC-01, SEC-02, SEC-04, BE-15 |
| `tests/test_ingest.py`, `tests/test_http.py` | duplicado concurrente, posición sin turno, `track` acotado, secreto por URL | BE-01, SEC-06, SEC-09, SEC-10 |
| `tests/test_push.py`, `tests/test_alerts.py` | error de red por suscripción, `notified` por registro, parámetros no numéricos | BE-02, BE-11 |
| `tests/test_traccar_sync.py` | respuesta HTML | BE-09 |
| `tests/test_driver_shift.py` | segunda vuelta, `no_gps_url`, buses sin GPS, ruta archivada, `reported_at` | BE-03, BE-04, BE-10, TAB-04 |
| `tests/test_driver_staff.py` | SOS de más de 24 h | BE-05 |
| `tests/test_portal.py`, `tests/test_complaints.py` | NAT con caché, sentido del viaje, limpieza del limitador, queja rápida | PORT-01, PORT-02, SEC-11, BE-13 |
| `tests/test_stop_picker.py`, `tests/test_track.py` | restricciones del modelo, periodo invertido | BE-06, BE-07 |
| `src/state/session.test.ts` | `no_shift`, fin de turno, servidor https, credencial | TAB-01, TAB-02, SEC-04, SEC-08 |
| `src/gps/runtime.test.ts` (nuevo) | timeout, error guardado, concurrencia, vaciado al terminar | TAB-05, TAB-06, TAB-07, TAB-10 |
| `src/state/secureStore.test.ts` | sin copia en `AsyncStorage`, migración | SEC-07 |
| `src/shift/progress.test.ts` | prioridad del SOS del servidor | TAB-03 |
| `qa/` (nuevo chequeo de i18n) | entradas vacías y modelos inexistentes | BE-12 |
