# Registro de defectos y análisis de causa raíz

Formato del taller de la Unidad 2: bitácora de incidencias y evaluación de la causa raíz. Los defectos DEF-001 a DEF-007 salen de `docs/academico/BITACORA.md` (se hallaron y cerraron al construir); DEF-008 a DEF-010 los halló la evaluación de calidad del 28-oct-2026 y DEF-011 a DEF-026 la auditoría integral del 2-nov-2026 (`docs/arquitectura/PLAN-AUDITORIA.md`, un defecto por hallazgo crítico o alto) y DEF-027 a DEF-034 la auditoría de diseño móvil del mismo día (`docs/arquitectura/PLAN-UI-MOVIL.md`). Generado por `qa/generar_docs.py` desde `qa/datos_calidad.py`.

Cada defecto se registra con tres campos separados: fallo observado, defecto localizado y causa de origen.

## 1. Bitácora de defectos

| ID | Fecha | Detectado por | Defecto | Ubicación | Estado |
|---|---|---|---|---|---|
| DEF-001 | 26-oct-2026 | Prueba manual con Traccar real | El webhook respondía 405 porque Traccar reenviaba con GET | docker-compose.yml | Cerrado |
| DEF-002 | 26-oct-2026 | Prueba de respaldo y restauración | El respaldo del filestore salía con 0 archivos y no avisaba | config/odoo.conf, scripts/backup.sh | Cerrado |
| DEF-003 | 26-oct-2026 | Revisión del log durante la prueba de punta a punta | El secreto del webhook aparecía completo en el log de Odoo | controllers/main.py | Cerrado |
| DEF-004 | 26-oct-2026 | Arranque de Odoo tras instalar pywebpush | Odoo dejó de arrancar (module lib has no attribute GEN_EMAIL) | docker/odoo/Dockerfile | Cerrado |
| DEF-005 | 26-oct-2026 | Test del asistente de respuesta | El pasajero habría visto la etiqueta <br/> como texto | asistente de respuesta (retirado después) | Cerrado |
| DEF-006 | 27-oct-2026 | Suite de Odoo | Un bus sin ruta rompía el cálculo de desvío de ruta | models/bus_alert.py | Cerrado |
| DEF-007 | 26-oct-2026 | Revisión en el navegador | El navegador seguía mostrando un CSS viejo del portal | controllers/portal.py | Cerrado |
| DEF-008 | 28-oct-2026 | Suite en vivo (E7) y auditoría | Se guardan posiciones con latitud o longitud imposibles (p. ej. 95°) | models/bus_vehicle.py (_apply_position), models/bus_position.py | Cerrado |
| DEF-009 | 28-oct-2026 | Suite en vivo (E8) y auditoría | Una latitud no numérica produce HTTP 500 en el webhook | models/bus_vehicle.py, controllers/main.py | Cerrado |
| DEF-010 | 28-oct-2026 | Suite en vivo (E9) y auditoría | Una hora GPS inválida produce HTTP 500 en el webhook | models/utils.py (parse_traccar_dt), controllers/main.py | Cerrado |
| DEF-011 | 02-nov-2026 | Auditoría integral (SEC-01) | Cualquier usuario interno podía emitir o revocar la credencial QR de otro chofer por RPC | models/res_users.py | Cerrado |
| DEF-012 | 02-nov-2026 | Auditoría integral (SEC-02) | El enlace con el token de la credencial QR se guardaba en claro y lo leía cualquier usuario interno | models/res_users.py | Cerrado |
| DEF-013 | 02-nov-2026 | Auditoría integral (SEC-03) | La contraseña del admin de producción estaba escrita en un script del repositorio público | scripts/clean-azure-db.sh | Cerrado |
| DEF-014 | 02-nov-2026 | Auditoría integral (OPS-01) | El script de reinicio borraba producción sin confirmar y luego fallaba por llamar métodos inexistentes | scripts/clean-azure-db.sh | Cerrado |
| DEF-015 | 02-nov-2026 | Auditoría integral (SEC-04) | La credencial QR servía como sesión y una sesión robada se renovaba para siempre por login_badge | models/bus_driver_token.py, controllers/driver_api.py | Cerrado |
| DEF-016 | 02-nov-2026 | Auditoría integral (SEC-05) | Los choferes eran usuarios internos y podían abrir el panel con la clave de la tableta | models/res_users.py | Cerrado |
| DEF-017 | 02-nov-2026 | Auditoría integral (SEC-06) | Odoo guardaba posiciones de buses sin turno abierto | models/bus_vehicle.py | Cerrado |
| DEF-018 | 02-nov-2026 | Auditoría integral (SEC-07) | La tableta copiaba el token de sesión en AsyncStorage, en texto plano | apps/conductor-tablet/src/state/secureStore.ts | Cerrado |
| DEF-019 | 02-nov-2026 | Auditoría integral (BE-01) | Webhook y cron con la misma posición a la vez: el webhook respondía 500 | models/bus_vehicle.py | Cerrado |
| DEF-020 | 02-nov-2026 | Auditoría integral (BE-02) | Un error de red del servicio push repetía los avisos cada minuto | models/bus_push.py, models/bus_alert.py, models/bus_incident.py | Cerrado |
| DEF-021 | 02-nov-2026 | Auditoría integral (BE-03) | Desde la segunda vuelta la tableta decía "sin próxima parada" | controllers/driver_api.py | Cerrado |
| DEF-022 | 02-nov-2026 | Auditoría integral (BE-04) | Sin dirección del GPS en Ajustes el turno empezaba pero el GPS nunca arrancaba | controllers/driver_api.py, scripts/dev_seed.py | Cerrado |
| DEF-023 | 02-nov-2026 | Auditoría integral (PORT-01) | Unos 10 pasajeros en la misma Wi-Fi recibían "demasiadas consultas" | controllers/portal.py | Cerrado |
| DEF-024 | 02-nov-2026 | Auditoría integral (TAB-01) | Cuando la oficina cerraba el turno, la tableta seguía enviando el GPS | apps/conductor-tablet/app/shift.tsx, src/state/session.ts | Cerrado |
| DEF-025 | 02-nov-2026 | Auditoría integral (TAB-02) | Sin red o con el turno ya cerrado, el chofer no podía terminar el turno | apps/conductor-tablet/src/state/session.ts | Cerrado |
| DEF-026 | 02-nov-2026 | Auditoría integral (OPS-02) | El CI no corría la suite de Odoo ni el linter de la tableta | .github/workflows/ci.yml | Cerrado |
| DEF-027 | 02-nov-2026 | Auditoría de diseño móvil (P1) | El SOS y las alertas abiertas quedaban fuera de la vista en horizontal y en Android | apps/conductor-tablet/app/shift.tsx | Cerrado |
| DEF-028 | 02-nov-2026 | Auditoría de diseño móvil (P2) | El detalle de las alertas salía en el idioma del usuario de Odoo y no en el de la app | controllers/driver_api.py, models/res_users.py | Cerrado |
| DEF-029 | 02-nov-2026 | Auditoría de diseño móvil (P2) | Ninguna acción que confirma algo daba respuesta háptica, aunque DISENO.md la prometía | apps/conductor-tablet/src/ui/cabin.tsx, app/shift.tsx, app/incident.tsx | Cerrado |
| DEF-030 | 02-nov-2026 | Auditoría de diseño móvil (P2) | El relleno del SOS animaba en el hilo de JS y volvía de golpe al soltar | apps/conductor-tablet/src/ui/cabin.tsx | Cerrado |
| DEF-031 | 02-nov-2026 | Auditoría de diseño móvil (P2) | El código de la línea llevaba texto blanco fijo sobre el color que elige la oficina (ilegible en amarillo o blanco) | apps/conductor-tablet/app/shift.tsx, app/select.tsx | Cerrado |
| DEF-032 | 02-nov-2026 | Auditoría de diseño móvil (P2) | Había valores de espaciado fuera de la cuadrícula de 4 px y sin tokens | apps/conductor-tablet/app/*.tsx, src/ui/*.tsx | Cerrado |
| DEF-033 | 02-nov-2026 | Auditoría de diseño móvil (P2) | Con la fuente del sistema al 130 % o más el turno se desbordaba y el SOS y Terminar turno quedaban inalcanzables | apps/conductor-tablet/app/shift.tsx, select.tsx, incident.tsx, gps.tsx | Cerrado |
| DEF-034 | 02-nov-2026 | Auditoría de diseño móvil (P2) | La selección de bus y línea quedaba en blanco sin buses, sin líneas o con todos los buses en uso | apps/conductor-tablet/app/select.tsx | Cerrado |
| DEF-035 | 04-nov-2026 | Diagnóstico en producción (Traccar/Odoo) | Traccar no reenviaba posiciones al webhook de Odoo por faltar FORWARD_ENABLE | docker-compose.yml, docker-compose.prod.yml | Cerrado |
| DEF-036 | 04-nov-2026 | Diagnóstico en producción (logs de Odoo) | Saturación del pool de conexiones PostgreSQL en Odoo (PoolError: The Connection Pool Is Full) | config/odoo.prod.conf (db_maxconn) | Cerrado |
| DEF-037 | 04-nov-2026 | Prueba en dispositivo móvil (pantalla Estado del GPS) | Dispositivo en Traccar mostraba guion (-) aun con credenciales guardadas en el almacenamiento | apps/conductor-tablet/app/gps.tsx | Cerrado |
| DEF-038 | 04-nov-2026 | Prueba de campo en iOS (iPhone quieto) | El iPhone dejaba de transmitir ubicación por GPS al permanecer detenido o estático | apps/conductor-tablet/src/gps/tracker.ts, app.json | Cerrado |

Resumen: 38 registrados, 38 cerrados (100 %), 0 abiertos. Densidad: 13,2 defectos por KLOC (2,871 KLOC de Python sin pruebas).

## 2. Análisis de causa raíz e impacto

### DEF-001: El webhook respondía 405 porque Traccar reenviaba con GET

- **Causa raíz:** Traccar 6 renombró la clave de reenvío (forward.json pasó a forward.type) y el proyecto asumía la versión anterior; no había prueba contra la versión vigente.
- **Categoría:** Configuración
- **Prueba que lo protege:** F12 y test_http (webhook con cabecera); probado con Traccar real

### DEF-002: El respaldo del filestore salía con 0 archivos y no avisaba

- **Causa raíz:** La configuración de producción sustituía el archivo de la imagen y no definía data_dir; el script no comprobaba que hubiera archivos.
- **Categoría:** Configuración
- **Prueba que lo protege:** Respaldo y restauración repetidos de principio a fin (bitácora, 4.ª sesión)

### DEF-003: El secreto del webhook aparecía completo en el log de Odoo

- **Causa raíz:** El secreto viajaba en la URL y el servidor registra las URL; se priorizó la compatibilidad y no la confidencialidad.
- **Categoría:** Seguridad
- **Prueba que lo protege:** F1 y F12; test_webhook_accepts_secret_in_header; 0 apariciones del secreto en el log

### DEF-004: Odoo dejó de arrancar (module lib has no attribute GEN_EMAIL)

- **Causa raíz:** pip instaló la última cryptography, incompatible con el pyOpenSSL de la imagen; las dependencias no tenían versión fijada.
- **Categoría:** Configuración
- **Prueba que lo protege:** Imagen reconstruida; test_push (cifrado y firma)

### DEF-005: El pasajero habría visto la etiqueta <br/> como texto

- **Causa raíz:** html_escape devuelve Markup y .replace sobre Markup escapa el <br/> nuevo.
- **Categoría:** Lógica
- **Prueba que lo protege:** Función retirada en la simplificación del 27-oct

### DEF-006: Un bus sin ruta rompía el cálculo de desvío de ruta

- **Causa raíz:** La regla asumía que todo bus tiene ruta y ningún test cubría el caso sin ruta.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_simple.TestOffRoute

### DEF-007: El navegador seguía mostrando un CSS viejo del portal

- **Causa raíz:** Odoo sirve los estáticos con caché larga y la URL no cambiaba al modificar el archivo.
- **Categoría:** Configuración
- **Prueba que lo protege:** test_public_assets_are_versioned_so_browsers_never_keep_stale_copies

### DEF-008: Se guardan posiciones con latitud o longitud imposibles (p. ej. 95°)

- **Causa raíz:** Los campos float no tienen restricción de rango y _apply_position no valida lo que recibe; ninguna prueba enviaba coordenadas fuera de rango.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E7; test_webhook_rejects_out_of_range_latitude y test_out_of_range_coordinates_raise_validation_error

### DEF-009: Una latitud no numérica produce HTTP 500 en el webhook

- **Causa raíz:** El valor llega sin convertir al ORM, que lanza una excepción no controlada.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E8; test_webhook_rejects_non_numeric_latitude y test_non_numeric_coordinates_raise_validation_error

### DEF-010: Una hora GPS inválida produce HTTP 500 en el webhook

- **Causa raíz:** parse_traccar_dt llama a isoparse sin capturar el error de formato.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E9; test_webhook_rejects_invalid_fixtime y test_invalid_fixtime_raises_validation_error

### DEF-011: Cualquier usuario interno podía emitir o revocar la credencial QR de otro chofer por RPC

- **Causa raíz:** Se protegió el botón en la vista y no el método; sudo() saltaba los permisos.
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_only_managers_issue_or_revoke_badges

### DEF-012: El enlace con el token de la credencial QR se guardaba en claro y lo leía cualquier usuario interno

- **Causa raíz:** Los campos no tenían groups; se guardó el enlace para mostrarlo sin pensar que es una contraseña.
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_only_managers_read_the_badge_link

### DEF-013: La contraseña del admin de producción estaba escrita en un script del repositorio público

- **Causa raíz:** Un script de emergencia se versionó con el secreto en vez de leerlo de .env.prod; no hay revisión de secretos antes del commit.
- **Categoría:** Seguridad
- **Prueba que lo protege:** Contraseña de producción rotada (confirmado por el responsable el 04-nov-2026), script reescrito sin secretos y gitleaks en el CI; el historial público conserva la clave anterior, ya inservible

### DEF-014: El script de reinicio borraba producción sin confirmar y luego fallaba por llamar métodos inexistentes

- **Causa raíz:** Se escribió a mano sin reutilizar init-prod.sh ni probarlo en un servidor de prueba.
- **Categoría:** Configuración
- **Prueba que lo protege:** scripts/reset-prod.sh (confirmación, respaldo previo, init-prod.sh)

### DEF-015: La credencial QR servía como sesión y una sesión robada se renovaba para siempre por login_badge

- **Causa raíz:** Credencial y sesión compartían tabla y la búsqueda no filtraba el tipo; el respaldo para servidores viejos aceptaba cualquier token.
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_a_badge_is_not_a_session, test_login_badge_rejects_a_session_token

### DEF-016: Los choferes eran usuarios internos y podían abrir el panel con la clave de la tableta

- **Causa raíz:** Odoo 16 no autenticaba un usuario sin tipo y se eligió el tipo interno en vez del de portal.
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_drivers_from_the_menu_are_portal_users; migración 16.0.1.2.0

### DEF-017: Odoo guardaba posiciones de buses sin turno abierto

- **Causa raíz:** La regla "posición sólo con turno" se cumplía sólo en la tableta, no en el servidor.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_positions_need_an_open_shift, test_cron_skips_buses_without_a_shift

### DEF-018: La tableta copiaba el token de sesión en AsyncStorage, en texto plano

- **Causa raíz:** Un respaldo para teclados con fallos de keystore se dejó activo siempre.
- **Categoría:** Seguridad
- **Prueba que lo protege:** secureStore.test.ts (sin copia en AsyncStorage, migración)

### DEF-019: Webhook y cron con la misma posición a la vez: el webhook respondía 500

- **Causa raíz:** Se comprobaba el duplicado con una consulta y luego se insertaba, sin contemplar la carrera.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_a_concurrent_duplicate_is_skipped_without_error

### DEF-020: Un error de red del servicio push repetía los avisos cada minuto

- **Causa raíz:** Sólo se capturaba WebPushException; el lote se marcaba al final.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_a_network_error_does_not_stop_the_queue_nor_repeat_it

### DEF-021: Desde la segunda vuelta la tableta decía "sin próxima parada"

- **Causa raíz:** La próxima parada se calculaba desde el inicio del turno, no del viaje; el regreso no se modeló.
- **Categoría:** Lógica
- **Prueba que lo protege:** TestTripProgress (cuatro casos), progress.test.ts

### DEF-022: Sin dirección del GPS en Ajustes el turno empezaba pero el GPS nunca arrancaba

- **Causa raíz:** Un parámetro obligatorio se trataba como opcional y nadie lo configuraba en desarrollo.
- **Categoría:** Configuración
- **Prueba que lo protege:** test_start_needs_the_gps_address

### DEF-023: Unos 10 pasajeros en la misma Wi-Fi recibían "demasiadas consultas"

- **Causa raíz:** El límite por IP contaba también las respuestas en caché; no se midió el caso de NAT.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_a_campus_behind_one_address_is_served_from_the_cache

### DEF-024: Cuando la oficina cerraba el turno, la tableta seguía enviando el GPS

- **Causa raíz:** La pantalla volvía a Elegir bus sin apagar el servicio de fondo.
- **Categoría:** Lógica
- **Prueba que lo protege:** session.test.ts: a shift closed by the office stops the gps

### DEF-025: Sin red o con el turno ya cerrado, el chofer no podía terminar el turno

- **Causa raíz:** El fin de turno dependía de la respuesta del servidor para apagar el GPS.
- **Categoría:** Lógica
- **Prueba que lo protege:** session.test.ts: ending without signal / a shift the server already closed

### DEF-026: El CI no corría la suite de Odoo ni el linter de la tableta

- **Causa raíz:** Se configuró sólo una revisión de sintaxis; los conteos de pruebas de la documentación no se verificaban.
- **Categoría:** Configuración
- **Prueba que lo protege:** Job odoo-tests y lint de la tableta en el CI

### DEF-027: El SOS y las alertas abiertas quedaban fuera de la vista en horizontal y en Android

- **Causa raíz:** Los avisos vivían dentro del bloque que hace scroll y se medían solo con datos de ejemplo cortos.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** notices.test.ts y capturas del escenario de peor caso (qa/capturas_movil.py)

### DEF-028: El detalle de las alertas salía en el idioma del usuario de Odoo y no en el de la app

- **Causa raíz:** La API traducía con el idioma del usuario y la app no enviaba el suyo.
- **Categoría:** Lógica
- **Prueba que lo protege:** TestOdooLanguagePick y test_state_accepts_the_app_language_and_ignores_nonsense

### DEF-029: Ninguna acción que confirma algo daba respuesta háptica, aunque DISENO.md la prometía

- **Causa raíz:** La promesa del documento no tenía una tarea ni una prueba que la cubriera.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** haptics.test.ts (la sensación se juzga en un dispositivo real)

### DEF-030: El relleno del SOS animaba en el hilo de JS y volvía de golpe al soltar

- **Causa raíz:** Se animó el ancho con el driver de JS, sin una lógica de mantener probada aparte.
- **Categoría:** Lógica
- **Prueba que lo protege:** hold.test.ts y prueba en el emulador (mantener 1,1 s no dispara)

### DEF-031: El código de la línea llevaba texto blanco fijo sobre el color que elige la oficina (ilegible en amarillo o blanco)

- **Causa raíz:** Se dio por hecho que el color de la línea sería siempre oscuro.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** contrast.test.ts y qa/contraste.py (chips de línea)

### DEF-032: Había valores de espaciado fuera de la cuadrícula de 4 px y sin tokens

- **Causa raíz:** Cada pantalla escribía sus números a ojo y nada lo comprobaba.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** spacing.test.ts

### DEF-033: Con la fuente del sistema al 130 % o más el turno se desbordaba y el SOS y Terminar turno quedaban inalcanzables

- **Causa raíz:** Las pantallas se diseñaron para encajar en una vista y solo se probaron con el tamaño de letra por defecto.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** layout.test.ts y qa/capturas_android.py con font_scale 1,3 y 2,0

### DEF-034: La selección de bus y línea quedaba en blanco sin buses, sin líneas o con todos los buses en uso

- **Causa raíz:** No se pensó el estado vacío ni el caso de flota ocupada.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** Capturas de los escenarios empty y busy de qa/capturas_movil.py

### DEF-035: Traccar no reenviaba posiciones al webhook de Odoo por faltar FORWARD_ENABLE

- **Causa raíz:** Se asumió que FORWARD_TYPE=json reemplazaba a FORWARD_ENABLE en Traccar 6, pero forward.enable es obligatorio para inicializar el reenviador de posiciones.
- **Categoría:** Configuración
- **Prueba que lo protege:** Comprobación con curl hacia Traccar y verificación de ingesta de posiciones en Odoo y /bus_tracking/health en 200 OK

### DEF-036: Saturación del pool de conexiones PostgreSQL en Odoo (PoolError: The Connection Pool Is Full)

- **Causa raíz:** El límite db_maxconn=3 era insuficiente para soportar peticiones web concurrentes, cron y webhook en Supabase.
- **Categoría:** Configuración
- **Prueba que lo protege:** Ajuste de db_maxconn=10 en odoo.prod.conf y verificación de consultas concurrentes sin error

### DEF-037: Dispositivo en Traccar mostraba guion (-) aun con credenciales guardadas en el almacenamiento

- **Causa raíz:** La vista leía session.snapshot.gps (en memoria) en vez de leer de forma asíncrona gpsStore del almacenamiento seguro.
- **Categoría:** Lógica
- **Prueba que lo protege:** Carga de uniqueId desde gpsStore en loadFacts() y tsc --noEmit PASS

### DEF-038: El iPhone dejaba de transmitir ubicación por GPS al permanecer detenido o estático

- **Causa raíz:** Apple CoreLocation ignora timeInterval (solo Android) y entra en reposo si no hay desplazamiento; además deferredUpdatesInterval retrasaba eventos hasta detectar movimiento.
- **Categoría:** Lógica
- **Prueba que lo protege:** Implementación de Stationary Heartbeat periódico (10s), disparo inmediato al iniciar turno y eliminación de deferredUpdatesInterval; jest PASS (149 tests) y expo lint PASS

## 3. Qué falta para cerrar los abiertos

1. DEF-013: hacer `git push --force-with-lease origin main develop` con el historial ya reescrito, pedir a todos que vuelvan a clonar y **cambiar la contraseña del admin** en el servidor (quien vio el commit viejo la conoce).
2. Agregar una revisión de secretos antes de cada commit (por ejemplo `gitleaks` en el CI) para que no se repita.
