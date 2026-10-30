# Plan y casos de prueba

Documento de pruebas en el sentido de ISO/IEC/IEEE 29119-3: estrategia, diseño de casos, procedimiento y criterios. Los resultados están en `04-resultados-y-metricas.md`. Este archivo lo genera `qa/generar_docs.py` a partir de las evidencias; no se edita a mano.

## 1. Estrategia

| Nivel | Qué prueba | Herramienta | Cantidad |
|---|---|---|---|
| Unitarias y de integración | Modelos, reglas de negocio, controladores y permisos dentro de Odoo, en una base limpia | `TransactionCase` y `HttpCase` de Odoo 16, con coverage.py | 150 pruebas |
| Suite en vivo | El sistema como lo usan un celular, un pasajero y un administrador, por HTTP y XML-RPC | `qa/qa_suite.py` | 47 casos |
| Auditoría aleatoria | Robustez ante entradas normales y límite, con semilla fija, sobre 15 áreas | `qa/auditoria.py` | 1.000 peticiones |
| Datos | Estado real de la base tras las pruebas (rangos, duplicados, coherencia) | Consultas SQL en `qa/metricas.py` | 11 consultas |
| Mutación (manual) | Que las pruebas fallen si se rompe una regla | Registradas en `docs/BITACORA.md` | 16 mutaciones, todas detectadas |
| Exploratoria (manual) | Interfaz, móvil de 390 px, idiomas | Chrome (ver bitácora) | Por sesión |

## 2. Criterios de aceptación

- Generales: error menor al 10 %, tiempo de respuesta promedio menor a 0,5 s, desviación baja (CV de 50 % o menos).
- Específicos: ninguna entrada puede causar una respuesta HTTP 5xx; ningún registro con datos imposibles; el feed público nunca muestra placa, conductor ni velocidad; capacidad de ingesta de al menos 10 peticiones por segundo (100 buses, un reporte cada 10 s).
- Un defecto corregido debe quedar protegido por una prueba nueva (ver `01-politica-y-alcance.md`).

## 3. Pruebas de Odoo (150)

| Archivo | Qué verifica | Pruebas | Media (s) | Máx. (s) |
|---|---|---|---|---|
| `test_alerts.py` | Alertas de velocidad, sin señal y parada larga | 14 | 0,0174 | 0,0600 |
| `test_complaints.py` | Quejas: modelo, formulario y antiabuso | 29 | 0,1180 | 0,6120 |
| `test_gps_setup.py` | Registro del GPS del celular y QR | 9 | 0,0317 | 0,0980 |
| `test_http.py` | Webhook, salud, mapa en vivo y landing | 13 | 0,1250 | 0,3540 |
| `test_ingest.py` | Ingesta de posiciones, llegadas y purga | 17 | 0,0082 | 0,0210 |
| `test_portal.py` | Portal público, privacidad, caché y límite de uso | 18 | 0,1148 | 0,4380 |
| `test_push.py` | Notificaciones push: permisos, cifrado y endpoints | 14 | 0,5351 | 1,0460 |
| `test_runs.py` | Recorridos automáticos | 8 | 0,0189 | 0,0300 |
| `test_simple.py` | Línea del mapa, desvío, push de alertas y permisos de quejas | 7 | 0,0194 | 0,0540 |
| `test_stop_picker.py` | Editor de paradas en el mapa | 6 | 0,0132 | 0,0460 |
| `test_traccar_sync.py` | Sincronización con Traccar (respuestas simuladas) | 6 | 0,0162 | 0,0300 |
| `test_track.py` | Trazado grabado y simplificación | 9 | 0,0242 | 0,0560 |

Comando (base nueva, sin datos de demostración):

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm odoo odoo -d buses_test -i bus_tracking --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all
```

## 4. Casos de la suite en vivo (47)

Códigos: F funcional, E manejo de errores, P rendimiento, U usabilidad.

| ID | Tipo | Objetivo | Entrada | Resultado esperado | Estado hoy |
|---|---|---|---|---|---|
| E1 | Error | Rechazar el webhook sin secreto | POST sin cabecera ni parámetro | HTTP 403 y 0 posiciones nuevas | PASS |
| E2 | Error | Rechazar el webhook con un secreto equivocado | X-Webhook-Secret: incorrecto | HTTP 403 | PASS |
| E3 | Error | Rechazar un cuerpo que no es JSON | Cuerpo "esto no es json" | HTTP 400, sin traza | PASS |
| E4 | Error | Rechazar un método distinto de POST en el webhook | GET al webhook | HTTP 405 (o 404), nunca 200/500 | PASS |
| E5 | Error | Ignorar un JSON sin identificador de dispositivo | {"foo": 1} | HTTP 200 y 0 posiciones nuevas | PASS |
| E6 | Error | Ignorar una posición de un dispositivo desconocido | deviceId 999999 | HTTP 200 y 0 posiciones nuevas | PASS |
| E7 | Error | No guardar una latitud fuera de rango | lat = 95° (el máximo es 90°) | Rechazo (4xx) o descarte; nunca 5xx ni dato guardado | PASS |
| E8 | Error | Controlar una latitud no numérica | lat = "abc" | Rechazo (4xx) o descarte; nunca 5xx | PASS |
| E9 | Error | Controlar una hora GPS inválida | fixTime = "ayer" | Rechazo (4xx) o descarte; nunca 5xx | PASS |
| E10 | Error | Responder 404 para una ruta pública inexistente | GET /rutas/NOPE y /rutas/NOPE/buses.json | HTTP 404 en ambas | PASS |
| E11 | Error | No mostrar una ruta privada | GET /rutas/QA-PRIV y su feed | HTTP 404 en ambas | PASS |
| E12 | Error | Rechazar una queja demasiado corta | description = "corto" | HTTP 400 con mensaje y 0 quejas nuevas | PASS |
| E13 | Error | Rechazar un correo inválido | email = "no-es-correo" | HTTP 400 con mensaje y 0 quejas nuevas | PASS |
| E14 | Error | Rechazar un envío sin token CSRF | POST /quejas sin csrf_token | Rechazo 4xx y 0 quejas nuevas | PASS |
| E15 | Error | Descartar sin guardar un envío con el campo trampa lleno | website = "http://spam" | Parece éxito (303) pero 0 quejas nuevas | PASS |
| E16 | Error | Descartar un envío demasiado rápido (menos de 3 s) | POST inmediato tras cargar el formulario | Parece éxito (303) pero 0 quejas nuevas | PASS |
| E17 | Error | Escapar lo que escribió la persona al volver a mostrar el formulario | description con <script> y correo inválido | El HTML devuelto no contiene <script> sin escapar | PASS |
| E18 | Error | Rechazar un cuerpo mayor de 20 KB | description de 25 000 caracteres | HTTP 413 y 0 quejas nuevas | PASS |
| E19 | Error | Negar el mapa interno sin sesión | JSON-RPC a /bus_tracking/live sin sesión | Error de sesión; sin datos de buses | PASS |
| E20 | Error | Negar el uso de notificaciones push a un usuario sin rol de administrador | Usuario de solo lectura llama /bus_tracking/push/state | Error de acceso (AccessError) | PASS |
| E21 | Error | Limitar el feed público a 60 peticiones por minuto y dirección | Más de 60 GET seguidos a /rutas/QA1/buses.json | Aparece HTTP 429 con Retry-After | PASS |
| E22 | Error | Limitar a 5 quejas por hora y dirección | Quejas válidas seguidas desde la misma dirección | La sexta recibe HTTP 429 y no se guarda | PASS |
| E23 | Error | Rechazar un login de chofer con clave incorrecta | POST /bus_tracking/driver/login con clave mala | HTTP 401; mismo aspecto que un usuario desconocido | PASS |
| E24 | Error | Rechazar el inicio de turno si el bus no tiene GPS | shift/start sobre QA-21 sin traccar_unique_id | HTTP 409 no_gps | PASS |
| E25 | Error | Rechazar un incidente sin turno activo | POST /driver/incident tras cerrar el turno | HTTP 409 no_shift | PASS |
| F1 | Funcional | Guardar una posición válida enviada por el webhook (secreto en cabecera) | POST con deviceId 101, lat -1.2650, lon -78.6250 | HTTP 200; 1 posición; el bus queda en esa posición | PASS |
| F2 | Funcional | Convertir la velocidad de nudos a km/h | speed = 10 nudos | last_speed = 18,52 km/h | PASS |
| F3 | Funcional | Ignorar una posición duplicada (mismo bus y hora GPS) | La misma posición enviada 2 veces | 1 sola posición guardada | PASS |
| F4 | Funcional | Una posición más antigua no sobrescribe el estado del bus | Posición de hace 100 s y luego una de hace 500 s | last_fix_time y última posición no cambian; se guardan 2 | PASS |
| F5 | Funcional | Registrar la llegada a una parada una sola vez mientras el bus sigue dentro del radio | Dos posiciones consecutivas en la parada QA Terminal | 1 llegada; el bus queda en esa parada | PASS |
| F6 | Funcional | Registrar un recorrido completo entre la primera y la última parada | Salida de QA Terminal, tramo intermedio y llegada a QA Campus | 1 recorrido terminado de Terminal a Campus | PASS |
| F7 | Funcional | Abrir y cerrar la alerta de exceso de velocidad | 40 nudos (74 km/h) y luego 5 nudos | Alerta "speeding" abierta con máximo ≈74 km/h y luego cerrada | PASS |
| F8 | Funcional | La página pública /rutas lista solo las rutas públicas | GET /rutas | HTTP 200; aparece "QA Troncal"; no aparece "QA Privada" | PASS |
| F9 | Funcional | El feed público expone solo nombre, posición, rumbo y estado | GET /rutas/QA1/buses.json | Claves exactas {name, lat, lon, course, status}; sin placa ni velocidad | PASS |
| F10 | Funcional | Guardar una queja válida y entregar un folio | Formulario con descripción de 60 caracteres y correo | HTTP 303 a /quejas/gracias?f=Q-…; queja en estado "new" | PASS |
| F11 | Funcional | Aceptar una queja anónima (sin correo ni teléfono) | Formulario solo con descripción | HTTP 303 con c=0 (no podemos responder) | PASS |
| F12 | Funcional | Aceptar el secreto como parámetro de consulta (instalaciones antiguas) | POST ?secret=… sin cabecera | HTTP 200 y 1 posición | PASS |
| F13 | Funcional | Iniciar sesión de chofer y recibir un token | POST /bus_tracking/driver/login con qa_driver | HTTP 200; token; el nombre del chofer | PASS |
| F14 | Funcional | Abrir un turno, consultar estado, reportar incidente y cerrar | start → state → incident → end sobre QA-20 | Turno activo, state con paradas, incidente guardado, turno cerrado | PASS |
| P1 | Rendimiento | 100 posiciones secuenciales al webhook | 100 POST de un mismo bus, una hora GPS distinta cada uno | Media < 0,5 s y 0 % de error | PASS |
| P2 | Rendimiento | 200 posiciones con 20 hilos sobre 20 buses distintos | 20 hilos × 10 posiciones por bus | Media < 1 s y error < 10 % | PASS |
| P3 | Rendimiento | 100 cargas de la página pública /rutas | 100 GET secuenciales | Media < 0,5 s y 0 % de error | PASS |
| P4 | Rendimiento | 45 lecturas del feed público (con caché de 5 s) | 45 GET a /rutas/QA1/buses.json | Media < 0,5 s y 0 % de error | PASS |
| P5 | Rendimiento | 100 consultas al endpoint de salud | 100 GET a /bus_tracking/health | Media < 0,5 s y 0 % de error | PASS |
| P6 | Rendimiento | Integridad con 20 hilos que envían la misma posición a la vez | 20 POST idénticos simultáneos | 1 posición guardada y ningún HTTP 5xx | PASS |
| P7 | Rendimiento | 60 posiciones distintas de un mismo bus con 20 hilos | 60 POST, un solo bus, 20 hilos | 60 guardadas, error < 10 % y p95 < 2 s | FAIL |
| U1 | Usabilidad | Mensajes de rechazo comprensibles y sin datos técnicos | 7 entradas inválidas hacia la persona usuaria | 100 % con mensaje de negocio, sin SQL ni trazas | PASS |

## 5. Áreas de la auditoría aleatoria (1.000 peticiones, semilla 20261028)

Cada petición tiene su resultado esperado decidido antes de enviarla. Pasa si el estado HTTP es uno de los esperados; además se cuentan como error las posiciones con coordenadas imposibles que el sistema guarda, porque responden 200 y solo se ven en la base.

| Área | Peticiones | Errores | Media (s) | Máx. (s) |
|---|---|---|---|---|
| 01 Webhook: posición válida | 68 | 0 | 0,0441 | 0,0896 |
| 02 Webhook: secreto ausente o falso | 74 | 0 | 0,0291 | 0,0537 |
| 03 Webhook: cuerpo que no es JSON | 72 | 0 | 0,0286 | 0,0522 |
| 04 Webhook: JSON que no es un objeto | 64 | 0 | 0,0277 | 0,0494 |
| 05 Webhook: dispositivo desconocido | 81 | 0 | 0,0281 | 0,0525 |
| 06 Webhook: valores inválidos en la posición | 83 | 25 | 0,0389 | 0,0766 |
| 07 Webhook: método incorrecto | 48 | 0 | 0,0281 | 0,0537 |
| 08 Portal: lista de rutas | 63 | 0 | 0,0548 | 0,0932 |
| 09 Portal: mapa de una ruta pública | 60 | 0 | 0,0579 | 0,1073 |
| 10 Portal: ruta inexistente, privada o hostil | 81 | 0 | 0,0284 | 0,0498 |
| 11 Feed público de buses | 56 | 0 | 0,0282 | 0,0632 |
| 12 Feed de ruta inexistente o privada | 59 | 0 | 0,0280 | 0,0552 |
| 13 Salud del servicio | 58 | 0 | 0,0295 | 0,0560 |
| 14 Formulario de quejas y páginas públicas | 70 | 0 | 0,0539 | 0,0949 |
| 15 Quejas: envíos inválidos | 63 | 0 | 0,0505 | 0,1577 |

## 6. Pruebas manuales registradas en la bitácora

- Prueba de punta a punta con Traccar real: celular simulado por OsmAnd, Traccar, webhook, Odoo (fases 3 y 9).
- Instalación de producción con `init-prod.sh`, HTTPS con el certificado interno de Caddy, respaldo, restauración en base paralela y restauración completa (fase 8).
- Revisión visual en Chrome de la landing, el login, el portal, el formulario de quejas y el panel, incluido el ancho de 390 px.
- Pendiente: celular y Traccar reales durante un turno, entrega de un push a un navegador real, correo con el servidor de la universidad.
