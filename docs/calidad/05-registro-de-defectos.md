# Registro de defectos y análisis de causa raíz

Formato del taller de la Unidad 2: bitácora de incidencias y evaluación de la causa raíz. Los defectos DEF-001 a DEF-007 salen de `docs/academico/BITACORA.md` (se hallaron y cerraron al construir); DEF-008 a DEF-010 los halló la evaluación de calidad del 28-oct-2026 y DEF-011 a DEF-026 la auditoría integral del 2-nov-2026 (`docs/arquitectura/PLAN-AUDITORIA.md`, un defecto por hallazgo crítico o alto) y DEF-027 a DEF-034 la auditoría de diseño móvil del mismo día (`docs/arquitectura/PLAN-UI-MOVIL.md`); DEF-035 a DEF-038 salieron de las pruebas en producción y en el celular (4-nov) y DEF-039 a DEF-048 de la etapa que cubre la rúbrica del proyecto final: simulador, métricas, tablero, Grafana, Fleet y SonarQube (`docs/arquitectura/PLAN-RUBRICA.md`, 4 y 5-nov); DEF-049 y DEF-050 de la actualización en Azure con Fleet (5-nov) y DEF-051 a DEF-062 de la segunda auditoría integral del 17-nov-2026 (`docs/arquitectura/PLAN-AUDITORIA-2.md`, un defecto por hallazgo crítico o medio que es un fallo; su corrección está planificada en las fases 38 a 43). Generado por `qa/generar_docs.py` desde `qa/datos_calidad.py`.

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
| DEF-039 | 04-nov-2026 | Pruebas del simulador de recorridos (R4) | El segundo escenario simulado de un bus no producía recorrido: sus posiciones se descartaban | models/trip_simulator.py | Cerrado |
| DEF-040 | 04-nov-2026 | Pruebas de las métricas (R5) | La desviación promedio (T5) devolvía vacío cuando todos los recorridos iban exactos | models/bus_kpi.py | Cerrado |
| DEF-041 | 04-nov-2026 | Pruebas de las métricas (R5) | Un indicador calculado justo después de crear un recorrido no lo veía | models/bus_kpi.py | Cerrado |
| DEF-042 | 04-nov-2026 | Pruebas de calidad del sistema (R5) | El registro de posiciones rechazadas se caía con cargas raras (sin diccionario, campos de otro tipo) | models/bus_quality.py | Cerrado |
| DEF-043 | 04-nov-2026 | Prueba del tablero en el navegador (R6) | El tablero de Odoo se quedaba en «Cargando…» con un error del cliente | static/src/xml/dashboard.xml | Cerrado |
| DEF-044 | 04-nov-2026 | Prueba del tablero en el navegador (R6) | Las tarjetas del tablero salían apiladas y flotando sobre el título | static/src/css/dashboard.css | Cerrado |
| DEF-045 | 04-nov-2026 | Pruebas de las vistas SQL (R7) | El módulo no se instalaba: «relation bus_vehicle does not exist» | models/__init__.py, models/bus_kpi_views.py | Cerrado |
| DEF-046 | 04-nov-2026 | Prueba de Grafana en el navegador (R7) | Con un token de 5 minutos, Grafana se quedaba sin datos al vencer | models/bus_grafana.py, static/src/js/grafana.js | Cerrado |
| DEF-047 | 04-nov-2026 | Pruebas de la integración con Fleet (R8) | Los gestores de buses no veían los vehículos de Fleet | security/security.xml | Cerrado |
| DEF-048 | 05-nov-2026 | Análisis estático con SonarQube (R10) | 16 bugs: promesas sin manejar que perdían errores; un hash SHA-1; una función muerta con pytz; una comparación de NaN consigo mismo | apps/conductor-tablet, static/src/js, controllers/main.py, models/ | Cerrado |
| DEF-049 | 05-nov-2026 | Actualización del módulo en Azure | Fallo de serialización concurrente en PostgreSQL al actualizar vistas en producción | docker-compose.prod.yml (procedimiento) | Cerrado |
| DEF-050 | 05-nov-2026 | Actualización del módulo en Azure | Error de validación XML en Odoo por uso de atributo `@string` en selector XPath | views/bus_fleet_views.xml | Cerrado |
| DEF-051 | 17-nov-2026 | Segunda auditoría integral (X1) | XSS guardado en el portal público: el nombre de una parada se inserta como HTML en el tooltip del mapa | static/src/portal/portal_map.js, static/src/js/stop_picker.js | Cerrado |
| DEF-052 | 17-nov-2026 | Segunda auditoría integral (W1) | Un SOS guardado sin señal puede desaparecer de la cola de la tableta | apps/conductor-tablet/src/incidents/queue.ts | Cerrado |
| DEF-053 | 17-nov-2026 | Segunda auditoría integral (B1) | Las posiciones nunca se purgan en una instalación nueva | models/bus_position.py, scripts/init-prod.sh | Cerrado |
| DEF-054 | 17-nov-2026 | Segunda auditoría integral (B2) | La base de datos de producción no arranca tras un down y up del compose | docker-compose.prod.yml, .env.prod.example | Cerrado |
| DEF-055 | 17-nov-2026 | Segunda auditoría integral (B4) | El panel de Traccar es público y su dominio por defecto publica la IP del servidor | docker-compose.prod.yml, proxy/Caddyfile | Cerrado |
| DEF-056 | 17-nov-2026 | Segunda auditoría integral (B3) | El login del panel de Odoo no tiene límite de intentos ni segundo factor | proxy/Caddyfile, despliegue | Cerrado |
| DEF-057 | 17-nov-2026 | Segunda auditoría integral (N1) | Tras cada fin de turno se abre una falsa alerta «No signal» con push a los managers | models/bus_alert.py | Cerrado |
| DEF-058 | 17-nov-2026 | Segunda auditoría integral (X2) | Las posiciones guardadas sin señal se pierden al terminar el turno | apps/conductor-tablet/src/state/session.ts | Cerrado |
| DEF-059 | 17-nov-2026 | Segunda auditoría integral (W2) | Un incidente o SOS guardado sin señal se borra si el turno ya cerró | controllers/driver_api.py, apps/conductor-tablet/src/state/session.ts | Cerrado |
| DEF-060 | 17-nov-2026 | Segunda auditoría integral (Z1, inferido) | Un manager de buses que no es administrador de Odoo no puede crear ni editar choferes | views/bus_driver_views.xml, security/security.xml | Cerrado |
| DEF-061 | 17-nov-2026 | Segunda auditoría integral (Y1) | Al cambiar de servidor, la tableta envía el token del servidor anterior al nuevo | apps/conductor-tablet/src/state/session.ts, app/scan.tsx | Cerrado |
| DEF-062 | 17-nov-2026 | Segunda auditoría integral (Y3) | La dirección del GPS acepta http y el identificador del bus viajaría sin cifrar | models/res_config_settings.py, apps/conductor-tablet/src/gps/osmand.ts | Cerrado |
| DEF-063 | 17-nov-2026 | Reporte del usuario tras el despliegue en Azure | Si el bus no pasa por la primera parada, la tableta la sigue mostrando como próxima y no avanza con las demás | models/bus_shift.py, models/bus_alert.py, models/bus_trip.py, models/bus_run.py | Cerrado |
| DEF-064 | 17-nov-2026 | Revisión del rediseño del portal | Esquinas cuadradas en la barra del mapa y en tarjetas del portal | static/src/css/live_map.css, static/src/portal/pages.css, static/src/css/brand.css | Cerrado |
| DEF-065 | 17-nov-2026 | Revisión del rediseño del portal | La portada salía en español aunque el visitante eligiera inglés o kichwa | views/landing_templates.xml, models/portal_i18n.py | Cerrado |
| DEF-066 | 17-nov-2026 | Revisión del rediseño del portal | La portada mostraba cifras y estados que ningún dato respalda | views/landing_templates.xml | Cerrado |
| DEF-067 | 17-nov-2026 | Revisión del rediseño del portal | Contraste insuficiente en el pie y en los números de los pasos; lista de cifras mal formada | static/src/portal/pages.css, views/landing_templates.xml | Cerrado |
| DEF-068 | 17-nov-2026 | Suite de pruebas de Odoo | Las pruebas HTTP fallaban al azar con «Session expired» (1 a 3 de 590 por corrida) | volumen /var/lib/odoo (entorno Docker) | Cerrado |
| DEF-069 | 17-nov-2026 | Reporte del usuario | Los gráficos del tablero de Odoo repetían su animación sin parar | static/src/js/dashboard.js | Cerrado |
| DEF-070 | 17-nov-2026 | Reporte del usuario | Mensajes de pasajeros: no aparecía la columna «Resuelta» | models/bus_complaint.py, views/bus_complaint_views.xml | Cerrado |
| DEF-071 | 17-nov-2026 | Retiro de Grafana | Al borrar un modelo, su tabla queda en la base | migrations/16.0.1.9.0/pre-migrate.py | Cerrado |
| DEF-072 | 17-nov-2026 | Reporte en PDF | Las traducciones nuevas del módulo no se cargaban | i18n/bus_tracking.pot | Cerrado |
| DEF-073 | 17-nov-2026 | Reporte en PDF | Descargar el reporte abría «Configure el diseño de sus documentos» en vez del PDF | models/bus_report.py | Cerrado |
| DEF-074 | 18-nov-2026 | Prueba del tablero de flota | Error del cliente de Odoo al salir del mapa en vivo mientras hace el primer zoom | static/src/js/live_map.js | Cerrado |
| DEF-075 | 18-nov-2026 | Reporte del usuario | El administrador no podía activar las notificaciones push en Windows: el botón se quedaba cargando | static/src/js/push_setup.js | Cerrado |
| DEF-076 | 18-nov-2026 | Despliegue de v1.0.0-rc1 en Azure | La migración 16.0.1.9.0 no pudo borrar el rol grafana_reader en Supabase | migrations/16.0.1.9.0/pre-migrate.py | Cerrado |
| DEF-077 | 18-nov-2026 | Verificación de v1.0.0-rc1 en Azure | Tras actualizar, los menús en español seguían diciendo Indicadores y Reportes | migrations/16.0.1.9.0/post-migrate.py | Cerrado |
| DEF-078 | 18-nov-2026 | Prueba de la tableta en el emulador de Android Studio | El emulador perdió el DNS y la app mostraba «Sin conexión» al iniciar sesión | Entorno (emulador Android 17) | Cerrado |
| DEF-079 | 18-nov-2026 | Prueba de la tableta en el emulador de Android Studio | Android muestra «la aplicación no responde» durante el turno aunque la app sigue funcionando | expo-task-manager (TaskJobService) en Android 17 | Abierto |
| DEF-080 | 18-nov-2026 | Uso en producción (gestor creando un recorrido) | Un gestor no podía crear recorridos, sincronizar un bus ni simular: «No puede crear Parada de un recorrido programado» | models/bus_trip.py, models/bus_vehicle.py, models/trip_simulator.py | Cerrado |
| DEF-081 | 20-nov-2026 | Revisión visual de la ficha de una multa | Los marcadores de inicio y fin del tramo daban 404 y salían como imagen rota | static/src/js/fine_evidence.js | Cerrado |
| DEF-082 | 20-nov-2026 | Revisión visual del kanban de multas | Los montos de las multas salían sin el símbolo $ | data/fine_types.xml | Cerrado |
| DEF-083 | 20-nov-2026 | Revisión visual de la ficha de una multa | El mapa de la evidencia ocupaba solo unos 300 px de ancho | static/src/css/fines.css | Cerrado |
| DEF-084 | 20-nov-2026 | Suite completa de las fases de multas | test_migration_grafana falla si otra base del mismo servidor aún da permisos al rol grafana_reader | tests/test_migration_grafana.py | Abierto |

Resumen: 84 registrados, 82 cerrados (98 %), 2 abiertos. Densidad: 16,7 defectos por KLOC (5,033 KLOC de Python sin pruebas).

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

### DEF-039: El segundo escenario simulado de un bus no producía recorrido: sus posiciones se descartaban

- **Causa raíz:** Se supuso que un bus podía recibir posiciones con fecha anterior a la última; el sistema ignora a propósito las más viejas que last_fix_time.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_trip_simulator.py: cada escenario se ejecuta tras otro con el bus reiniciado (_reset)

### DEF-040: La desviación promedio (T5) devolvía vacío cuando todos los recorridos iban exactos

- **Causa raíz:** Odoo no guarda un 0,0 que nunca se escribió: queda NULL en la base y AVG de NULL es NULL.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_kpi.py (T5 con recorridos exactos) y COALESCE en la consulta

### DEF-041: Un indicador calculado justo después de crear un recorrido no lo veía

- **Causa raíz:** Las consultas SQL leen las tablas y el ORM aún tenía los cambios en memoria sin escribir.
- **Categoría:** Lógica
- **Prueba que lo protege:** flush_all() antes de consultar; test_kpi.py crea y mide en la misma transacción

### DEF-042: El registro de posiciones rechazadas se caía con cargas raras (sin diccionario, campos de otro tipo)

- **Causa raíz:** Se asumió que lo rechazado siempre era un diccionario bien formado, justo lo contrario de lo que se rechaza.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** test_quality.py: test_garbage_does_not_break_the_log

### DEF-043: El tablero de Odoo se quedaba en «Cargando…» con un error del cliente

- **Causa raíz:** Las plantillas de OWL no conocen String(): la comparación se escribió como en JavaScript puro.
- **Categoría:** Lógica
- **Prueba que lo protege:** Captura con Playwright de las siete pestañas sin errores de consola (qa de esta etapa) y método routeSelected

### DEF-044: Las tarjetas del tablero salían apiladas y flotando sobre el título

- **Causa raíz:** Las clases del tablero (o_bus_card, o_bus_tab) ya las usaba el mapa en vivo con otra posición y otro estilo.
- **Categoría:** Accesibilidad y diseño
- **Prueba que lo protege:** Prefijo propio o_dash_* y capturas de escritorio y móvil

### DEF-045: El módulo no se instalaba: «relation bus_vehicle does not exist»

- **Causa raíz:** Las vistas kpi_* se creaban en el orden de carga de los modelos, antes de las tablas que leen.
- **Categoría:** Configuración
- **Prueba que lo protege:** TestKpiViews: el módulo se instala y las nueve vistas existen; el modelo se carga al final

### DEF-046: Con un token de 5 minutos, Grafana se quedaba sin datos al vencer

- **Causa raíz:** Se supuso que Grafana abría una sesión con el token; en realidad el navegador lo reenvía en cada consulta.
- **Categoría:** Seguridad
- **Prueba que lo protege:** qa/grafana_smoke.py y TestGrafanaAccess: duración configurable (480 min por defecto) con renovación al 90 %; el rol de solo lectura limita el daño

### DEF-047: Los gestores de buses no veían los vehículos de Fleet

- **Causa raíz:** El grupo «Officer» de Fleet solo ve el vehículo que conduce; hace falta el grupo «Administrator».
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_fleet.py: test_a_manager_can_open_the_fleet_menu_and_the_buses_stay_in_the_bus_menu

### DEF-048: 16 bugs: promesas sin manejar que perdían errores; un hash SHA-1; una función muerta con pytz; una comparación de NaN consigo mismo

- **Causa raíz:** Llamadas «dispara y olvida» sin .catch y código heredado sin revisión estática.
- **Categoría:** Lógica
- **Prueba que lo protege:** SonarQube: bugs 16 → 0, vulnerabilidades 12 → 0, deuda 107 → 0 min; 512 y 167 pruebas siguen en verde (docs/calidad/16-sonarqube.md)

### DEF-049: Fallo de serialización concurrente en PostgreSQL al actualizar vistas en producción

- **Causa raíz:** Se ejecutó `odoo -u bus_tracking` con el contenedor de producción en marcha y sus crons escribiendo (`SerializationFailure: concurrent update`).
- **Categoría:** Infraestructura y despliegue
- **Prueba que lo protege:** Procedimiento de actualización con parada limpia del servicio web antes de la inicialización de esquemas.

### DEF-050: Error de validación XML en Odoo por uso de atributo `@string` en selector XPath

- **Causa raíz:** Odoo 16 prohíbe `@string` en selectores XPath por ser un atributo traducible (`View inheritance may not use attribute 'string' as a selector`).
- **Categoría:** Interfaz y vistas
- **Prueba que lo protege:** Selector por elemento de campo hijo `//group[field[@name='driver_id']]` validado por `ir.ui.view._check_xml()`.

### DEF-051: XSS guardado en el portal público: el nombre de una parada se inserta como HTML en el tooltip del mapa

- **Causa raíz:** Leaflet trata como HTML el texto de bindTooltip y los nombres de paradas, que pueden venir de un GPX importado, no se escapan.
- **Categoría:** Seguridad
- **Prueba que lo protege:** qa/xss_tooltips.js (en el CI): el mapa público real en jsdom muestra como texto una parada llamada <img onerror>; el editor de paradas usa el mismo nodo de texto

### DEF-052: Un SOS guardado sin señal puede desaparecer de la cola de la tableta

- **Causa raíz:** La cola de incidentes no se serializa: un vaciado en curso guarda su copia antigua y sobrescribe el SOS recién añadido.
- **Categoría:** Lógica
- **Prueba que lo protege:** incidents/queue.test.ts y diagnostics/queue.test.ts: un SOS añadido durante un envío lento se conserva y dos vaciados a la vez envían una sola vez

### DEF-053: Las posiciones nunca se purgan en una instalación nueva

- **Causa raíz:** El cron usa 0 (conservar todo) si el parámetro no existe y Ajustes sólo guarda los 30 días al pulsar Guardar.
- **Categoría:** Configuración
- **Prueba que lo protege:** test_ingest.py: sin el parámetro se borran las posiciones de más de 30 días y se pide a Traccar borrar las suyas

### DEF-054: La base de datos de producción no arranca tras un down y up del compose

- **Causa raíz:** El servicio db está en el perfil local-db, que el ejemplo no activa; el ejemplo apunta a Supabase y los scripts asumen la base local.
- **Categoría:** Infraestructura y despliegue
- **Prueba que lo protege:** scripts/db.sh probado contra un Postgres con TLS (crear base, pg_dump y pg_restore); falta init-prod.sh completo contra un proyecto de Supabase (fase 46)

### DEF-055: El panel de Traccar es público y su dominio por defecto publica la IP del servidor

- **Causa raíz:** Se publicó el panel para la demostración y quedó como valor por defecto del compose.
- **Categoría:** Seguridad
- **Prueba que lo protege:** caddy adapt: el sitio del panel responde 404 fuera de TRACCAR_PANEL_ALLOW (por defecto 127.0.0.1/32) y el compose ya no lleva la IP

### DEF-056: El login del panel de Odoo no tiene límite de intentos ni segundo factor

- **Causa raíz:** Odoo Community no limita los intentos y el proxy tampoco; quedó como limitación conocida.
- **Categoría:** Seguridad
- **Prueba que lo protege:** TestPanelSignIn: la espera tras fallos se duplica hasta una hora y auth_totp está instalado (2FA opcional por usuario: imponerlo exige correo); test_driver_auth: otra dirección no bloquea al chofer

### DEF-057: Tras cada fin de turno se abre una falsa alerta «No signal» con push a los managers

- **Causa raíz:** La regla de sin señal no mira si el bus tiene turno; al cerrarlo Odoo descarta sus posiciones y la última hora queda fija.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_alerts: un bus sin turno no abre «No signal» y cerrar el turno cierra la alerta abierta

### DEF-058: Las posiciones guardadas sin señal se pierden al terminar el turno

- **Causa raíz:** La tableta cierra el turno en el servidor antes de vaciar la cola GPS, y Odoo descarta posiciones sin turno.
- **Categoría:** Lógica
- **Prueba que lo protege:** session.test.ts: endShift detiene el GPS (que envía la cola) antes de cerrar el turno en el servidor

### DEF-059: Un incidente o SOS guardado sin señal se borra si el turno ya cerró

- **Causa raíz:** El servidor exige turno activo (409 no_shift) y la tableta trata ese rechazo como definitivo.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_driver_shift: un SOS del turno llega hasta 2 h después del cierre y uno más viejo se rechaza; session.test.ts: sin sesión el incidente se conserva

### DEF-060: Un manager de buses que no es administrador de Odoo no puede crear ni editar choferes

- **Causa raíz:** El menú Choferes abre res.users, que exige base.group_erp_manager; las pruebas usan admin.
- **Categoría:** Seguridad
- **Prueba que lo protege:** test_driver_staff: el test confirmó el defecto; un manager sin derechos de administrador crea, edita y archiva choferes con el asistente, que rechaza al personal

### DEF-061: Al cambiar de servidor, la tableta envía el token del servidor anterior al nuevo

- **Causa raíz:** Cambiar la dirección del servidor no borra la sesión guardada.
- **Categoría:** Seguridad
- **Prueba que lo protege:** session.test.ts: un servidor nuevo cierra la sesión antes de cualquier consulta y la credencial de otro servidor sólo lo cambia si la acepta

### DEF-062: La dirección del GPS acepta http y el identificador del bus viajaría sin cifrar

- **Causa raíz:** La validación de Ajustes admite http y la tableta completa con http:// sin comprobar el esquema.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** test_driver_shift: los ajustes rechazan http fuera de la red local y el inicio de turno no entrega el identificador a una dirección http; osmand.test.ts: la tableta no envía a http externo

### DEF-063: Si el bus no pasa por la primera parada, la tableta la sigue mostrando como próxima y no avanza con las demás

- **Causa raíz:** La próxima parada era la primera sin llegada en orden, no la que sigue a la más lejana alcanzada; las paradas saltadas sólo se avisaban al cerrar un viaje programado y nunca en un turno sin horario; un recorrido sólo empezaba en un extremo.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_driver_shift: empezar en la cuarta parada sigue con la quinta y avisa de las tres anteriores; test_trip_run: el viaje marca la primera parada saltada en cuanto llega a la segunda; test_runs: un recorrido empieza en una parada intermedia

### DEF-064: Esquinas cuadradas en la barra del mapa y en tarjetas del portal

- **Causa raíz:** Las hojas usaban --radio-md y --radio-lg, que brand.css no definía; una variable inexistente deja el radio en 0.
- **Categoría:** Interfaz
- **Prueba que lo protege:** Búsqueda de variables usadas y no definidas: ninguna

### DEF-065: La portada salía en español aunque el visitante eligiera inglés o kichwa

- **Causa raíz:** Unos veinte textos (etiquetas de sección, pie, insignias) estaban escritos en la plantilla y no en las cadenas del portal.
- **Categoría:** Internacionalización
- **Prueba que lo protege:** test_portal: las tres lenguas tienen las mismas claves; revisión de la plantilla sin textos fijos

### DEF-066: La portada mostraba cifras y estados que ningún dato respalda

- **Causa raíz:** El rediseño añadió «100 % servicio universitario» y «sistema activo y conectado en tiempo real» fijos, aun con cero buses con señal.
- **Categoría:** Contenido
- **Prueba que lo protege:** Las cifras salen de total_buses, las líneas y las paradas; test_no_invented_numbers_when_no_bus_reports

### DEF-067: Contraste insuficiente en el pie y en los números de los pasos; lista de cifras mal formada

- **Causa raíz:** Colores gris y ámbar sobre fondos claros u oscuros por debajo de 4,5:1; el <dl> tenía un <span> entre <dt> y <dd>.
- **Categoría:** Accesibilidad
- **Prueba que lo protege:** qa/accesibilidad.py (axe): 0 problemas en escritorio y móvil

### DEF-068: Las pruebas HTTP fallaban al azar con «Session expired» (1 a 3 de 590 por corrida)

- **Causa raíz:** 13 de las 256 carpetas de sesiones eran de root; Odoo corre como odoo, no podía guardar ahí la sesión y werkzeug oculta el error.
- **Categoría:** Entorno
- **Prueba que lo protege:** chown -R odoo:odoo /var/lib/odoo; dos corridas completas seguidas sin fallos

### DEF-069: Los gráficos del tablero de Odoo repetían su animación sin parar

- **Causa raíz:** Un reloj actualiza el estado cada segundo; onPatched destruía y volvía a crear todos los gráficos en cada repintado.
- **Categoría:** Rendimiento
- **Prueba que lo protege:** Prueba en el navegador: los gráficos sólo se crean al cargar y al cambiar de pestaña (antes, dos por segundo)

### DEF-070: Mensajes de pasajeros: no aparecía la columna «Resuelta»

- **Causa raíz:** El tablero agrupaba por estado sólo con los estados presentes y la acción filtraba por defecto los no resueltos.
- **Categoría:** Interfaz
- **Prueba que lo protege:** test_complaints: el tablero siempre muestra Nueva, En revisión y Resuelta

### DEF-071: Al borrar un modelo, su tabla queda en la base

- **Causa raíz:** Odoo borra los registros de un modelo que ya no existe pero no su tabla (bus_position_day) ni las vistas SQL kpi_*.
- **Categoría:** Migración
- **Prueba que lo protege:** Actualización de la base de desarrollo: sin vistas kpi_*, sin tabla ni parámetros de Grafana

### DEF-072: Las traducciones nuevas del módulo no se cargaban

- **Causa raíz:** Odoo combina cada .po con el .pot del módulo; el .pot era del 5-nov y descartaba las entradas posteriores.
- **Categoría:** Internacionalización
- **Prueba que lo protege:** Plantilla .pot regenerada; menús y textos en español y kichwa tras actualizar

### DEF-073: Descargar el reporte abría «Configure el diseño de sus documentos» en vez del PDF

- **Causa raíz:** report_action pide el diseño de la compañía si no está configurado, aunque el reporte tiene su propia cabecera.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_report: imprimir devuelve directamente la acción del reporte; descarga probada desde el tablero

### DEF-074: Error del cliente de Odoo al salir del mapa en vivo mientras hace el primer zoom

- **Causa raíz:** Leaflet 1.9.4 termina la animación de zoom 250 ms después aunque el mapa ya se haya quitado, y falla sobre los paneles borrados.
- **Categoría:** Interfaz
- **Prueba que lo protege:** Prueba en el navegador: entrar y salir del mapa en vivo de inmediato no muestra errores

### DEF-075: El administrador no podía activar las notificaciones push en Windows: el botón se quedaba cargando

- **Causa raíz:** La página esperaba navigator.serviceWorker.ready, que sólo se cumple con un service worker que controle la página; /web queda fuera del alcance /bus_tracking/ del nuestro y la espera no terminaba.
- **Categoría:** Lógica
- **Prueba que lo protege:** Chrome (FCM) y Edge (WNS) en Windows: activar, registrar el dispositivo y enviar la prueba; test_push comprueba que no se espera a ready

### DEF-076: La migración 16.0.1.9.0 no pudo borrar el rol grafana_reader en Supabase

- **Causa raíz:** Desde PostgreSQL 16, DROP OWNED BY exige ser miembro del rol; el usuario postgres de Supabase no es superusuario y no lo era.
- **Categoría:** Migración
- **Prueba que lo protege:** En la base de producción: GRANT al usuario actual, DROP OWNED y DROP ROLE en una transacción, 0 roles restantes; test_migration_grafana

### DEF-077: Tras actualizar, los menús en español seguían diciendo Indicadores y Reportes

- **Causa raíz:** Una actualización sin --i18n-overwrite conserva las traducciones que ya estaban en la base, así que los menús renombrados mantenían el nombre viejo.
- **Categoría:** Internacionalización
- **Prueba que lo protege:** Producción: -u con --i18n-overwrite, menús Reportes, Tablero y Notificaciones (Willachikuna en kichwa); desarrollo: la migración devuelve el nombre nuevo a un menú con el viejo

### DEF-078: El emulador perdió el DNS y la app mostraba «Sin conexión» al iniciar sesión

- **Causa raíz:** El emulador conserva el DNS de la red con la que arrancó; la red del PC cambió (red compartida y Tailscale) y dejó de resolver nombres, aunque las IP respondían.
- **Categoría:** Entorno
- **Prueba que lo protege:** Reiniciar la red del emulador (svc wifi/data) o arrancarlo con -dns-server 8.8.8.8; después resolvió el dominio de Azure

### DEF-079: Android muestra «la aplicación no responde» durante el turno aunque la app sigue funcionando

- **Causa raíz:** Cada posición del GPS en segundo plano llega por un trabajo de JobScheduler; en el emulador con Android 17 el sistema no logra enlazar el servicio (Timed out while trying to bind, stated jobs went negative) y lo reporta como ANR. El hilo principal de la app estaba libre.
- **Categoría:** Entorno
- **Prueba que lo protege:** Pendiente: probar en una tableta real o en un emulador con Android 14 o 15; si se repite, agrupar las posiciones para crear menos trabajos

### DEF-080: Un gestor no podía crear recorridos, sincronizar un bus ni simular: «No puede crear Parada de un recorrido programado»

- **Causa raíz:** Crear un recorrido arma sus paradas, y sincronizar o simular guarda posiciones, con el usuario que pulsa el botón; los gestores no pueden crear esos registros del sistema. Las pruebas corrían como superusuario y no lo veían.
- **Categoría:** Permisos
- **Prueba que lo protege:** TestTripCreation y TestManagerActions crean, sincronizan y simulan con un gestor real; un usuario de solo lectura no puede sincronizar

### DEF-081: Los marcadores de inicio y fin del tramo daban 404 y salían como imagen rota

- **Causa raíz:** Leaflet busca las imágenes de su marcador por defecto junto a su CSS, y el módulo solo trae leaflet.js y leaflet.css.
- **Categoría:** Interfaz
- **Prueba que lo protege:** Inicio y fin son etiquetas HTML (divIcon); captura sin errores de consola ni 404

### DEF-082: Los montos de las multas salían sin el símbolo $

- **Causa raíz:** La compañía de una base nueva usa EUR y el dólar viene inactivo: el panel solo conoce las monedas activas.
- **Categoría:** Configuración
- **Prueba que lo protege:** Los datos del módulo activan USD en cada instalación y actualización; captura del kanban con $

### DEF-083: El mapa de la evidencia ocupaba solo unos 300 px de ancho

- **Causa raíz:** Odoo envuelve cada campo en un elemento que no ocupa todo el ancho cuando está fuera de un grupo.
- **Categoría:** Interfaz
- **Prueba que lo protege:** CSS de ancho completo para o_field_bus_fine_evidence; captura del mapa a todo el ancho

### DEF-084: test_migration_grafana falla si otra base del mismo servidor aún da permisos al rol grafana_reader

- **Causa raíz:** El rol es del servidor, no de una base: la base de desarrollo buses sigue en 16.0.1.6.0 con 9 permisos del rol, y DROP ROLE no puede borrarlo. La prueba supone que ninguna otra base lo usa.
- **Categoría:** Entorno
- **Prueba que lo protege:** Pendiente: actualizar la base de desarrollo a 16.0.1.10.0 (su migración 16.0.1.9.0 quita los permisos) o hacer que la prueba cree su propio rol con otro nombre

## 3. Qué falta para cerrar los abiertos

Cada defecto abierto tiene su fase en `docs/arquitectura/PLAN-AUDITORIA-2.md` y la prueba que lo cerrará en la sección 2.

1. DEF-079: Android muestra «la aplicación no responde» durante el turno aunque la app sigue funcionando
2. DEF-084: test_migration_grafana falla si otra base del mismo servidor aún da permisos al rol grafana_reader
