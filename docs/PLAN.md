# Plan de implementación: rastreo de buses (Odoo 16 + Traccar)

Estado: **[HECHO]** construido y probado, **[HECHO*]** construido pero sin probar en entorno real, **[PENDIENTE]** no iniciado.

## Contexto del cliente

El sistema es para los buses de la **Universidad Técnica de Ambato (UTA)**, en **Ambato, Ecuador**. Por eso: zona horaria `America/Guayaquil`, español de Ecuador, mapa centrado en Ambato, nombre configurable (por defecto "Buses UTA", provisional), límite de velocidad urbano de 50 km/h, kichwa como lengua originaria. Detalle en `docs/PERSONALIZACION.md`.

## Fase 0. Decisiones previas **[RESPONDIDA el 2026-10-26]**

| Tema | Decisión del cliente | Qué implica |
|---|---|---|
| Pasajeros | Solo pueden ver los buses de una ruta y levantar una queja o reporte | Portal público sin login: elegir ruta, ver el mapa con sus buses y paradas, enviar queja. No ven reportes, alertas, conductores ni historial. |
| Cantidad de buses | Administrable | Sin tope fijo; el administrador crea y desactiva buses. El tamaño del servidor se calcula con la tabla de volumen de abajo. |
| Frecuencia del GPS | La recomiendo yo | Ver recomendación abajo. |
| GPS | Tableta Android en el bus (app Expo `apps/conductor-tablet`; OsmAnd a Traccar) | Sustituye Traccar Client. Hay que confirmar chip GPS, batería, datos y consentimiento del chofer. |
| Alojamiento | Azure | Máquina virtual Linux con Docker (recomendada), ver fase 14. |
| Alertas | Correo o notificación push | Fase 12. |
| Idiomas | Español, inglés y, si se puede, quechua | Fase 13. Quechua necesita una variante definida y revisión de una persona hablante. |

### Recomendación de frecuencia del GPS

**Cada 10 segundos en movimiento**. La app de tableta usa `expo-location` en alta precisión, intervalo 10 s, cola sin red y OsmAnd hacia Traccar. El mapa se refresca cada 10 segundos. Si la batería no aguanta, 15 a 20 segundos es aceptable.

Volumen estimado de posiciones con 10 horas de servicio al día y 10 segundos de intervalo (estimación mía, no medida):

| Buses | Posiciones por día | En 30 días (retención por defecto) | Espacio aproximado en Postgres |
|---|---|---|---|
| 20 | 72 mil | 2,2 millones | menos de 1 GB |
| 50 | 180 mil | 5,4 millones | ~1,5 GB |
| 100 | 360 mil | 10,8 millones | ~3 GB |
| 300 | 1,1 millones | 32 millones | ~9 GB; conviene partir la tabla por mes |

El consumo de datos por celular es bajo (del orden de 2 MB por turno).

Advertencias sobre usar el celular del chofer:

- En Android hay que dejar la app sin restricción de batería y con el servicio en primer plano; en iPhone el seguimiento en segundo plano es menos fiable.
- Conviene un soporte con carga en el bus y un plan de datos acordado.
- El seguimiento solo debe estar activo durante el turno y el chofer debe saberlo y aceptarlo por escrito. Depende de la ley de datos personales del país (no sé cuál es; por favor confírmalo).

## Fase 1. Infraestructura **[HECHO]**

- `docker-compose.yml` con Postgres 15, Odoo 16 y Traccar.
- `.env.example` con `DB_PASSWORD`, `WEBHOOK_SECRET`, `ODOO_PORT`.
- Criterio de aceptación: `docker compose up -d` levanta los tres servicios. Verificado.

## Fase 2. Modelo de datos y seguridad **[HECHO]**

- Modelos: `bus.vehicle`, `bus.route`, `bus.route.stop`, `bus.position`, `bus.stop.arrival`.
- Grupos User y Manager, permisos por modelo.
- Criterio de aceptación: el módulo se instala en una base limpia sin errores. Verificado.

## Fase 3. Integración con Traccar

| Tarea | Estado |
|---|---|
| Webhook `/bus_tracking/traccar/webhook` con secreto, validación y deduplicación | HECHO (probado con curl: 403/200/400) |
| Cron de respaldo cada minuto contra `/api/positions` | HECHO (probado con Traccar real) |
| Importar dispositivos de Traccar como buses | HECHO (probado con Traccar real) |
| Reenvío Traccar -> Odoo por `FORWARD_TYPE=json` + `FORWARD_URL` | HECHO (probado: POST 200; `forward.json` ya no existe en Traccar 6) |

Criterio de aceptación: un GPS asignado a un bus aparece en Odoo con posición actualizada en menos de 10 s. Validado con un GPS simulado por protocolo OsmAnd (puerto 5055); **falta repetirlo con un GPS físico o teléfono real.**

## Fase 4. Operación y mapa

| Tarea | Estado |
|---|---|
| Mapa en vivo con filtro por ruta, estado del bus y trazado de 4 h | HECHO (probado en Chrome, sin errores de consola) |
| Detección de llegada a paradas y reporte de llegadas | HECHO |
| Ruta dibujada siguiendo las calles | HECHO*: calculada con OpenStreetMap y OSRM, 34 trazados (`docs/TRAZADOS.md`); falta grabarlos y verificarlos con un bus real |
| Viajes con horario (`bus.trip`) y puntualidad | HECHO (probado con posiciones simuladas) |
| Estimación de llegada a la próxima parada | HECHO (portal; usa la velocidad del horario) |

## Fase 5. Alertas **[PARCIAL]**

Las reglas y sus umbrales son un supuesto mío (la fase 0 no se respondió) y se cambian en `Configuración > Ajustes`.

| Alerta | Regla por defecto | Estado |
|---|---|---|
| Exceso de velocidad | Más de 50 km/h (urbano; verificar con la normativa de tránsito vigente y con las vías reales de cada ruta); se cierra al bajar del límite y guarda la velocidad máxima | HECHO |
| Bus sin señal | Un bus que reportó en las últimas 6 horas y lleva 10 minutos en silencio; se cierra al volver a reportar | HECHO |
| Parada larga fuera de paradero | Detenido 15 minutos o más, lejos de cualquier parada de su ruta; se cierra al moverse | HECHO |
| Desvío de ruta | Más de 150 m del trazado por 3 min; solo con trazados grabados o verificados | HECHO |
| Recorrido no iniciado | 10 min después de la hora planificada, una alerta por bus | HECHO |
| Aviso por correo o mensaje | Hoy las alertas se ven en el menú `Alertas` y como etiqueta roja en el mapa en vivo | PENDIENTE (depende del canal que se elija) |

## Fase 6. Reportes **[PARCIAL]**

| Reporte | Estado |
|---|---|
| Actividad diaria por bus: kilómetros, minutos en movimiento y detenido, velocidad máxima (gráfico, tabla dinámica y lista) | HECHO |
| Llegadas a paradas | HECHO (desde antes) |
| Puntualidad contra horario | HECHO (`Reportes > Puntualidad`) |
| Historial reproducible de un viaje en el mapa | HECHO (botón Replay; sin probar con viajes reales) |

## Fase 7. Calidad **[PARCIAL]**

- **[HECHO]** Tests automatizados: 53 tests (`addons/bus_tracking/tests/`): ingesta, deduplicación, llegadas a paradas, purga, alertas, reporte de actividad, cliente de Traccar con respuestas simuladas, webhook, salud, endpoints y landing. Comprobado que fallan si se rompe el factor de velocidad o la autenticación del webhook.
- **[HECHO]** Traducción `i18n/es.po` (146 textos traducidos; los textos de la landing ya están en español en el código).
- **[HECHO*]** Prueba de carga de ingesta (2026-10-28): 39 peticiones por segundo con 20 hilos en un solo proceso, sin errores; falta repetirla con varios procesos y el volumen de 30 días.
- **[HECHO]** Informe de calidad en PDF (`docs/calidad/`) con 42 pruebas en vivo, auditoría de 1000 peticiones y cobertura de 93,8 %. Halló 3 defectos abiertos (DEF-008 a DEF-010) en la validación de la posición del webhook.
- **[HECHO]** Corregir DEF-008 a DEF-010 y portar E7, E8 y E9 a las pruebas de Odoo (verificados con 247 tests Odoo y 46/47 suite en vivo).
- **[HECHO]** Documentación de calidad en `docs/calidad/` (política, reglas, casos, resultados, defectos, lluvia de ideas, Pareto, Ishikawa, ISO y evidencias).
- **[PENDIENTE]** Análisis estático (flake8, pylint-odoo, SonarQube) e integración continua; una persona de QA independiente.

## Fase 8. Producción **[PARCIAL]**

Detalle y comandos en `docs/PRODUCCION.md`.

| Tarea | Estado |
|---|---|
| Proxy inverso con HTTPS y cabeceras de seguridad (Caddy) | HECHO (probado con el certificado interno de Caddy; Let's Encrypt real sin probar) |
| Secretos aleatorios, contraseña maestra de Odoo con hash, `list_db` apagado | HECHO |
| Webhook por la red interna, con el secreto en una cabecera y no en la URL; bloqueado desde el proxy | HECHO |
| Panel de Traccar solo a través del proxy; Traccar sobre Postgres | HECHO |
| Healthchecks, rotación de logs, límites de Odoo | HECHO |
| Respaldos (Odoo, Traccar y filestore) con checksums y retención | HECHO |
| Restauración probada (base paralela y restauración destructiva completa) | HECHO |
| Monitoreo: endpoint `/bus_tracking/health` | HECHO; falta conectar un servicio externo que avise |
| Retención de posiciones acorde al volumen | Parámetro disponible; partición por mes PENDIENTE (depende de la fase 0) |
| Copia de los respaldos fuera del servidor | PENDIENTE (depende de dónde se aloje) |
| Límite de intentos de login, 2FA, bloqueo de IPs | PENDIENTE |
| Cifrado del tráfico GPS (TLS en Traccar) | PENDIENTE (depende del modelo de GPS) |
| Prueba en un servidor Linux real con dominio público | PENDIENTE |

## Fase 9. Teléfonos de los choferes como GPS **[HECHO salvo la prueba con un celular real]**

- Código QR para configurar la app tableta Buses UTA (dirección del servidor Odoo).
- El proxy publica el puerto de OsmAnd por HTTPS, de modo que la ubicación viaje cifrada (hoy viaja en claro).
- Guía corta para el chofer (instalar, activar el turno, batería).
- Hecho: registro del GPS desde Odoo, identificador aleatorio solo visible para administradores, QR (sin verificar en un teléfono), HTTPS para los celulares, cuenta de Traccar creada automáticamente, `docs/GUIA-CHOFER.md`.
- **Pendiente:** criterio de aceptación con un celular real: aparece en el mapa en menos de 15 segundos y sigue reportando con la pantalla apagada 30 minutos (solo se simuló con peticiones HTTP).

## Fase 10. Portal público de pasajeros **[HECHO]**

- Página pública (sin login): lista de rutas activas, mapa con la ruta, sus paradas y sus buses en vivo; estado de cada bus ("en movimiento", "sin señal").
- Endpoint público de solo lectura que expone solo lo necesario: nombre del bus, posición, rumbo y estado. Nunca patente, conductor, velocidad exacta ni historial.
- Límite de peticiones por IP y caché de pocos segundos para que mil pasajeros no saturen el servidor.
- Estilo coherente con la landing; funciona bien en celulares.
- Hecho: `/rutas` (lista), `/rutas/<código>` (mapa) y `/rutas/<código>/buses.json`; ruta con casilla *Visible to passengers*; límite de 60 peticiones por minuto por IP y caché de 5 segundos (por proceso); buses sin reportar hace más de 15 minutos no se muestran; español e inglés con selector y cookie; versionado de los estáticos para que el navegador no guarde copias viejas.
- Criterio de aceptación cumplido: desde la landing, un clic a `/rutas` y otro a la ruta (probado en un ancho de 390 px).
- Limitación: la ruta se dibuja como línea recta entre paradas hasta que exista la geometría real.

## Fase 11. Quejas y reportes **[HECHO salvo el correo, que va en la fase 12]**

- Hecho: formulario público `/quejas` (ruta, bus opcional, tipo, descripción de 10 a 2000 caracteres, correo y teléfono opcionales) que conserva lo escrito si hay errores; folio `Q-00001` en una página de agradecimiento.
- Hecho: protección contra abuso con campo trampa, tiempo mínimo firmado de 3 segundos, token CSRF, límite de 5 quejas por IP y hora (por proceso), cuerpo máximo de 20 KB, y descarte silencioso de los envíos sospechosos.
- Hecho: bandeja en el panel (`Quejas`) con estados nueva, en revisión y resuelta, responsable, nota interna y filtros por estado, ruta y tipo. Los datos de contacto solo los ven los administradores.
- Hecho: aviso de privacidad en el formulario y borrado automático del correo y el teléfono a los 90 días de resuelta la queja (configurable; 0 los conserva).
- **Pendiente (fase 12):** acuse de recibo y respuesta por correo, aviso al equipo cuando llega una queja nueva, y captcha opcional si se aporta una clave de servicio.

## Fase 12. Notificaciones (correo y push) **[HECHA salvo el correo institucional real y la prueba del push en un navegador]**

Detalle de uso en `docs/CORREO.md`.

- Hecho: cola de notificaciones (`bus.notification`) que un cron revisa cada minuto, para que un servicio de correo o de push lento nunca retrase la llegada de una posición o de una queja.
- Hecho: alertas de bus (exceso de velocidad, sin señal, parada larga) y quejas nuevas llegan por correo a los administradores suscritos, en un solo resumen si hay varios eventos a la vez (máximo 20 filas, el resto se resume), en el idioma y la hora local de cada persona.
- Hecho: cada administrador elige en sus preferencias qué recibe (correo, push y cada tipo de alerta o quejas).
- Hecho: acuse de recibo automático al pasajero que dejó su correo, en su idioma, con solo el folio (nunca lo que escribió), y asistente para responderle desde la queja; la respuesta queda en el historial.
- Hecho: notificaciones push web: registro de dispositivos desde una página del panel, claves VAPID creadas solas, mensajes cifrados (RFC 8291) y firmados, lista de servicios push permitidos para evitar peticiones del servidor a direcciones internas, y eliminación de suscripciones caducadas.
- Pendiente: probar el correo con el servidor institucional real de la UTA (se probó con un buzón de pruebas) y el push en un navegador real (se probó el cifrado, la firma y los endpoints, pero no la entrega a un navegador).
- Hecho: horario de silencio por persona y destinatarios por ruta.

## Fase 13. Idiomas: español, inglés y kichwa **[PARCIAL]**

- Hecho: el panel está en español de Ecuador (`es_EC`) e inglés es el idioma base; el portal de pasajeros ya tiene español e inglés con selector, elección según el navegador y memoria de la elección.
- Hecho: borrador de kichwa en el portal, marcado "borrador" y nunca elegido solo desde el navegador; falta la revisión de una persona hablante.
- Variante: kichwa de Ecuador (definido por el cliente). Falta acordar con la universidad cuál (el kichwa unificado u otra variante local) y conseguir la revisión de una persona hablante antes de publicar; mi borrador no reemplaza esa revisión.
- Hallazgo técnico: Odoo 16 **no incluye** quechua ni kichwa entre sus idiomas del panel (sí incluye `es_EC`), aunque la biblioteca de formatos (Babel) conoce `qu_EC`. Por eso el kichwa se hará primero en el portal de pasajeros, que usa un diccionario propio y solo necesita agregar una clave. En el panel solo sería posible creando un idioma personalizado y su catálogo, y no se recomienda mientras no haya personal que lo use en kichwa.

## Fase 14. Despliegue en Azure **[PENDIENTE]**

Recomendación: **una máquina virtual Linux** (por ejemplo 2 vCPU y 4 a 8 GB) con el `docker-compose.prod.yml` actual, porque Traccar recibe conexiones de dispositivos que no encajan bien en servicios de aplicación web. Para 100 buses o menos alcanza; con más, medir antes de crecer.

- Región: elegir la región de Azure disponible más cercana a Ecuador (por ejemplo Brasil Sur); comprobar disponibilidad, precios y si la universidad ya tiene una suscripción o convenio educativo de Azure.
- Reglas de red: abrir solo 80 y 443 (los celulares usan HTTPS); 5055 y 5023 ya no se publican.
- Respaldos: copiar `backups/` a Azure Blob Storage con ciclo de vida de retención; además, instantáneas del disco.
- Correo saliente: servicio de correo de Azure o un relé SMTP por el puerto 587 (Azure bloquea el 25 desde las máquinas virtuales).
- Posible mejora posterior: base de datos administrada (Azure Database for PostgreSQL) y alertas de Azure Monitor sobre `/bus_tracking/health`.
- Lo que no puedo hacer yo: crear recursos en tu suscripción de Azure. Puedo dejar guías y plantillas, pero no las podré probar contra tu cuenta.

## Fase 15. Recorridos oficiales de la UTA **[HECHA salvo las confirmaciones con la universidad]**

Fuente: `RECORRIDOS-INSTITUCIONALES-2025.pdf`. Detalle, anomalías y supuestos en `docs/RECORRIDOS.md`.

- Hecho: lectura del PDF (`scripts/roster_from_pdf.py`), modelo de recorridos y tramos, importador repetible (asistente en el panel y `scripts/import-roster.sh`), 11 buses con sus conductores, 4 líneas (Troncal, Izamba, Pelileo, Píllaro) con sus paradas, 123 tramos.
- Hecho: la línea de cada bus se asigna sola, cada minuto, según el tramo que le toca; el panel muestra qué hace cada recorrido ahora.
- Hecho: *Horario de hoy* en la página pública de cada línea (próximas salidas por origen y destino, hora de Ecuador, sin conductores).
- Confirmar con la universidad: los días en que rige cada recorrido (se supuso lunes a viernes), las coordenadas de los campus (aproximadas, de OpenStreetMap; la de Ingahurco es la menos segura), y las 9 anomalías del documento.
- Hecho: geometría de cada tramo (calculada), informe de puntualidad y alerta de recorrido no iniciado. Pendiente: verificar los trazados con buses reales.

## Pendientes anteriores que siguen abiertos

- Geometría real de las rutas (hoy una línea recta entre paradas). Propuesta barata: una acción que guarde el trazado a partir de un recorrido real del bus.
- Viajes con horario, puntualidad y estimación de llegada ("cuánto falta"), útil para el portal de pasajeros.
- Prueba de carga, copia de respaldos fuera del servidor, límite de intentos de login, autenticación en dos pasos.

## Orden recomendado

1. Fase 9 (celulares como GPS): es lo que hay que validar con un dispositivo real antes de construir encima.
2. Fases 10 y 11 (portal de pasajeros y quejas): el núcleo de lo que pidió el cliente.
3. Fase 12 (correo y push).
4. Fase 13 (idiomas), junto con la revisión del quechua.
5. Fase 14 (Azure) cuando haya suscripción y dominio.


## Simplificación (2026-10-27)

El alcance se redujo: ver la entrada de `docs/BITACORA.md` de esa fecha. Las fases sobre roster, trazados por calle, viajes y puntualidad, correo y respuestas a quejas quedan **canceladas**.

## App de tableta para choferes (fases 16 a 22) **[código en develop; falta jornada real]**

Plan completo en `docs/PLAN-APP-CHOFER.md`. Backend (16–18) y app Expo (19–21) integrados. Fase 22: casos QA del API de chofer, guía, producción y perfil EAS `production`. Pendiente: APK firmado en tableta con GPS, jornada con chofer real.
