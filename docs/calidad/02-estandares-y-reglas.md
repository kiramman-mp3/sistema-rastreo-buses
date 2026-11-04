# Estándares técnicos, reglas de negocio e interfaces

Reglas que el código implementa hoy y que las pruebas verifican. Si una regla cambia, se cambia aquí, en el código y en una prueba.

## 1. Reglas de negocio

| N.º | Regla | Dónde vive | Prueba |
|---|---|---|---|
| R1 | La velocidad llega en nudos y se guarda en km/h (× 1,852). Un bus "se mueve" por encima de 2 km/h. | `models/utils.py`, `bus_vehicle.py` | F2; `test_ingest` |
| R2 | Una posición es única por bus y hora GPS; una posición más antigua no pisa el estado del bus. | `bus_position.py` (restricción SQL), `bus_vehicle.py` | F3, F4, P6 |
| R3 | Un bus está "conectado" si su última posición tiene 3 minutos o menos; sin eso se muestra "sin señal". | `bus_vehicle.py` | `test_ingest`, `test_portal` |
| R4 | La llegada a una parada se registra una sola vez mientras el bus sigue dentro del radio de la parada. | `bus_vehicle._update_current_stop` | F5 |
| R5 | Un recorrido se abre cuando el bus sale de la primera o la última parada y se cierra al llegar a la otra. Si vuelve al origen se descarta; uno abierto más de 12 horas se descarta; una ruta con menos de 2 paradas no genera recorridos. | `bus_run.py` | F6; `test_runs` (8 pruebas) |
| R6 | Alerta de **exceso de velocidad** por encima del límite (50 km/h por defecto); se cierra al bajar y guarda el máximo. | `bus_alert.py` | F7; `test_alerts` |
| R7 | Alerta de **bus sin señal** tras 10 minutos de silencio, solo si reportó en las últimas 6 horas. Alerta de **parada larga** tras 15 minutos detenido lejos de toda parada. Alerta de **desvío** si se aleja más de 150 m de la línea de la ruta durante 3 minutos. Todos los umbrales se cambian en Ajustes. | `bus_alert.py` | `test_alerts`, `test_simple` |
| R8 | Solo puede haber una alerta abierta por bus y tipo (lo impone un índice único de la base). | `bus_alert.init` | `test_database_allows_a_single_open_alert_…` |
| R9 | El portal público muestra solo rutas activas y marcadas como públicas, con buses que reportaron en los últimos 15 minutos, y de cada bus únicamente nombre, posición, rumbo y estado. | `controllers/portal.py` | F8, F9, E10, E11; `test_portal` |
| R10 | El feed público admite 60 consultas por minuto por dirección (429 con `Retry-After`) y guarda una caché de 5 segundos. El límite cuenta por proceso. | `controllers/portal.py` | E21 |
| R11 | Una queja lleva descripción de 10 a 2000 caracteres, correo y teléfono opcionales con formato válido, y recibe un folio `Q-00001…`. Se descartan en silencio los envíos con el campo trampa lleno, con el token falso o hechos en menos de 3 segundos. Máximo 5 quejas por dirección y hora; cuerpo máximo de 20 KB; token CSRF obligatorio. | `controllers/complaints.py`, `bus_complaint.py` | F10, F11, E12 a E18, E22 |
| R12 | El correo y el teléfono de una queja se borran 90 días después de resuelta (0 = conservar) y solo los leen los administradores. | `bus_complaint.py` | `test_contact_data_is_erased_…` |
| R13 | El webhook exige el secreto (cabecera `X-Webhook-Secret` o `Authorization: Bearer`; el parámetro de URL queda por compatibilidad), comparado en tiempo constante. Si no hay secreto configurado, el webhook queda cerrado. | `controllers/main.py` | E1, E2, F1, F12 |
| R14 | Las notificaciones push solo se registran y se envían a administradores, y solo a los servicios push de una lista permitida. Los mensajes van cifrados y firmados. | `controllers/push.py`, `bus_push.py` | E20; `test_push` |
| R15 | Las posiciones más antiguas que la retención (días, ajustable; 0 = conservar todo) se purgan cada día. | `bus_position._cron_cleanup` | `test_cleanup_…` |
| R16 | Una posición con latitud fuera de −90 a 90, longitud fuera de −180 a 180 u hora ilegible **debe rechazarse con 400 sin guardarse**. | — | **No se cumple hoy** (DEF-008 a DEF-010); E7, E8, E9 |

## 1.1 Reglas de horario, puntualidad y recorridos programados

Piden el PDF del proyecto final (Actividades 4, 5 y 6). Todos los umbrales se cambian en *Configuración > Ajustes > Trips and punctuality*.

| N.º | Regla | Valor por defecto | Por qué ese valor | Dónde vive | Prueba |
|---|---|---|---|---|---|
| R17 | Cada parada tiene minutos previstos desde la salida (no decrecen a lo largo de la ruta). Un horario dice a qué hora sale una línea y en qué días; el recorrido programado es un bus en un horario en una fecha. Las horas se escriben en hora de Ecuador (UTC-5) y se guardan en UTC. | — | Ecuador no tiene horario de verano | `bus_trip.py`, `bus_route.py` | `test_trips` |
| R18 | Un bus no puede tener dos recorridos que se solapen; puede hacer otras rutas en otros horarios. | — | Un bus está en un solo sitio | `bus.trip._check_overlap` | `test_a_bus_cannot_have_two_trips…` |
| R19 | Una llegada a una parada pertenece al recorrido programado de esa ruta cuya ventana (inicio previsto a fin previsto), ampliada por un margen, contiene la hora; si hay dos, el de inicio más cercano. | margen de 30 min | Un bus llega antes de salir y se queda después de llegar; 30 min cubre eso sin confundir recorridos consecutivos de 25 min | `bus.trip._on_arrival` | `TestTripRun` |
| R20 | **Retraso:** una llegada es tardía si pasa de la hora prevista más la tolerancia; adelantada si llega antes de la hora prevista menos la tolerancia. Ejemplo del PDF: parada prevista a las 08:15, tolerancia 5 min, llegada a las 08:23: retraso de 8 min e incumplimiento de puntualidad. En el límite exacto (5 min 00 s) es puntual; con 5 min 01 s es tardía. | tolerancia de 5 min | El tráfico urbano de Ambato varía unos minutos de un día a otro; menos de 5 min haría saltar la alerta por ruido y más de 10 dejaría pasar retrasos que el pasajero sí nota | `bus.trip._register_arrival` | `test_the_example_of_the_assignment`, `test_the_tolerance_limit_is_exact` |
| R21 | **Parada omitida:** al cerrar un recorrido, la parada sin llegada dentro de su radio es omitida. **Recorrido incompleto:** el que se cierra con alguna parada omitida o sin llegar a ninguna. Un recorrido que nunca arrancó genera una sola alerta de recorrido incompleto, no una por parada. | radio de la parada: 50 m | Es el radio que ya usa la detección de llegadas (R4); un GPS de celular tiene una exactitud de 5 a 20 m | `bus.trip._finalize`, `_evaluate_rules` | `TestSkippedAndIncomplete` |
| R22 | **Salida tardía:** un recorrido planificado que no ha arrancado pasados 10 minutos de su hora prevista (una alerta por recorrido; 0 la desactiva). | 10 min | Es el mismo orden de magnitud que la alerta de bus sin señal (R7) | `bus.trip._cron_close_trips` | `TestLateStart` |
| R23 | **Diferencia de tiempos:** un recorrido terminado cuya duración real difiere de la prevista en más de este porcentaje queda marcado. | 25 % | Un recorrido de 25 min que dura 31 min o más (o menos de 19) ya cambia la experiencia del pasajero | `bus.trip._evaluate_rules` | `TestDurationFlag` |
| R24 | Un recorrido cuya ventana (y margen) terminó se cierra solo con lo que tiene; las alertas de estas reglas se escriben cerradas, una por recorrido, tipo y parada. | cada 10 min | Un cierre tardío no debe duplicar alertas | `bus.trip._cron_close_trips`, `bus.alert._trip_event` | `test_closing_twice…` |

## 2. Estándares de las interfaces

| Interfaz | Respuesta correcta | Errores |
|---|---|---|
| Webhook `POST /bus_tracking/traccar/webhook` | 200 sin cuerpo (también cuando el dispositivo es desconocido o falta el identificador) | 403 secreto ausente o falso; 400 cuerpo que no es JSON; 405 otro método; **hoy 500 con latitud no numérica u hora inválida (debería ser 400)** |
| Salud `GET /bus_tracking/health` | 200 `{"status": "ok"}` | 503 `{"status": "stale"}` si no llegan posiciones |
| Feed `GET /rutas/<código>/buses.json` | 200 `{"generated_at", "buses": [{name, lat, lon, course, status}]}` | 404 ruta inexistente o privada; 429 demasiadas consultas |
| Páginas públicas `/rutas`, `/quejas` | 200 HTML | 400 datos inválidos con mensaje en el idioma de la persona; 413 cuerpo grande; 429 límite de quejas |
| Panel `/bus_tracking/live` y similares (JSON-RPC) | Resultado JSON-RPC | Error de sesión o `AccessError`; nunca datos sin sesión |

Semántica de los códigos: 400 para datos inválidos o ausentes, 403 para falta de autorización del emisor, 404 para lo que no existe o no es público, 429 para exceso de uso. Un 500 es siempre un defecto: ninguna entrada debe producirlo (meta del cuadro de mando). A diferencia de la API del taller de TechStore, este sistema no usa el formato `{"success": bool}` porque sus entradas son un webhook sin cuerpo de respuesta y páginas HTML; solo el feed devuelve JSON.

## 3. Convenciones de trabajo

- Ramas `main` (estable), `develop` (desarrollo) y `feature/*`, `fix/*`, `refactor/*`, `chore/*`; nombres en kebab-case; nada se desarrolla en `main`.
- Commits pequeños con Conventional Commits (`feat`, `fix`, `refactor`, `style`, `docs`, `test`, `chore`, `perf`, `build`, `ci`); la fusión a `develop` usa `--no-ff`. Detalle en `CLAUDE.md`.
- Código en inglés, documentación en español, textos de interfaz traducibles en `i18n/`.
- Las pruebas de Odoo corren siempre en una base nueva y sin el español cargado.
- Los secretos nunca se versionan (`.env`, `.env.prod`, `config/odoo.prod.conf` y `backups/` están en `.gitignore`).

## 4. Análisis estático

El taller de referencia exige SonarQube con `flake8` y `pylint-odoo` antes de integrar. **Hoy el proyecto no tiene ninguno configurado** (no hay `.flake8`, `.pylintrc` ni `sonar-project.properties`). Es un faltante declarado en `11-elementos-acs.md`. Plan: agregar `flake8` y `pylint-odoo` con una configuración mínima en `chore/lint-config`, ejecutarlos junto con las pruebas y, cuando haya servidor, enviar el reporte a SonarQube.
