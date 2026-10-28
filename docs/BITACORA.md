# Bitácora del proyecto

Registro cronológico de lo que se hace en el proyecto. Cada entrada indica qué se hizo, qué se verificó y qué quedó pendiente. Se agrega una entrada nueva en cada sesión de trabajo, sin borrar las anteriores.

## 2026-10-26: construcción inicial y validación con Traccar real

### Qué se hizo

1. **Infraestructura** (`docker-compose.yml`, `.env.example`, `config/odoo.conf`): Postgres 15, Odoo 16 y Traccar. El puerto de Odoo en el host es configurable con `ODOO_PORT` porque el 8069 ya lo ocupaba otro contenedor (`odoo16`) de esta máquina.
2. **Módulo Odoo `addons/bus_tracking`**:
   - Modelos: `bus.vehicle`, `bus.route`, `bus.route.stop`, `bus.position`, `bus.stop.arrival`.
   - Cliente REST de Traccar (`models/traccar_api.py`).
   - Webhook `POST /bus_tracking/traccar/webhook?secret=...` y endpoints JSON `/bus_tracking/live` y `/bus_tracking/track`.
   - Cron de respaldo cada minuto y cron diario de purga de posiciones.
   - Vistas, menús, grupos User/Manager y pantalla de configuración con "Test connection" e importación de dispositivos.
   - Mapa en vivo (acción de cliente OWL + Leaflet 1.9.4 incluido en `static/lib/leaflet`).
3. **Documentación**: `README.md` (puesta en marcha) y `docs/PLAN.md` (fases del proyecto).

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Sintaxis Python y XML | OK |
| Instalar el módulo en Odoo 16 limpio | OK, sin errores ni warnings |
| Ingesta: nudos a km/h, deduplicación, detección de llegada a parada | OK (shell de Odoo) |
| Webhook por HTTP: secreto malo o ausente / válido / cuerpo inválido | 403 / 200 / 400 |
| Importar dispositivos desde un Traccar real | OK |
| GPS simulado por OsmAnd (puerto 5055) -> Traccar -> Odoo | OK; posición y llegada registradas |
| Mapa en Chrome: paradas, ruta, bus, trazado, lista, sin errores de consola | OK |

### Problemas encontrados y cómo se resolvieron

- **Puerto 8069 ocupado** por un Odoo ajeno al proyecto. Se agregó `ODOO_PORT`. Mis primeras pruebas HTTP golpearon ese Odoo por error (respuesta 404); se repitieron en el puerto 8070.
- **Traccar reenviaba con `GET` y el webhook respondía 405.** La clave `forward.json` ya no existe en Traccar 6; ahora es `forward.type=json`. Se cambió `FORWARD_JSON`/`FORWARD_ENABLE` por `FORWARD_TYPE=json` y `FORWARD_RETRY_ENABLE=true`. Fuente: https://www.traccar.org/forward/
- **`docker compose exec ... odoo shell` fallaba** (sin conexión a Postgres) porque `exec` no pasa por el entrypoint que agrega los argumentos de base de datos. Se usa `docker compose run --rm -T odoo odoo shell ...`.

### Pendiente o sin confirmar

- La llegada a la parada "Hospital" no apareció en la consulta que corrí justo después del último punto simulado. No se volvió a revisar; hay que repetir la prueba.
- Falta probar con un GPS físico o un teléfono real.
- Fase 0 del plan sin responder (flota, hardware, hosting, pasajeros, alertas, idioma).
- Fases 5 a 8 del plan sin iniciar.

### Estado del entorno de pruebas

Los contenedores, volúmenes, la base `bustest` y el `.env` de prueba se eliminaron al terminar. Para repetir las pruebas hay que levantar el stack de nuevo.

## 2026-10-26 (segunda sesión): landing, login y tema del backend

### Qué se hizo

1. **Landing pública** en `/` (visitantes sin sesión) y en `/inicio` (siempre visible). Quien ya tiene sesión sigue yendo a `/web`. Controlador en `controllers/landing.py`, plantilla en `views/landing_templates.xml`, estilos en `static/src/landing/landing.css`.
2. **Login rediseñado** (`views/login_templates.xml`, `static/src/css/login.css`): panel con foto y frase a la izquierda, formulario a la derecha; en pantallas angostas la foto pasa a ser un banner superior.
3. **Tema del backend**: variables SCSS (`static/src/scss/primary_variables.scss`) y `static/src/css/backend.css`: barra superior color tinta con línea amarilla, botones primarios verde azulado, tipografías nuevas. El mapa en vivo usa los mismos colores.
4. **Activos libres**: tres fotos de Unsplash y dos familias tipográficas con licencia OFL, guardadas dentro del módulo (sin dependencias externas en tiempo de ejecución, salvo los mapas de OpenStreetMap).
5. Detalle del diseño y créditos en `docs/DISENO.md`.

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Instalar el módulo con las plantillas y los assets nuevos | OK, sin errores ni warnings |
| `/` y `/inicio` responden 200; `/web/login` responde 200 | OK |
| Landing en Chrome (escritorio): hero, ruta animada, secciones, cierre, pie | OK |
| Login en Chrome (escritorio y ancho 390 px) | OK |
| Backend con el tema nuevo (menú, lista de rutas, mapa) | OK, sin errores de consola |
| Desbordamiento horizontal en 390 px (landing 375/375, login 390/390) | Sin desbordes |

### Problemas encontrados

- Unsplash bloquea las descargas por línea de comandos con un desafío anti-bots. No se intentó esquivarlo: las direcciones públicas de las fotos se leyeron desde el navegador del usuario y las imágenes se descargaron desde el CDN de Unsplash.
- Una de las fotos candidatas era de Unsplash+ (licencia de pago) y se descartó.
- `resize_window` no cambia el viewport real en este entorno; el ancho móvil se probó con un iframe de 390 px.
- En una pantalla de 622 px de alto, la ruta animada del hero queda bajo el pliegue; en pantallas más altas debería verse completa, pero no lo medí.

### Pendiente o sin confirmar

- "Ruta Viva" es un nombre provisional que inventé para la marca. Hay que confirmarlo o cambiarlo (aparece en `views/landing_templates.xml`, `views/login_templates.xml` y el pie).
- El texto de la landing supone tres públicos (quien espera, quien conduce, quien coordina). La fase 0 del plan sigue sin respuesta; no se prometió ninguna función para pasajeros que no exista hoy.
- Las etiquetas del login ("Email", "Password", "Log in") salen en el idioma de la base de datos. Para verlas en español hay que instalar el idioma español en Odoo.
- La traducción `i18n/es.po` de los textos del módulo sigue pendiente.
- No se probó la landing en Safari ni Firefox.

### Estado del entorno de pruebas

Contenedores, volúmenes y la base `bustest` eliminados. No quedó `.env` de prueba.

## 2026-10-26 (tercera sesión): tests automatizados y traducción al español

### Qué se hizo

1. **Tests** en `addons/bus_tracking/tests/` (31 tests): ingesta de posiciones (conversión de nudos a km/h, zona horaria, duplicados, posiciones inválidas, posición antigua que no pisa la última), llegadas a paradas (una sola llegada mientras el bus está dentro del radio, salida de la parada, recorrido completo en orden), purga por retención, estado del bus, cliente de Traccar con respuestas simuladas (credenciales, token, error 500, sin configurar, importación de dispositivos), webhook (secreto, cuerpo inválido, método GET), endpoints `/live` y la landing.
2. **Traducción** `i18n/es.po` generada desde `i18n/bus_tracking.pot` (108 textos traducidos).
3. README: sección de tests y cómo activar el español.

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base nueva | 0 fallos, 0 errores, 31 tests |
| Mutación: factor de velocidad en 1.0 y autenticación del webhook desactivada | La suite falló en 3 tests (velocidad y dos de webhook); código restaurado |
| Español cargado en Odoo: etiqueta "Patente", estados "En movimiento / Detenido / Sin señal", menús "Mapa en vivo" y "Configuración" | OK |

### Pendiente anterior aclarado

La llegada a la parada "Hospital" sí se registra: `test_full_route_logs_every_stop_in_order` pasa con Terminal, Plaza y Hospital en orden. Lo que vi antes fue una consulta mía ejecutada antes de que se procesara el último punto.

### Problemas encontrados

- Git Bash convierte `/bus_tracking` en una ruta de Windows y el runner de tests no encontraba nada ("Invalid tag C:/Program Files/Git/bus_tracking", 0 tests). Se resuelve con `MSYS_NO_PATHCONV=1`.
- Mi primer script para generar `es.po` perdió las barras invertidas al pasar por la shell; se reescribió sin ellas.
- Un test de `HttpCase` usa el usuario `admin` con contraseña `admin`, que es la que Odoo asigna al crear una base con `-i` sin datos de demostración. Si cambias esa contraseña antes de correr los tests en la misma base, esos dos tests (`/live` con sesión y landing con sesión) fallarán; usa una base de pruebas aparte.

### Pendiente o sin confirmar

- Fase 0 del plan sin responder. Las fases 4 (geometría real de la ruta, viajes y ETA), 5 (alertas) y 6 (reportes) dependen de esas decisiones.
- Prueba con un GPS físico o teléfono real.
- Prueba de carga de la ingesta.
- Fase 8 (producción: HTTPS, secretos, respaldos).

### Estado del entorno de pruebas

Contenedores, volúmenes y la base de pruebas eliminados.

## 2026-10-26 (cuarta sesión): fase 8, producción

### Qué se hizo

1. **Pila de producción** (`docker-compose.prod.yml`, `proxy/Caddyfile`, `.env.prod.example`): Postgres, Odoo, Traccar y Caddy como proxy HTTPS. Solo el proxy y los puertos de los GPS se publican.
2. **`scripts/init-prod.sh`**: crea secretos aleatorios, genera `config/odoo.prod.conf` (contraseña maestra con hash, `list_db = False`, `dbfilter`, workers y límites), crea las bases, instala el módulo, fija la contraseña de `admin` y carga el secreto del webhook.
3. **`scripts/backup.sh` y `scripts/restore.sh`**: respaldo de Odoo, Traccar y filestore con checksums y retención; restauración en base paralela o completa (`--yes`).
4. **Traccar sobre Postgres** en producción (en desarrollo sigue la base H2 de pruebas).
5. **Secreto del webhook en una cabecera** (`X-Webhook-Secret`, o `Authorization: Bearer`): antes iba en la URL y los logs de Odoo la mostraban completa. El parámetro de URL se mantiene por compatibilidad. El `docker-compose.yml` de desarrollo también usa la cabecera ahora.
6. **Endpoint `/bus_tracking/health`** (200 mientras llegan posiciones, 503 si no) y el ajuste `Report as down after (minutes)` en Settings.
7. **Documentación**: `docs/PRODUCCION.md` (instalación, respaldos, monitoreo, actualización, limitaciones) y `.gitignore` para secretos y respaldos.
8. **Traducción**: 3 textos nuevos en `i18n/es.po`.

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Instalación completa con `init-prod.sh` desde una máquina sin nada | OK (se repitió dos veces, ver problemas) |
| HTTPS con certificado interno de Caddy; cabeceras HSTS, nosniff, SAMEORIGIN, Referrer-Policy; sin cabecera `Server` | OK |
| `/bus_tracking/traccar/webhook`, `/web/database/manager` y `/web/database/selector` desde el proxy | 404 |
| Traccar sobre Postgres | 51 tablas creadas |
| Posición simulada por OsmAnd -> Traccar -> Odoo con el secreto en la cabecera | OK; el log de Odoo muestra `POST /bus_tracking/traccar/webhook` sin el secreto (0 apariciones del secreto) |
| Respaldo y checksums | OK; el filestore respalda 26 archivos |
| Restauración en una base paralela | Mismas cantidades de filas que producción |
| Restauración destructiva completa: se borró el bus y se corrompió un adjunto | Volvieron el bus, el contenido original del adjunto y las 51 tablas de Traccar; los servicios quedaron arriba |
| `restore.sh` sin `--yes` | Se niega a tocar producción |
| Healthchecks de Postgres, Odoo y Traccar | En verde |
| `/bus_tracking/health` con un bus que nunca reportó | 503 `{"status": "stale"}` |
| Suite de tests tras los cambios | 34 tests, 0 fallos (3 nuevos: cabecera del secreto y dos de salud) |
| Traducción nueva cargada en Odoo | OK |

### Problemas encontrados y cómo se resolvieron

- **Respaldo del filestore vacío.** Mi `odoo.prod.conf` reemplaza el archivo de la imagen y no definía `data_dir`, así que Odoo guardaba el filestore en otra ruta que la que respaldaba el script (el respaldo salió con 0 archivos y no avisó). Se agregó `data_dir = /var/lib/odoo` a la configuración generada y a `config/odoo.conf`. Se repitió la prueba desde cero y ahora el respaldo trae los archivos. Atención: una instalación que ya tenga datos con la configuración anterior los tiene en `/var/lib/odoo/.local/share/Odoo/filestore`; habría que moverlos antes de cambiar `data_dir`. No hay ninguna instalación así todavía.
- **Directorio en lugar de archivo.** La primera versión del script generaba el hash de la contraseña con un contenedor que montaba el archivo de configuración que aún no existía; Docker creó un directorio con ese nombre y el arranque falló. Ahora el hash se genera con `docker run` sin ese montaje.
- **Un comando de prueba fue bloqueado** por la verificación de seguridad de Claude Code: yo quería borrar a mano el filestore dentro del contenedor para simular un desastre. No lo reintenté por otra vía; lo reemplacé por borrar el bus por SQL y sobrescribir el adjunto. Consecuencia: la prueba no demuestra por sí sola que el filestore restaurado reemplace a uno borrado; sí demuestra que el respaldo contiene los archivos (listado del `tar`) y que la restauración completa deja todo funcionando.
- **El log de Odoo imprimía el secreto del webhook** al venir en la URL. Se resolvió con la cabecera (ver arriba).
- **La redirección HTTP a HTTPS apuntó a `https://localhost/`** sin el puerto 8443 de la prueba. Es un efecto de publicar el proxy en puertos no estándar solo para esta prueba; con 80/443 no ocurre.
- Mi script de traducción no manejaba bien un texto de ayuda partido en varias líneas; se agregó a mano.

### Pendiente o sin confirmar

- Certificados reales de Let's Encrypt: no se pueden probar sin un dominio público.
- Un servidor Linux real: todo se probó en Windows con Docker Desktop y Git Bash.
- El `docker-compose.yml` de desarrollo con la cabecera del secreto no se ejecutó; usa el mismo mecanismo que sí se probó en producción y su sintaxis valida.
- Copia de los respaldos fuera del servidor, límite de intentos de login, 2FA, bloqueo de IPs, TLS para el tráfico de los GPS, partición de la tabla de posiciones y conectar un servicio de monitoreo externo.
- Fase 0 del plan sigue sin respuesta; las fases 4 (pendientes), 5 y 6 dependen de ella.

### Estado del entorno de pruebas

Contenedores y volúmenes de desarrollo y de producción eliminados, y se borraron `.env.prod`, `config/odoo.prod.conf` y `backups/` de prueba.

## 2026-10-26 (quinta sesión): alertas y reporte de actividad diaria

La fase 0 del plan sigue sin respuesta. Para no frenar el proyecto implementé las fases 5 y 6 en su versión mínima, con valores por defecto que son **supuestos míos** y que se cambian en `Configuración > Ajustes > Alerts`.

### Qué se hizo

1. **Alertas** (`models/bus_alert.py`): tres tipos.
   - **Exceso de velocidad:** más de 80 km/h. Se evalúa al llegar cada posición; guarda la velocidad máxima y se cierra cuando el bus baja del límite.
   - **Bus sin señal:** un bus que reportó en las últimas 6 horas y lleva 10 minutos en silencio. Se cierra al volver a reportar. Los buses que llevan más de 6 horas sin reportar se consideran estacionados, no "sin señal".
   - **Parada larga:** detenido 15 minutos o más, lejos de cualquier parada de su ruta. Se cierra al moverse.
   - Un índice único de la base de datos impide dos alertas abiertas del mismo tipo para un bus.
   - Un cron revisa cada minuto las reglas que dependen del tiempo (sin señal y parada larga).
2. **Reporte de actividad diaria** (`models/bus_report.py`): vista SQL por bus y día con kilómetros, minutos en movimiento, minutos detenido y velocidad máxima; gráfico de barras, tabla dinámica y lista. La distancia solo cuenta tramos con el bus en movimiento (la deriva del GPS estacionado no suma kilómetros) y se saltan los huecos de más de 5 minutos sin señal.
3. **Interfaz**: menú `Alertas`, menú `Reportes > Daily Activity`, etiqueta roja con el tipo de alerta en cada bus de la lista del mapa en vivo, y tres ajustes nuevos.
4. **Traducción**: 35 textos nuevos en `i18n/es.po` (146 en total).
5. `docs/PLAN.md` y `README.md` actualizados.

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa | 53 tests, 0 fallos (19 tests nuevos: alertas, reporte y la lista del mapa con alertas) |
| Mutaciones: quitar el límite de 6 horas, impedir que moverse cierre la parada larga, contar la distancia también estacionado | La suite falló en 3 tests (uno por cada mutación); código restaurado |
| Revisión en Chrome con datos de ejemplo: lista de alertas, gráfico de actividad, mapa con la etiqueta "No signal" en el bus sin señal, pantalla de ajustes | OK, sin errores de consola |
| Traducciones cargadas: tipos de alerta y detalles ("Sin reportes hace 27 min", "Hasta 93 km/h (límite 80 km/h)") | OK |

### Problemas encontrados

- Un test del reporte falló por un error mío: `mapped('vehicle_id.name')` elimina duplicados. Las 3 filas sí se generaban; se corrigió el test.
- La primera versión de los tests de alertas comparaba horas con microsegundos contra horas con segundos exactos; se fijó el reloj de los tests al segundo.

### Limitaciones y supuestos

- **Los días del reporte son días UTC**, no de la hora local. Un recorrido nocturno puede repartirse entre dos días.
- El reporte depende de las posiciones guardadas: con la retención por defecto de 30 días no hay historial más antiguo.
- Las alertas no envían ningún aviso fuera de Odoo (correo, mensaje). Hay que mirar el menú `Alertas` o el mapa.
- Una parada larga solo se detecta si el bus tuvo movimiento registrado antes (dentro de la retención); un bus nuevo que nunca se movió no genera la alerta.
- No hay alerta de desvío de ruta: la ruta es una línea recta entre paradas y daría falsas alarmas.
- La landing no menciona las alertas ni el reporte nuevo.

### Pendiente

- Fase 0 (flota, hardware, hosting, pasajeros, alertas deseadas, idioma). Define los umbrales reales, si hace falta aviso por correo y si hay que particionar posiciones.
- Geometría real de las rutas, viajes con horario, puntualidad y estimación de llegada.
- Prueba con un GPS físico, prueba de carga, y lo pendiente de la fase 8.

### Estado del entorno de pruebas

Contenedores y volúmenes eliminados.

## 2026-10-26 (sexta sesión): respuestas de la fase 0 y plan nuevo

El cliente respondió la fase 0: los pasajeros solo ven los buses de una ruta y levantan quejas; la flota es administrable; el GPS son los celulares de los choferes; el sistema se aloja en Azure; las alertas salen por correo o push; los idiomas son español, inglés y, si se puede, quechua. La frecuencia del GPS se dejó a mi criterio.

### Qué se hizo

1. `docs/PLAN.md`: la fase 0 quedó respondida, con la recomendación de frecuencia (10 segundos en movimiento) y una tabla de volumen estimado de posiciones. Se agregaron las fases 9 a 14: celulares como GPS, portal de pasajeros, quejas, notificaciones por correo y push, idiomas y despliegue en Azure, con orden recomendado.
2. Decisiones guardadas en la memoria del proyecto.

No se escribió código en esta sesión.

### Puntos que hay que confirmar con el cliente

- País del cliente (define la ley de protección de datos, la zona horaria y la variante de quechua).
- Variante de quechua y quién la revisará.
- Si las notificaciones push son solo para el personal o también para los pasajeros.
- Si quien presenta la queja debe dejar un contacto obligatorio, opcional o ninguno.
- Qué hacer con las posiciones de los choferes fuera de turno: el celular debe dejar de reportar al terminar el turno.

### Riesgos anotados

- La tabla de volumen es una estimación mía; hay que medirla con la flota real.
- El chofer debe consentir por escrito el seguimiento de su celular.
- No puedo crear recursos en Azure por el cliente; solo dejar guías y plantillas que no podré probar.

## 2026-10-26 (séptima sesión): fase 9, celulares como GPS (trabajo detenido a mitad)

El cliente respondió las preguntas pendientes: país Ecuador (quechua: kichwa), push solo para el personal, contacto opcional en las quejas, y empezar por la fase 9. Esta sesión se detuvo a pedido del usuario antes de terminar la fase 9.

### Hecho y verificado

1. **Odoo crea los dispositivos en Traccar** (`bus.traccar.api.create_device`, botón `Register GPS in Traccar` en el bus): identificador aleatorio (`b-` + 16 caracteres hexadecimales), distinto por bus. El identificador solo lo ven los administradores, porque en el protocolo OsmAnd es la única credencial.
2. **Sección "Driver's phone"** en la ficha del bus: identificador, enlace de configuración y QR generado en el servidor (sin enviar el identificador a ningún servicio externo). El formato del enlace (`org.traccar.client://config?...`) no está documentado oficialmente y no se probó en un celular; el camino seguro es escribir la dirección y el identificador a mano.
3. **Ajuste nuevo** `GPS address for the phones` (`bus_tracking.gps_url`).
4. **Producción**: los celulares envían por HTTPS a `GPS_DOMAIN` (el proxy lo pasa al puerto 5055 de Traccar, sin publicarlo en el servidor); los puertos 5055 y 5023 ya no se abren al público; el panel de Traccar ya no se expone (queda comentado en `proxy/Caddyfile`). `scripts/init-prod.sh` ahora crea solo la cuenta de administrador de Traccar (contraseña aleatoria guardada en Odoo) y cierra el registro abierto. `.env.prod.example` pide `GPS_DOMAIN` en lugar de `TRACCAR_DOMAIN`.
5. **Tests**: 62 en total, 0 fallos (9 nuevos: registro del dispositivo, identificadores únicos, rechazo de doble registro, fallo de Traccar, enlace y QR, ocultar el identificador a usuarios sin permiso, y la creación de la cuenta de Traccar).
6. **Prueba de punta a punta con Traccar real** (dominios `localhost` y `gps.localhost`): el registro abierto quedó cerrado (HTTP 400 a un alta anónima); Odoo creó el dispositivo; una posición enviada por GET y otra por POST de formulario, ambas por HTTPS, llegaron a Odoo; el puerto 5055 no está publicado en el host; la API de Traccar no es alcanzable por el dominio GPS.
7. **Interfaz revisada en Chrome**: la ficha del bus con GPS registrado muestra identificador, enlace y QR; la de un bus sin GPS muestra el botón de registro y oculta esa sección. Sin errores de consola.
8. **Traducción**: 11 textos nuevos al español (157 en total).
9. `docs/PLAN.md`: recomendación de GPS corregida (precisión **Highest**; ver más abajo).

### Corrección a una recomendación anterior

Escribí que bastaba "alta precisión". La documentación oficial de Traccar Client dice que el intervalo por tiempo solo funciona con precisión Highest (o con distancia 0 en Android). Quedó corregido en el plan.

### Falta para cerrar la fase 9

- Escribir `docs/GUIA-CHOFER.md` (instalar la app, dirección, identificador, ajustes, batería sin restricción, cuándo iniciar y detener el turno, aviso de privacidad).
- Actualizar `docs/PRODUCCION.md`: ahora `GPS_DOMAIN` en lugar de `TRACCAR_DOMAIN`, puertos GPS cerrados, la cuenta de Traccar se crea sola, y el endurecimiento de los GPS por HTTPS ya no es una limitación.
- Actualizar `README.md` (cómo registrar el GPS de un bus).
- Prueba con un celular real durante 30 minutos con la pantalla apagada (no hecha: solo se simuló con peticiones HTTP).
- El `docker-compose.yml` de desarrollo sigue publicando el puerto 5055 sin cifrar; es solo para desarrollo.

### Siguiente

Fases 10 y 11 (portal de pasajeros y quejas), luego 12 (correo y push), 13 (idiomas: español, inglés y kichwa de Ecuador, con revisión de una persona hablante), 14 (Azure). País Ecuador: la ley de protección de datos aplicable debe confirmarla quien asesore legalmente al cliente.

### Estado del entorno

Contenedores y volúmenes eliminados; sin `.env.prod`, configuración de producción ni respaldos de prueba.

## 2026-10-26 (octava sesión): fase 9 cerrada y fase 10, portal de pasajeros

### Qué se hizo

1. **Fase 9, documentación**: `docs/GUIA-CHOFER.md` (instalar la app, ajustes recomendados, batería, turno, privacidad, qué hacer si falla), y `docs/PRODUCCION.md` y `README.md` actualizados al flujo nuevo (dominio `GPS_DOMAIN`, solo 80/443 abiertos, cuenta de Traccar automática, registro del GPS desde Odoo).
2. **Fase 10, portal público de pasajeros**:
   - `/rutas`: lista las rutas activas con la casilla nueva *Visible to passengers* y cuántos buses están en servicio.
   - `/rutas/<código>`: mapa con la ruta, sus paradas y sus buses en vivo (se actualiza cada 10 segundos), con lista de buses y su estado; en pausa si la pestaña no está visible.
   - `/rutas/<código>/buses.json`: solo nombre, posición, rumbo y estado. No sale patente, conductor, velocidad, identificadores ni historial (un test lo comprueba buscando esos datos en la respuesta).
   - Un bus que no reporta hace más de 15 minutos desaparece; entre 5 y 15 minutos se muestra como "sin señal".
   - Protección: 60 peticiones por minuto por IP (en memoria, por proceso, así que con varios procesos el tope real es mayor), caché de 5 segundos, rutas privadas o inexistentes responden 404, nombres y colores se escapan o validan (un color inválido no puede inyectar CSS).
   - Idiomas: español e inglés, elegidos según el navegador o con el selector, y recordados en una cookie. Kichwa no está: espera a la fase 13 y a una persona que lo revise.
   - La landing ahora lleva al pasajero a su ruta (botón principal "Ver los buses de mi ruta").
3. **Versionado de los estáticos públicos**: los enlaces a CSS y JS de la landing y del portal llevan `?v=<fecha de modificación>`. Se descubrió porque el navegador seguía mostrando un CSS viejo; en producción pasaría tras cada actualización porque Odoo sirve los estáticos con caché larga.
4. Traducción: 2 textos nuevos (159 en total).

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base limpia | 80 tests, 0 fallos (17 nuevos del portal: rutas visibles, 404, escape de HTML, color inválido, datos mínimos, buses viejos y ajenos, caché, límite de peticiones, idioma, estáticos versionados) |
| Revisión en Chrome: lista de rutas, mapa con dos buses, ruta privada oculta | OK, sin errores de consola |
| Ancho móvil de 390 px (iframe) | Sin desbordes (375/375 y 390/390) tras ajustar el encabezado |
| Inglés con `?lang=en` | OK |

### Problemas encontrados

- **Encabezado desbordado en móvil**: el logo con texto, el selector de idioma y el botón no cabían en 390 px; se oculta el texto del logo por debajo de 520 px (queda el ícono y su etiqueta de accesibilidad).
- **Caché del navegador** (ver arriba).
- **Dos tests míos mal escritos**: la cookie de idioma persistía en la sesión de prueba, y la segunda posición era idéntica a la primera.
- **Base de pruebas sucia**: dejé datos de ejemplo guardados en la base de desarrollo y los tests fallaron por rutas y buses repetidos. Las pruebas deben correr en una base nueva.
- **Idioma de las pruebas**: los tests comparan textos en inglés; si se carga el español en la base de pruebas fallan. El comando del README no lo carga.

### Pendiente

- Fase 9: prueba con un celular real.
- Fase 11 (quejas y reportes), fase 12 (correo y push), fase 13 (inglés ya está en el portal; falta el panel de gestión y kichwa con revisión), fase 14 (Azure).
- Geometría real de las rutas y estimación de llegada.
- Si el sistema crece a varios procesos, el límite de peticiones por IP debería pasar a un almacén compartido o al proxy.
- Los textos de la landing y del portal están en el código, no en el catálogo de traducción de Odoo.

### Estado del entorno

Contenedores y volúmenes eliminados.

## 2026-10-26 (novena sesión): fase 11, quejas y reportes

### Qué se hizo

1. **Modelo `bus.complaint`**: folio `Q-00001` con secuencia propia, ruta y bus opcionales, tipo (demora, trato, seguridad, limpieza, otro), descripción (máximo 2000 caracteres), estado (nueva, en revisión, resuelta), responsable, nota interna, idioma del pasajero y correo y teléfono opcionales. Los datos de contacto solo los leen los administradores.
2. **Formulario público `/quejas`** (y `/quejas/gracias`): la ruta preseleccionada llega por enlace desde la página de cada ruta; el selector de bus se filtra por ruta con un script pequeño (sin script, el selector muestra todos los buses con su ruta); español e inglés; los errores se muestran junto al campo y se conserva lo escrito.
3. **Protección contra abuso**: campo trampa, token firmado con tiempo mínimo de 3 segundos (los envíos instantáneos o con token falso se descartan en silencio y responden como si hubieran funcionado), token CSRF de Odoo, máximo 5 quejas por IP y hora, cuerpo máximo de 20 KB, y eliminación de caracteres NUL (Postgres los rechaza). Un formulario abierto más de 24 horas pide enviar de nuevo sin perder el texto.
4. **Panel**: menú `Quejas` con lista, formulario, botones *Iniciar revisión*, *Resolver* y *Reabrir*, y filtros por estado, asignación, ruta y tipo.
5. **Privacidad**: aviso en el formulario con los días de retención, y un cron diario borra el correo y el teléfono 90 días después de resolver la queja (ajustable en Ajustes; 0 los conserva).
6. Traducción: 37 textos nuevos (196 en total). Refactor interno: los ayudantes del portal pasaron a funciones compartidas.

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base limpia | 109 tests, 0 fallos (29 nuevos: modelo, permisos, retención, formulario, validaciones, antiabuso, idioma) |
| Mutaciones: desactivar el campo trampa y el token falso, el límite por IP y el permiso de los datos de contacto | La suite falló en 4 tests (uno por cada mutación); código restaurado |
| Chrome: enviar una queja real desde el formulario (ruta preseleccionada, bus filtrado, correo) y ver el folio | OK |
| Chrome: bandeja, ficha de la queja y botón *Iniciar revisión* (pasó a "En revisión" y se asignó) | OK, sin errores de consola |

### Problemas encontrados

- Cuatro tests míos mal escritos: la redirección llega como URL absoluta, y un caso usaba una descripción válida que no volvía a mostrar el formulario.
- Un comando de shell con demasiadas comillas falló dos veces sin ejecutarse; las plantillas y los scripts largos se escribieron con la herramienta de archivos.
- A la plantilla le faltaba el cierre `</odoo>` tras fusionar las partes; se detectó al validar el XML antes de correr Odoo.
- El folio de la prueba en Chrome fue Q-00075 porque las pruebas automáticas consumieron la secuencia en esa base; en una instalación nueva empieza en Q-00001.
- Como en las otras fases, las pruebas deben correr en una base limpia y sin idioma español cargado.

### Limitaciones

- Sin correo saliente todavía: el pasajero que deja su correo no recibe acuse ni respuesta (fase 12), y el equipo no recibe aviso de quejas nuevas.
- El límite de 5 quejas por IP y hora se cuenta por proceso (con varios procesos el tope real es mayor).
- Varias personas detrás de la misma IP (por ejemplo, un wifi público) comparten ese límite.
- No hay captcha: la protección es el campo trampa, el tiempo mínimo y el límite por IP.
- No hay una pantalla para que el pasajero consulte el estado de su queja con el folio (decisión de privacidad: evitar un buscador público de quejas).

### Pendiente

- Fase 12: correo (acuse, respuesta, aviso al equipo, alertas de buses) y notificaciones push al panel.
- Fase 13: panel en inglés y kichwa con revisión de una persona hablante.
- Fase 14: Azure.
- Fase 9: prueba con un celular real.
- Geometría real de las rutas y estimación de llegada.

### Estado del entorno

Contenedores y volúmenes eliminados.

## 2026-10-26 (décima sesión): adaptación a la Universidad Técnica de Ambato

El cliente aclaró que el sistema es para la ciudad de Ambato (Ecuador) y para los buses de la Universidad Técnica de Ambato (UTA).

### Qué se hizo

1. **Nombre configurable** (`bus_tracking.brand_name`, por defecto "Buses UTA", provisional): reemplaza al "Ruta Viva" que yo había inventado en la landing, el portal, el formulario de quejas, la pantalla de ingreso y los títulos de página. Se escapa al mostrarse. El logo sigue siendo un ícono genérico de bus.
2. **Mapa centrado en Ambato** (`bus_tracking.map_center`, por defecto -1.2417,-78.6167) en el mapa en vivo del panel y en el del portal, cuando no hay paradas ni buses que encuadrar. Un valor mal escrito o fuera de rango vuelve al de Ambato.
3. **Zona horaria de Ecuador**: el reporte de actividad diaria ahora corta los días en hora de `America/Guayaquil` y no en UTC (antes, un recorrido después de las 19:00 hora local caía en el día siguiente). El script de instalación fija esa zona para el administrador y la compañía.
4. **Límite de velocidad por defecto de 50 km/h** (urbano), antes 80. Sigue siendo configurable.
5. **Español de Ecuador (`es_EC`)** como idioma por defecto de la instalación en producción.
6. **Enlace opcional a la política de privacidad** de la universidad en el formulario de quejas (solo se acepta una dirección `http` o `https`).
7. **Copia de la landing** dirigida a la comunidad universitaria ("Estudiantes, docentes y personal ven por dónde va...").
8. Documentación: `docs/PERSONALIZACION.md` (qué ya viene ajustado, qué se cambia en Ajustes y qué debe aportar la universidad), contexto agregado a `docs/PLAN.md`, nota en `docs/DISENO.md` y `README.md`. Traducción: 7 textos nuevos (203 en total).

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base limpia | 121 tests, 0 fallos (12 nuevos: marca, centro del mapa, enlace de privacidad, límite por defecto, días locales del reporte) |
| El reporte reparte un recorrido de las 22:00 y las 00:30 hora local en dos días distintos | OK |
| Chrome: portal con una ruta sin paradas | El mapa abre sobre Ambato; el nombre "Buses UTA" aparece en el encabezado |
| Chrome: landing con el texto nuevo y el botón "Ver los buses de mi ruta" | OK |
| Idioma `es_EC` | Usa el catálogo en español (etiquetas traducidas) |
| Hallazgo: idiomas disponibles en Odoo 16 | `es_EC` sí; quechua/kichwa no (Babel sí conoce `qu_EC`) |

### Problemas y advertencias

- **La foto de la portada no es de Ambato**: muestra un paradero de otra ciudad con un letrero en portugués. Las tres fotos del proyecto deben reemplazarse por fotos propias de la universidad (guía en `docs/PERSONALIZACION.md`).
- **El nombre "Buses UTA" y el aviso de privacidad son provisionales**: la universidad debe aprobar el nombre y entregar logo y manual de marca, y su área legal debe revisar el aviso frente a la ley de protección de datos de Ecuador. Yo no puedo dar ese criterio legal.
- **El límite de 50 km/h** es mi supuesto urbano; hay que contrastarlo con la normativa vigente y con las vías reales de cada ruta.
- Un test mío falló porque el orden de los atributos del enlace de privacidad en el HTML no era el que yo suponía; se corrigió el test.
- Otra vez se evitó la shell para scripts largos (se escribieron como archivos y se borraron al terminar), porque los comandos con muchas comillas fallaban sin ejecutarse.

### Pendiente

- Fase 12 (correo y push): hay que confirmar con el área de tecnología de la UTA el servidor de correo institucional.
- Fase 13: kichwa en el portal con revisión de una persona hablante y acuerdo sobre la variante.
- Fase 14: Azure (región más cercana a Ecuador, a confirmar).
- Cargar las rutas y paradas reales de los campus, y probar con un celular real.

### Estado del entorno

Contenedores y volúmenes eliminados.

## 2026-10-26 (undécima sesión): fase 12, correo y notificaciones push

El cliente no respondió qué correo usará la universidad; se avanzó con el servidor de correo estándar de Odoo (configurable) y un buzón de pruebas local (Mailpit).

### Qué se hizo

1. **Cola de notificaciones** (`bus.notification`): las alertas de bus y las quejas nuevas se encolan al ocurrir y un cron cada minuto las convierte en correos y push. Así un servicio lento no retrasa la llegada de una posición ni de una queja. Varios eventos del mismo minuto llegan en un solo resumen por persona (máximo 20 filas).
2. **Preferencias por administrador** (en su perfil): correo, push, y cada tipo de alerta y quejas. Los textos salen en el idioma y la hora local de cada persona.
3. **Quejas**: aviso al equipo (sin datos de contacto), acuse automático al pasajero con solo el folio y en su idioma, asistente *Responder al pasajero* y historial (chatter) con el seguimiento de estado y responsable. El módulo ahora depende de `mail`.
4. **Push web**: página *Notificaciones en este dispositivo*, registro de dispositivos, claves VAPID creadas solas, cifrado RFC 8291, lista de servicios push permitidos, y borrado de suscripciones caducadas.
5. **Infraestructura**: imagen propia de Odoo (`docker/odoo/Dockerfile`) con `pywebpush`; Mailpit en el `docker-compose.yml` de desarrollo; el de producción construye la misma imagen.
6. Ajuste *Sender address for notifications* y `docs/CORREO.md`. Traducción: 81 textos nuevos (284 en total).

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base limpia | 155 tests, 0 fallos (34 nuevos: cola, resúmenes, preferencias, receptores, acuse, respuesta, push, endpoints) |
| Mutaciones: aceptar cualquier dirección push, incluir lo que escribió el pasajero en el acuse, avisar a todos sin mirar preferencias | La suite falló en 4 tests (uno por defecto por mutación); código restaurado |
| Cifrado push: el mensaje se descifra con la clave del navegador y la firma VAPID lleva la clave pública correcta | OK |
| Mailpit con el cron real: un exceso de velocidad llegó al administrador, en español, con la hora local de Ecuador y el enlace correcto | OK |
| Mailpit: una queja generó el aviso al equipo (sin correo ni teléfono del pasajero) y el acuse al pasajero (solo el folio) | OK |
| Mailpit y panel: respuesta de un administrador llegó al pasajero, quedó en el historial, y el estado y el responsable se rastrearon | OK |
| Página de notificaciones en Chrome | Carga y detecta que el navegador y el servidor admiten push; el botón de activar no se pulsó |

### Problemas encontrados

- **`pip install pywebpush` dejó a Odoo sin arrancar.** Instaló `cryptography` 50, que rompe el `pyOpenSSL` 20 de la imagen de Odoo 16 (`module 'lib' has no attribute 'GEN_EMAIL'`). Se corrigió fijando `cryptography==3.3.2` y usando `pywebpush` 1.14.1 (la serie 2.x exige `aiohttp` y `cryptography>=46`). Se comprobó que el cifrado funciona con esas versiones. El Dockerfile lo explica para que nadie lo actualice a ciegas.
- **Odoo envía una invitación a cada usuario nuevo**, y mis tests contaban ese correo como si fuera mío; ahora lo excluyen.
- **Defecto real hallado por un test**: en el asistente de respuesta `html_escape(...)` devuelve `Markup` y `.replace('\n', '<br/>')` escapaba el `<br/>`, de modo que el pasajero habría visto la etiqueta como texto. Corregido.
- `mail.send()` borra el correo enviado (`auto_delete`), así que los tests detienen el envío real para poder leer los correos.
- Un script de mutaciones usó una sintaxis de la shell de Git Bash dentro de Windows y no ejecutó los tests; se reescribió sin esa dependencia (el código quedó restaurado).
- Con `mail` instalado aparece el menú "Conversaciones" de Odoo en la barra superior; es inofensivo pero no es parte del sistema.

### Limitaciones y pendientes

- El correo no se probó con un servidor real de la universidad (solo con Mailpit); falta confirmar con su área de tecnología el servidor, el puerto y si permite una cuenta de servicio.
- La entrega de un push a un navegador real no se probó: requiere que una persona acepte el permiso del navegador.
- Un correo que falla puede conservar la dirección del pasajero hasta que se borre; conviene revisar los correos fallidos.
- Sin horario de silencio por persona ni destinatarios por ruta.
- iPhone: el push solo funciona con el sitio agregado a la pantalla de inicio.
- Fases pendientes: 13 (kichwa), 14 (Azure), prueba con un celular real, geometría de rutas, estimación de llegada, prueba de carga.

### Estado del entorno

Contenedores y volúmenes eliminados.

## 2026-10-26 (duodécima sesión): recorridos oficiales de la UTA

El cliente pidió que rutas, conductores y todo lo demás salgan del documento oficial `RECORRIDOS-INSTITUCIONALES-2025.pdf`.

### Qué se hizo

1. **Lectura del PDF** (`scripts/roster_from_pdf.py`, requiere `pymupdf`): extrae cada tabla por la posición de sus celdas, clasifica los tramos (viaje, espera, almuerzo), detecta origen y destino, asigna cada viaje a una línea, repara los caracteres dañados (Ñ, Í) y lista las anomalías del documento. Genera un JSON en `data/` (la carpeta no se versiona porque el documento nombra a los conductores).
2. **Modelo nuevo**: recorrido (`bus.service`) y tramo (`bus.service.leg`), con los días en que rige (lunes a viernes por defecto), horas de trabajo, calles oficiales y observaciones del documento.
3. **Importador repetible** (`bus.service._import_roster`): crea o actualiza líneas, paradas, buses, conductores (contactos con etiqueta *Chofer*) y recorridos. No duplica, conserva las coordenadas y los días ya corregidos, y reemplaza los tramos. Disponible como asistente en el panel y como `scripts/import-roster.sh`. Se monta `data/` como solo lectura en los dos `docker-compose`.
4. **La línea de cada bus sale de su horario**: un cron cada minuto le asigna la línea del tramo vigente (con márgenes de 45 minutos antes del primer viaje y 15 después del último).
5. **Panel**: `Flota > Recorridos (documento oficial)` con el estado de cada recorrido ahora y su tramo vigente; menú para importar.
6. **Portal**: *Horario de hoy* en la página de cada línea (próximas salidas por origen y destino, hasta cinco por sentido, hora de Ecuador, sin conductores).
7. Traducción: 69 textos nuevos (353 en total). Documentación: `docs/RECORRIDOS.md`.

### Lo que contiene el documento (resultado real de la importación)

11 recorridos (buses 03 al 12 y 14), 123 tramos (98 viajes, 17 esperas, 8 almuerzos), 11 conductores, 4 líneas: Troncal (80 viajes), Izamba, Pelileo y Píllaro (6 cada una), y 14 paradas (campus Ingahurco, Huachi y Querochaca, más Izamba, Pelileo y Píllaro repartidas en las líneas).

### Qué se verificó

| Prueba | Resultado |
|---|---|
| Suite completa en una base limpia | 182 tests, 0 fallos (27 nuevos: importación, repetición sin duplicar, lo corregido que sobrevive, validaciones, asistente, línea según la hora, márgenes, días sin servicio, portal con horario) |
| Mutaciones: quitar el margen antes del primer viaje, no reemplazar los tramos al reimportar, no filtrar las salidas ya pasadas, no actualizar la línea del bus | La suite falló en 9 tests; código restaurado |
| Importación del documento oficial real en una base de desarrollo | 4 líneas, 14 paradas, 11 conductores, 11 buses, 11 recorridos, 123 tramos, 9 observaciones |
| Panel con los datos reales a las 18:37 (hora de Ecuador) | 3 recorridos "en viaje" con su tramo vigente (R02, R04 y R09), que es lo que dice el documento para esa hora |
| Portal: lista de líneas y *Horario de hoy* de la Troncal con los datos reales | Salidas de las 19:10 en adelante, por origen y destino |

### Problemas encontrados

- **El texto extraído del PDF salía mezclado** (celdas con distintas fuentes): se extrajo cada celda por su posición en la página.
- **Hallazgos del documento** (en `docs/RECORRIDOS.md`): errata "CAMPUS IGAHURCO", solapes de horario en dos recorridos, almuerzos listados después del último viaje, un tramo repetido, un tramo que nombra un solo lugar, y tres recorridos sin horas de trabajo ni fecha legibles.
- **`any` no existe en los dominios de Odoo 16**: se escribió `service_ids.active`.
- **Un servicio archivado**: mi primera versión dejaba al bus sin línea; ahora el bus deja de estar gobernado por el horario y conserva la línea que el equipo le dio.
- **Días de la semana sin traducir**: los nombres venían de una variable y Odoo no los extrae; ahora son textos traducibles y se ven "Lun, Mar, Mié, Jue, Vie".
- **El mapa del portal parecía mal ajustado**, pero era mi propia herramienta de prueba: el "scroll" pasaba sobre el mapa y su rueda lo alejaba. Al recargar sin tocarlo abre bien (zoom 11). Agregué de todos modos un reajuste cuando cambia el tamaño del contenedor.
- Git Bash volvió a convertir una ruta (`/mnt/data/...`) en una de Windows al pasarla en una variable; el script ahora pasa solo el nombre del archivo.

### Limitaciones y supuestos

- **Los días en que rige cada recorrido son un supuesto** (lunes a viernes): el documento solo trae fechas de elaboración.
- **Las coordenadas de los campus son aproximadas** (OpenStreetMap); la de Ingahurco es la menos segura. El mapa y la detección de llegadas dependen de ellas.
- La ruta se dibuja como línea recta entre campus; las calles oficiales están como texto en cada tramo.
- La agrupación en cuatro líneas es una decisión mía, no del documento.
- Los nombres de los conductores quedan en la base de datos como contactos; el portal público no los muestra, pero la universidad debe validar este tratamiento.
- Aún no hay informe de puntualidad ni alerta de recorrido no iniciado.

### Pendiente

- Confirmar con la universidad los días de cada recorrido, las coordenadas de los campus y las anomalías del documento.
- Informe de puntualidad y alerta de recorrido no iniciado (necesitan posiciones reales).
- Fase 13 (kichwa), fase 14 (Azure), prueba con un celular real, geometría de cada tramo.
- Si la universidad entrega su escudo y colores, aplicarlos (`docs/PERSONALIZACION.md`).

### Estado del entorno

Contenedores y volúmenes eliminados. `data/roster_2025.json` queda en la carpeta del proyecto (no versionada) con los datos del documento.

## 2026-10-27 (decimotercera sesión): trazados por calle, viajes, puntualidad y más

### Qué se hizo

1. **Trazados por calle** (`docs/TRAZADOS.md`): `scripts/fetch_osm.py` y `scripts/build_paths.py` convierten las calles escritas del documento en geometría real con OpenStreetMap y OSRM. 34 trazados, uno por texto de recorrido; los 98 viajes quedaron enlazados. Modelo `bus.path` con origen (calculado, grabado o a mano), confianza, verificado y la acción de grabar desde un viaje real (ajuste a calles de las posiciones GPS). El mapa del panel y el portal dibujan las calles. Comprobado en el navegador: `/rutas/TRONCAL` dibuja el trazado, sin errores de consola.
2. **Viajes con horario** (`bus.trip`): un viaje por tramo y día, creado por un cron; detecta salida y llegada reales con las posiciones (radio del origen y del destino) y calcula demora y puntualidad (tolerancia de 5 min, configurable). Menú `Reportes > Puntualidad (viajes)` con lista, tabla dinámica y gráfico.
3. **Alertas nuevas**: recorrido no iniciado (10 min después de la hora, una por bus) y desvío de ruta (solo con trazados grabados o verificados).
4. **Estimación de llegada** a la próxima parada, en el portal.
5. **Reproducción de un viaje** en el mapa (`bus_tracking.trip_replay`, botón en cada viaje, x1 a x64).
6. **Notificaciones**: horario de silencio por persona (puede cruzar la medianoche) y filtro por rutas. Durante el silencio no se envía nada; las alertas siguen en el menú.
7. **Kichwa en el portal**: borrador mío con textos básicos, marcado "borrador", que nunca se elige solo desde el navegador; lo que falta cae al español. Necesita revisión de una persona hablante antes de publicarse.
8. **Tests**: 214 en total, 0 fallos (32 nuevos en `tests/test_paths_trips.py`).

### Problemas encontrados

- Overpass rechazó (502, 406) la descarga de toda la zona; se pidieron solo las calles del documento.
- La primera versión eligió cruces en calles homónimas de otras zonas (Píllaro a Huachi salía con 133 km). Se resolvió con el corredor y la elección por distancia total; lo que aún contradice los tiempos del documento cae a la vía más rápida y se marca de confianza media.
- Los acentos rotos del PDF y los puntos sueltos ("AV.", "M.") partían mal los nombres; corregido.
- Los heredocs de Git Bash fallan con ciertas comillas; se usaron las herramientas de archivo.

### Limitaciones

- **Ningún trazado está verificado en terreno.** Hace falta que un bus recorra cada trazado.
- Las coordenadas de los campus siguen siendo aproximadas.
- Push, correo institucional y celular real como GPS siguen sin probarse en entorno real.
- La estimación de llegada usa la velocidad del horario, no el tráfico real.
- Los trazados que pasan dos veces por la misma calle pueden confundir la posición a lo largo del trazado.
- Las cadenas nuevas de la interfaz del panel aún no están en `i18n/es.po`.

### Estado del entorno

Stack levantado con la base `buses` (roster y trazados importados), puerto 8070. Base `buses_test` creada para los tests.


## 2026-10-27 (decimocuarta sesión): simplificación del sistema

### Qué se hizo

Por pedido del cliente, el sistema quedó con lo mínimo que se pueda defender.

1. **Menú**: Mapa en vivo; *Administración de Buses* (Buses, Recorridos, Rutas con sus paradas); Quejas (sin botón de crear: solo las crea el portal público; el administrador cambia su estado); Reportes (Velocidad, Sin señal, Paradas largas, Desvíos de ruta, Llegada a paradas); Configuración (Ajustes, Notificaciones en este dispositivo). Los nombres del menú están en español en el código.
2. **Recorridos** pasó a ser un horario simple (`bus.schedule`: bus, ruta, salida, llegada). El portal muestra las salidas que faltan hoy.
3. **Desvío de ruta** se mide contra la línea que une las paradas de la ruta. Sin trazados por calle.
4. **Notificaciones**: solo push, a todos los administradores con un dispositivo suscrito. Un cron de un minuto envía las alertas nuevas (`bus.alert.notified`).
5. **Tests**: 127, 0 fallos. Un test atrapó un error real: un bus sin ruta rompía el desvío.

### Eliminado

Roster oficial y su importación, trazados por calle (OSM/OSRM) y sus scripts, viajes y puntualidad, alerta de recorrido no iniciado, estimación de llegada, reproducción de viajes, reporte de actividad diaria, cola de notificaciones, correo, acuses y respuestas a quejas, preferencias de notificación por persona (silencio, filtro por ruta), importación de dispositivos de Traccar, lista de dispositivos push, historial de quejas con chatter. Documentos `RECORRIDOS.md`, `TRAZADOS.md` y `CORREO.md`.

### Pendiente

- `i18n/es.po` y `.pot` aún traen textos de lo eliminado.
- La copia anterior del código quedó en la carpeta temporal de la sesión (no hay git).


## 2026-10-28: Recorridos automáticos

- `bus.schedule` (horario manual) se reemplazó por `bus.run`: el sistema abre un recorrido cuando el bus sale de la primera o la última parada de su ruta y lo cierra cuando entra a la otra. Si vuelve al origen sin llegar, el recorrido se descarta; uno abierto más de 12 horas también.
- Se quitó la sección "Horario de hoy" del portal público: sin horario planificado no hay qué mostrar.
- Límites: usa solo la primera y la última parada en orden; no distingue conductores; una ruta con menos de 2 paradas no genera recorridos.
- Tests: 148, 0 fallos.


## 2026-10-28: pulido del diseño

- Se conservó la identidad (papel, tinta, verde ruta, amarillo señal, rojo bus; Bricolage Grotesque y Atkinson Hyperlegible).
- Portal: punto de estado en cada ruta y en cada bus de la lista (verde en movimiento, amarillo detenido, rojo sin señal), tarjetas blancas, línea sobre el pie, `prefers-reduced-motion` respetado. Nuevo token `--bus-ok`.
- Panel de Odoo (`backend.css`): hoja de formulario como tarjeta, títulos de grupo con subrayado amarillo, encabezados de lista con línea de tinta, fila resaltada al pasar, insignias de estado con los colores de la marca, foco visible, página de Ajustes y barra lateral del mapa en vivo.
- Landing: pasos de "Así llega un bus" sin jerga (Traccar, Odoo).
- Tests: 150, 0 fallos.
- **Sin verificar a ojo:** el panel de Odoo (hace falta iniciar sesión; no se creó un usuario de prueba) y los anchos de móvil de esta sesión.


## 2026-10-28: informe de calidad en PDF

### Qué se hizo

Se generó el informe técnico de calidad del sistema (`docs/calidad/Informe_calidad_rastreo_buses.pdf`, 25 páginas, copia en `Documentos` como `Manzano_Rodriguez_informeCalidad_rastreoBuses.pdf`) con la estructura del taller de ACS de la UTA que sirvió de modelo (`Manzano_Rodriguez_trabajoFinalU3.pdf`): objetivos, escenario, diseño y ejecución de pruebas, métricas, análisis estadístico, ISO 25010, ISO 12207, CMMI, decisión, conclusiones, referencias y anexos. Todas las cifras salen de pruebas ejecutadas hoy, no escritas a mano.

Código nuevo en `qa/`: `qa_suite.py` (42 casos en vivo: 12 funcionales, 22 de error, 7 de rendimiento, 1 de usabilidad), `auditoria.py` (1000 peticiones aleatorias con semilla fija sobre 15 áreas), `metricas.py`, `graficos.py`, `informe_lib.py`, `generar_informe.py` y `ejecutar_todo.sh`. Las evidencias están en `docs/calidad/evidencias/`.

### Resultados

| Conjunto | Pruebas | Fallos |
|---|---|---|
| Pruebas de Odoo (con coverage.py) | 150 | 0; cobertura 93,8 % (sentencias y ramas) |
| Suite en vivo | 42 | 3 (7,1 %) |
| Auditoría aleatoria | 1000 | 57 (5,7 %): 25 respuestas HTTP 500 y 32 posiciones imposibles guardadas |

Rendimiento (servidor de un solo proceso): 0,04 s en promedio en uso normal; con 20 hilos, media 0,39 s, p95 1,6 s y 39 peticiones por segundo (se necesitan 10 para 100 buses). Integridad concurrente correcta (1 de 20 envíos idénticos; 60 de 60 de un mismo bus).

### Defectos nuevos (abiertos, no se corrigieron)

- DEF-008: se guardan coordenadas imposibles (latitud 95°).
- DEF-009: latitud no numérica produce HTTP 500 en el webhook.
- DEF-010: hora GPS inválida produce HTTP 500 en el webhook.

Los tres están en la validación de la posición (`bus_vehicle._apply_position`, `utils.parse_traccar_dt`). Decisión del informe: apto para un piloto controlado; para producción abierta faltan cerrarlos y probar con un celular real.

### Problemas encontrados

- Dos corridas de la suite se pisaron (una quedó huérfana al cerrarse la shell) y falsearon un resultado; se descartaron y se repitió todo desde un servidor reiniciado.
- Los límites de uso (60 consultas por minuto, 5 quejas por hora) viven en memoria: la suite y la auditoría esperan o reinician el servidor antes de medir.
- Dos pruebas mías compartían buses con otra y daban conteos falsos; se separaron.

### Limitaciones

- No se ejecutó SonarQube (el modelo lo incluía); figura como enfoque faltante.
- El GPS se simuló con peticiones HTTP; no hay celular real ni push entregado a un navegador.
- Las 16 mutaciones manuales citadas salen de esta bitácora, no se repitieron hoy.
- El valor de 50 % de CV para "desviación alta" es una decisión del informe.

### Estado del entorno

Contenedor `qa-odoo` y base `buses_qa` eliminados. Para repetir: Anexo B del informe.


## 2026-10-28: carpeta `docs/calidad` con toda la documentación de calidad

### Qué se hizo

Se organizó `docs/calidad/` como el lugar donde va toda la documentación de pruebas y calidad, con el formato del Taller de la Unidad 2 (`Taller ACS.pdf`) y el informe de la Unidad 3. Se agregaron 12 documentos: un índice (`README.md`) y 11 numerados: política y alcance con RACI y flujo, reglas de negocio y estándares de interfaz, plan y casos de prueba, resultados y cuadro de mando, registro de defectos con causa raíz, lluvia de ideas categorizada, Pareto, Ishikawa, cumplimiento de ISO 25010, 12207, CMMI y 29119-3, evidencias y reproducción, y elementos del ACS (qué existe, qué falta, qué mejorar).

Los documentos 03, 04, 05 y 07 y las figuras de Pareto e Ishikawa los escribe `qa/generar_docs.py` desde las evidencias y desde `qa/datos_calidad.py`, para que las cifras coincidan con el PDF.

### Qué se verificó

- Los totales de la lluvia de ideas (94 ideas: 57 hechas, 14 retiradas, 2 descartadas, 21 pendientes) se contaron por script sobre las tablas, y las sumas de ISO 25010 (31 subcaracterísticas), 12207 (30 procesos) y CMMI (22 áreas) también.
- El Pareto de problemas de la construcción clasifica los 53 problemas de la bitácora: pruebas y su entorno 16, herramientas 12, entorno y dependencias 10, datos y supuestos 8, lógica y diseño 7.

### Hallazgos de esta tarea

- La lluvia de ideas es una **reconstrucción** a partir del plan, la bitácora y los pedidos del cliente, no el acta de una sesión; así consta en el propio documento.
- El RACI es una **propuesta** (roles tomados del Taller de la Unidad 2), a confirmar por el equipo.
- El CMMI quedó en "nivel 2 en consolidación" (REQM y PPQA parciales): se corrigió el PDF, que decía "respaldado".
- Siguen faltando el análisis estático (SonarQube, flake8, pylint-odoo) y la integración continua.

### Pendiente

- Cerrar DEF-008 a DEF-010 y regenerar la documentación.
- Hacer una sesión real de lluvia de ideas con la universidad y registrar el acta.


## 2026-10-28: guion de defensa del proyecto

### Qué se hizo

Se escribió `docs/GUION_DEFENSA.md`: guion de 15 minutos más 5 de preguntas, con apertura, problema y motivo, demostración, arquitectura, decisiones, proceso, calidad, estándares, defectos abiertos y cierre. Incluye 15 preguntas difíciles con respuesta, una tabla de cifras para memorizar y una lista de cosas que no hay que afirmar.

### Qué se verificó

Todas las cifras se tomaron de `docs/calidad/` (ejecución del 28-oct-2026). Se comprobó que 8 de las 12 metas del cuadro de mando se cumplen y que los 60 fallos (3 de la suite y 57 de la auditoría) coinciden con el Pareto.

### Limitaciones

- El motivo del proyecto (sección 1) se redactó con los datos del plan y de las decisiones del cliente; los documentos no registran una anécdota real de pasajeros, así que se dejó una nota para añadirla.
- Las respuestas sobre costo de Azure y sobre el reparto de trabajo con Claude Code son orientativas y las debe ajustar quien defiende.
- Si se cierran DEF-008 a DEF-010 antes de la defensa, hay que actualizar las secciones 6, 8 y 9 y la pregunta 2.


## 2026-10-28: el pipeline de calidad se prepara solo

### Qué se hizo

`qa/ejecutar_todo.py` (nuevo) crea Postgres, la base `buses_qa`, el servidor `qa-odoo` y la base desechable de las pruebas de Odoo, ejecuta las pruebas con cobertura, la suite en vivo, la auditoría y las métricas, y acepta un paso suelto (`odoo`, `suite`, `auditoria`, `metricas`) o `--limpiar`. Funciona en `cmd`, PowerShell y Git Bash. `qa/ejecutar_todo.sh` ahora solo lo llama. Antes había que crear la base y el servidor a mano y el script fallaba con `ConnectionRefusedError` si `qa-odoo` no existía.

### Qué se verificó

Ejecución completa desde cero (sin `qa-odoo` ni `buses_qa`), con la salida en otra carpeta: 150 pruebas de Odoo, 0 fallos, cobertura 94 %; suite en vivo 39 de 42 (los mismos DEF-008 a DEF-010); auditoría 943 de 1000 (5,7 %).

### Limitaciones

- La auditoría dio 25 respuestas 5xx y 32 posiciones imposibles, como en el informe; la suite y la auditoría cuentan 27 y 33 en total.
- Los tiempos varían entre ejecuciones (la media de la auditoría fue 0,0585 s contra 0,037 s del informe), así que las cifras del PDF no se actualizaron.
- Una ejecución nueva sobre `docs/calidad/evidencias/` reemplaza las evidencias del informe.
- `qa-odoo` y `buses_qa` quedan creados al terminar; `--limpiar` los elimina.
