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
