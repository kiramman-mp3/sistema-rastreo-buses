# Lluvia de ideas del proyecto, categorizada

Todas las ideas que aparecieron entre el 26 y el 28 de octubre de 2026, ordenadas por categoría y con lo que pasó con cada una. **No es el acta de una sesión de lluvia de ideas:** se reconstruyó leyendo `docs/arquitectura/PLAN.md`, `docs/academico/BITACORA.md` y los pedidos del cliente, de modo que cada idea tiene rastro en esos documentos. Si falta alguna, se agrega con el mismo formato.

Origen: **Cliente** (la UTA, por medio de quien pidió el sistema), **Equipo** (propuesta del desarrollo y del asistente de código) o **Taller** (idea tomada de los talleres de la Unidad 2 o 3).

Estados: **Hecha** (funciona y tiene prueba), **Hecha, sin prueba real** (funciona con datos simulados), **Retirada** (se construyó y se quitó en la simplificación del 27-oct o después), **Descartada** (se decidió no hacerla), **Pendiente**.

## Resumen

| Categoría | Ideas | Hechas | Retiradas | Descartadas | Pendientes |
|---|---|---|---|---|---|
| A. Pasajeros y portal público | 13 | 6 | 3 | 2 | 2 |
| B. GPS y captura de datos | 13 | 10 | 1 | 0 | 2 |
| C. Operación y administración | 12 | 7 | 5 | 0 | 0 |
| D. Alertas y notificaciones | 10 | 5 | 5 | 0 | 0 |
| E. Seguridad y privacidad | 10 | 7 | 0 | 0 | 3 |
| F. Calidad y pruebas | 11 | 7 | 0 | 0 | 4 |
| G. Infraestructura y producción | 11 | 5 | 0 | 0 | 6 |
| H. Interfaz, marca e idiomas | 10 | 7 | 0 | 0 | 3 |
| I. Alcance y gestión | 7 | 6 | 0 | 0 | 1 |
| **Total** | **97** | **60** | **14** | **2** | **21** |

Los totales se verificaron contando las filas de las tablas de abajo. "Hechas" incluye 3 ideas "hechas, sin prueba real" (B1, B4 y D7: funcionan con datos simulados). La idea A7 (kichwa) tiene un borrador y se cuenta como pendiente.

## A. Pasajeros y portal público

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| A1 | Ver en un mapa los buses de una ruta, sin iniciar sesión | Cliente | Hecha | `/rutas`, `/rutas/<código>` |
| A2 | Levantar una queja o reporte | Cliente | Hecha | `/quejas`, folio `Q-00001` |
| A3 | Dejar contacto de forma opcional | Cliente | Hecha | Correo y teléfono opcionales |
| A4 | Mostrar el estado de cada bus ("en movimiento", "sin señal") | Equipo | Hecha | Punto de color en la lista |
| A5 | Exponer solo nombre, posición, rumbo y estado; nunca placa, conductor, velocidad ni historial | Cliente y equipo | Hecha | Prueba F9 |
| A6 | Español e inglés con selector | Cliente | Hecha | Cookie y navegador |
| A7 | Kichwa en el portal | Cliente ("si se puede") | Pendiente (borrador) | Borrador sin revisión de una persona hablante; no se elige solo |
| A8 | "Horario de hoy" con próximas salidas | Equipo | Retirada | Sin horario planificado no hay qué mostrar |
| A9 | Estimación de llegada ("cuánto falta") | Equipo | Retirada | Simplificación del 27-oct |
| A10 | Consultar el estado de una queja con su folio | Equipo | Descartada | Evita un buscador público de quejas (privacidad) |
| A11 | Captcha en el formulario | Equipo | Pendiente | La protección actual es campo trampa, tiempo mínimo y límite por dirección |
| A12 | Notificaciones push a los pasajeros | Equipo | Descartada | El cliente aclaró que el push es solo para el personal |
| A13 | Acuse de recibo por correo al pasajero | Equipo | Retirada | Se quitó el correo en la simplificación |

## B. GPS y captura de datos

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| B1 | Usar el celular de cada chofer como GPS (Traccar Client) | Cliente | Hecha, sin prueba real | Solo se simuló con peticiones HTTP |
| B2 | Enviar la posición cada 10 s en movimiento | Equipo (el cliente delegó) | Hecha (documentada) | `docs/arquitectura/PLAN.md`, `docs/guias/GUIA-CHOFER.md` |
| B3 | Identificador aleatorio por bus, visible solo para administradores | Equipo | Hecha | Es la única credencial del celular |
| B4 | Código QR para configurar la app del chofer | Equipo | Hecha, sin prueba real | El formato del enlace no está documentado por Traccar |
| B5 | Crear el dispositivo en Traccar desde Odoo | Equipo | Hecha | Botón "Registrar GPS" |
| B6 | Webhook en tiempo real y cron de respaldo cada minuto | Equipo | Hecha | Probado con Traccar real |
| B7 | Importar los dispositivos que ya tiene Traccar | Equipo | Retirada | Simplificación del 27-oct |
| B8 | Enviar la ubicación del celular por HTTPS (proxy al puerto 5055) | Equipo | Hecha | Los puertos GPS ya no se abren al público |
| B9 | Guía para el chofer y consentimiento por escrito del seguimiento | Equipo | Pendiente | La guía está hecha; falta el consentimiento y la revisión legal |
| B10 | Probar un celular real 30 minutos con la pantalla apagada | Equipo | Pendiente | Criterio de aceptación de la fase 9 |
| B11 | Forzar envío periódico en reposo en iOS (Stationary Heartbeat cada 10 s) | Equipo | Hecha | Resuelve la suspensión por inactividad de CoreLocation (`tracker.ts`) |
| B12 | Activar reenvío explícito forward.enable en Traccar para webhook Odoo | Equipo | Hecha | Traccar no instanciaba PositionForwarder sin la clave |
| B13 | Modo background de localización en iOS (UIBackgroundModes location) | Equipo | Hecha | Configurado en `app.json` para builds nativos de iPhone |

## C. Operación y administración

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| C1 | Mapa en vivo con filtros por ruta y estado, y trazado de 4 horas | Equipo | Hecha | |
| C2 | Flota administrable, sin cantidad fija de buses | Cliente | Hecha | |
| C3 | Detectar la llegada de un bus a cada parada | Equipo | Hecha | F5 |
| C4 | Recorridos automáticos entre la primera y la última parada | Cliente | Hecha | F6; reemplazó al horario manual |
| C5 | Dibujar la ruta siguiendo las calles con OpenStreetMap y OSRM | Equipo | Retirada | Sustituida por grabar el trazado desde un recorrido real |
| C6 | Grabar el trazado de una ruta a partir de un recorrido real del bus | Equipo | Hecha | `bus.route.record` |
| C7 | Editar las paradas sobre el mapa | Equipo | Hecha | `test_stop_picker` |
| C8 | Reporte de actividad diaria (km, minutos, velocidad máxima) | Equipo | Retirada | Simplificación |
| C9 | Importar los recorridos oficiales del PDF de la universidad (11 recorridos, 123 tramos) | Cliente | Retirada | Simplificación |
| C10 | Viajes con horario y puntualidad | Equipo | Retirada | Sin horario planificado no hay puntualidad |
| C11 | Reproducir un viaje en el mapa | Equipo | Retirada | |
| C12 | Reportes simples: velocidad, sin señal, paradas largas, desvíos y llegadas | Cliente (simplificación) | Hecha | Menú Reportes |

## D. Alertas y notificaciones

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| D1 | Alerta de exceso de velocidad (50 km/h) | Equipo | Hecha | F7; el límite es un supuesto |
| D2 | Alerta de bus sin señal | Equipo | Hecha | |
| D3 | Alerta de parada larga fuera de paradero | Equipo | Hecha | |
| D4 | Alerta de desvío de ruta | Equipo | Hecha | Contra la línea entre paradas |
| D5 | Alerta de recorrido no iniciado | Equipo | Retirada | Dependía del horario planificado |
| D6 | Avisos por correo | Cliente ("correo o push") | Retirada | Se mantuvo solo el push |
| D7 | Push web para el personal, con claves VAPID y mensajes cifrados | Cliente | Hecha, sin prueba real | No se probó la entrega a un navegador real |
| D8 | Cola de notificaciones con resumen por minuto | Equipo | Retirada | |
| D9 | Horario de silencio y filtro por ruta por persona | Equipo | Retirada | |
| D10 | Preferencias de notificación por administrador | Equipo | Retirada | Hoy llegan a todos los administradores suscritos |

## E. Seguridad y privacidad

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| E1 | Secreto del webhook en una cabecera y no en la URL | Equipo | Hecha | DEF-003; E1, E2, F1 |
| E2 | Ocultar el identificador del GPS a quien no es administrador | Equipo | Hecha | |
| E3 | Protección del formulario: campo trampa, tiempo mínimo, CSRF y límite por dirección | Equipo | Hecha | E14 a E16, E22 |
| E4 | Borrar el contacto de una queja a los 90 días de resuelta | Equipo | Hecha | |
| E5 | Rutas privadas con 404, HTML escapado y colores validados | Equipo | Hecha | E10, E11, E17 |
| E6 | Roles User y Manager con permisos por modelo | Equipo | Hecha | `ir.model.access.csv` |
| E7 | Límite de intentos de login, 2FA y bloqueo de direcciones | Equipo | Pendiente | |
| E8 | Revisión legal del aviso de privacidad (ley de datos de Ecuador) | Equipo | Pendiente | Lo debe hacer el área legal de la UTA |
| E9 | Límites de uso compartidos entre procesos (proxy o almacén común) | Equipo | Pendiente | Hoy cuentan por proceso |
| E10 | Cifrar el tráfico GPS con TLS | Equipo | Hecha | Por HTTPS en el proxy |

## F. Calidad y pruebas

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| F1 | Pruebas automáticas de Odoo | Equipo | Hecha | 150 pruebas, 0 fallos |
| F2 | Pruebas de mutación manuales | Equipo | Hecha | 16 mutaciones, todas detectadas |
| F3 | Correr las pruebas en una base nueva cada vez | Equipo | Hecha | Tras varios tropiezos (ver Pareto) |
| F4 | Suite en vivo y auditoría aleatoria de 1000 peticiones | Taller | Hecha | `qa/` |
| F5 | Medir la cobertura con coverage.py | Taller | Hecha | 93,8 % |
| F6 | Prueba de carga de la ingesta | Equipo | Hecha | 39 req/s con 20 hilos, un solo proceso |
| F7 | Informe de calidad en PDF | Taller | Hecha | `Informe_calidad_rastreo_buses.pdf` |
| F8 | Análisis estático con SonarQube, flake8 y pylint-odoo | Taller | Pendiente | |
| F9 | Integración continua con pruebas, cobertura y análisis | Taller | Pendiente | |
| F10 | Pruebas de interfaz extremo a extremo (Playwright) | Taller | Pendiente | |
| F11 | Pruebas de usabilidad con pasajeros y revisión de accesibilidad | Equipo | Pendiente | |

## G. Infraestructura y producción

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| G1 | Docker Compose con Postgres, Odoo y Traccar | Equipo | Hecha | |
| G2 | Proxy Caddy con HTTPS y cabeceras de seguridad | Equipo | Hecha | Probado con el certificado interno; Let's Encrypt real sin probar |
| G3 | Script de instalación con secretos aleatorios | Equipo | Hecha | `scripts/init-prod.sh` |
| G4 | Respaldos con checksums y restauración probada | Equipo | Hecha | DEF-002 |
| G5 | Endpoint `/bus_tracking/health` y healthchecks | Equipo | Hecha | |
| G6 | Máquina virtual Linux en Azure | Cliente (Azure) | Pendiente | Falta suscripción y dominio |
| G7 | Copia de los respaldos a Azure Blob Storage | Equipo | Pendiente | |
| G8 | Partir por mes la tabla de posiciones | Equipo | Pendiente | Solo hace falta con más de 100 buses |
| G9 | Servicio externo de monitoreo sobre `/health` | Equipo | Pendiente | |
| G10 | Base de datos administrada (Azure PostgreSQL) | Equipo | Pendiente | Mejora futura |
| G11 | Probar en un Linux real con dominio público | Equipo | Pendiente | Todo se probó en Windows con Docker Desktop |

## H. Interfaz, marca e idiomas

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| H1 | Landing pública | Equipo | Hecha | |
| H2 | Pantalla de login con tema propio | Equipo | Hecha | |
| H3 | Tema del panel de Odoo con los colores de la marca | Equipo | Hecha | |
| H4 | Nombre configurable ("Buses UTA", provisional) | Equipo | Hecha | |
| H5 | Mapa centrado en Ambato y zona horaria de Ecuador | Cliente | Hecha | |
| H6 | Español de Ecuador (`es_EC`) como idioma de instalación | Cliente | Hecha | |
| H7 | Pulir el diseño (puntos de estado, tarjetas, foco visible) | Equipo | Hecha | 28-oct |
| H8 | Fotos propias de la universidad | Equipo | Pendiente | Las actuales no son de Ambato |
| H9 | Logo y manual de marca de la UTA | Equipo | Pendiente | Lo aporta la universidad |
| H10 | Limpiar `i18n/es.po` de textos de lo eliminado | Equipo | Pendiente | |

## I. Alcance y gestión

| ID | Idea | Origen | Estado | Nota |
|---|---|---|---|---|
| I1 | Fase 0: decisiones del cliente (pasajeros, flota, GPS, Azure, alertas, idiomas) | Cliente | Hecha | 26-oct |
| I2 | Plan de implementación por fases antes de construir | Cliente | Hecha | Se pidió después de la primera construcción |
| I3 | Documentar todo en `docs/` | Cliente | Hecha | Bitácora y plan |
| I4 | Flujo Git con `main`, `develop` y ramas de trabajo | Cliente | Hecha | `CLAUDE.md` |
| I5 | Simplificar el sistema a lo mínimo defendible | Cliente | Hecha | 27-oct |
| I6 | Documentación de calidad al estilo del Taller ACS | Cliente | Hecha | Esta carpeta |
| I7 | Confirmar con la UTA país, variante de kichwa, días, coordenadas y correo | Equipo | Pendiente | |

## Conclusiones de la lluvia de ideas

- De 94 ideas, **57 están hechas**, **14 se retiraron** al simplificar, **2 se descartaron** por privacidad o por decisión del cliente y **21 siguen pendientes**.
- Las ideas retiradas pertenecen casi todas a dos bloques: el horario oficial (recorridos, puntualidad, estimación de llegada) y las notificaciones por correo y sus preferencias. Se retiraron por decisión del cliente, no por fallos.
- Los pendientes se concentran en **infraestructura (Azure)**, **calidad (análisis estático, integración continua, pruebas con personas)** y **cosas que debe aportar la universidad** (fotos, logo, revisión legal, kichwa). Las prioridades están en `11-elementos-acs.md` y en el informe en PDF, Tabla 22.
