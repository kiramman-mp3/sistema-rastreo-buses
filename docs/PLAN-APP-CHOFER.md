# Plan de implementación: app de tableta para choferes

Continúa la numeración de `docs/PLAN.md` (fases 0 a 15). Aquí van las fases 16 a 22.

## Objetivo

Una tableta en cada bus donde el chofer inicia sesión con su usuario de Odoo, elige bus y ruta, inicia y termina su turno, ve las paradas y el avance, ve sus alertas y reporta incidentes. La posición sigue yendo por Traccar (protocolo OsmAnd). Odoo solo gestiona login, rutas y turnos.

## Decisiones tomadas

- La app es **nueva, en Expo (TypeScript)**. Traccar Client es Flutter, así que no se puede hacer un fork literal con Expo. Se replica su comportamiento (envío OsmAnd en segundo plano, cola sin red). Licencia Apache 2.0: se cita el origen en un `NOTICE`.
- GPS por Traccar, igual que hoy (`GPS_DOMAIN` → Caddy → `traccar:5055`).
- Login con usuario de Odoo por chofer, en el grupo `group_bus_driver`. Token propio, porque Odoo 16 solo acepta API keys en sus endpoints RPC.
- Primera versión orientada a Android en tabletas/teléfonos. Soporte para iOS añadido en 2026-11-04 (DEF-038: adaptación de Apple CoreLocation con stationary heartbeat, `showsBackgroundLocationIndicator` y `UIBackgroundModes: ["location", "fetch"]`).
- Se necesita *development build* o standalone build (EAS Build): Expo Go no sirve para GPS en segundo plano.

## Mapa de fases

| Fase | Contenido | Rama | Depende de | Estado |
|---|---|---|---|---|
| 16 | Backend: grupo, turnos, tokens, login | `feature/driver-backend` | — | Integrada en develop |
| 17 | Backend: iniciar/terminar turno, ruta, estado, alertas, incidentes | `feature/driver-shifts-api` | 16 | Integrada en develop |
| 18 | Backend: vistas de staff, traducciones, avisos push de incidentes | `feature/driver-staff-views` | 17 | Integrada en develop |
| 19 | App: proyecto Expo, login, selección de bus y ruta | `feature/driver-app-base` | 16, 17 | Integrada en develop |
| 20 | App: GPS en segundo plano y cola sin red | `feature/driver-app-gps` | 17, 19 | Integrada en develop |
| 21 | App: paradas, avance, alertas, incidentes, idiomas | `feature/driver-app-route` | 17, 19 | Integrada en develop |
| 22 | Prueba real, QA, distribución y documentación | `feature/driver-app-release` | 18, 20, 21 | Docs y QA en develop; falta jornada real |
| 25 | App: ergonomía de cabina (modo oscuro profundo, headway semafórico, parada 34px y SOS anti-vibración) | `feature/driver-tablet-shift` | 21 | Integrada en develop |

Las fases 19 a 21 pueden avanzar en paralelo con la 18 una vez que la 17 fije el contrato de la API.

## Fase 16. Backend: base de autenticación y turnos

Hecho en la rama `feature/driver-backend` y merge `--no-ff` a `develop`.

- Grupo `group_bus_driver`, regla para que cada chofer vea solo sus turnos, accesos mínimos de lectura.
- `bus.shift` con un turno activo por chofer y por bus (índices únicos parciales).
- `bus.driver.token`: solo se guarda el hash, vence a los 30 días, cron diario de purga.
- Endpoints `POST /bus_tracking/driver/login`, `/logout`, `/me`, con límite de intentos y misma respuesta para clave mala y usuario sin rol.
- Tests en `tests/test_driver_auth.py`.
- El chofer se crea como usuario interno (`base.group_user`) más el grupo Driver. El grupo Driver no abre el panel por sí solo.
- Suite del módulo (2026-10-30): 216 tests, 0 fallos. Cifra de esa fecha; la actual está en `docs/PLAN-AUDITORIA.md` (248 tests el 2026-11-02).

Criterio de aceptación: cumplido.

## Fase 17. Backend: turnos y datos del recorrido

Archivos: `controllers/driver_api.py`, `models/bus_shift.py`, nuevo `models/bus_incident.py`, `tests/test_driver_shift.py`.

1. `POST /driver/shift/start` con `vehicle_id` y `route_id`.
   - Falla con 409 si el bus o el chofer ya tienen turno activo.
   - Falla con 409 `no_gps` si el bus no tiene `traccar_unique_id` (un gestor debe registrar el GPS).
   - Asigna `bus.vehicle.driver_id` y `route_id`.
   - Devuelve el turno, `traccar_unique_id` y `bus_tracking.gps_url`. Es el único lugar donde el id llega al chofer, y solo con turno activo.
2. `POST /driver/shift/end`: cierra el turno, limpia `driver_id`. Cron horario que cierra turnos abiertos más de 14 horas, igual que `bus.run._cron_discard_stale`.
3. `POST /driver/state`: una sola llamada para refrescar la pantalla. Devuelve paradas de la ruta con `arrived_at` dentro del turno (de `bus.stop.arrival`), `next_stop_id`, parada actual (`bus.vehicle.current_stop_id`) y alertas abiertas o de las últimas 2 horas del bus. Una llamada cada 15 s ahorra batería frente a varias.
4. `POST /driver/route`: paradas con latitud, longitud y radio, más las líneas de `route._map_lines()` para dibujar el mapa una sola vez.
5. `POST /driver/incident`: `kind` (avería, tráfico, accidente, otro), `note` opcional (máx. 300 caracteres), `lat` y `lon` opcionales. Valida rangos (-90..90, -180..180) y tipos desde el inicio. Exige turno activo.
6. Modelo `bus.incident`: `shift_id`, `vehicle_id`, `kind`, `note`, `lat`, `lon`. Lectura para el grupo de usuarios del sistema, borrado para gestores.

Tests: bus ocupado, turno doble, bus sin GPS, id de GPS ausente en `/me` y presente solo en `shift/start`, cierre de turnos viejos, incidente sin turno, coordenadas fuera de rango, `state` con parada alcanzada, chofer sin acceso a turnos ajenos.

Criterio de aceptación: cubierto por `tests/test_driver_shift.py` (login → start → state/route/incident → end; el bus recibe `driver_id` = partner del chofer, que es lo que pinta el mapa en vivo). Suite del módulo 2026-10-30: 232 tests, 0 fallos (cifra de esa fecha; hoy son 248).

## Fase 18. Backend: vistas de staff y avisos

Archivos: `views/bus_shift_views.xml`, `views/bus_incident_views.xml`, `views/menus.xml`, `i18n/es.po`, `models/bus_push.py`.

- Menús Turnos e Incidentes (lista, filtros por bus, ruta y fecha).
- El mapa en vivo muestra el chofer del turno, que ya sale de `driver_id`.
- Un incidente nuevo envía un aviso push a los gestores reutilizando `bus.push.subscription` y el mismo mecanismo que las alertas.
- Acción de gestor "Cerrar sesión de la tableta" que revoca los tokens de un chofer.
- Traducciones al español de todo texto nuevo.

Criterio de aceptación: cubierto por `tests/test_driver_staff.py` (lectura/borrado, push una vez, revocar tableta cierra el turno). Suite del módulo 2026-10-30: 239 tests, 0 fallos.

## Fase 19. App: base, login y selección

Carpeta `apps/conductor-tablet/`. Expo SDK vigente, TypeScript, `expo-router`.

- Estructura: `app/` (rutas), `src/api/` (cliente), `src/state/` (sesión y turno), `src/i18n/`, `src/gps/`, `src/ui/`.
- Cliente de API con token en `expo-secure-store`. Un 401 cierra sesión y vuelve al login.
- URL del servidor desde `EXPO_PUBLIC_ODOO_URL`, con valor por defecto para desarrollo.
- Pantallas: Login, Selección de bus y ruta (buses con `available: false` aparecen deshabilitados), y recuperación del turno activo al abrir la app.
- Tableta: textos y botones grandes, `expo-keep-awake`.
- Pantallas adaptables: la app gira libre (`orientation: default`) y funciona en teléfono y tableta, vertical y horizontal. `src/ui/layout.ts` clasifica la pantalla (lado corto < 600 dp es teléfono) y decide: tamaños de texto (tableta 20-60 px, teléfono 16-40 px), alto mínimo de los controles (72 / 56 px), paneles lado a lado o apilados, y qué se oculta cuando falta altura. `Screen` (`src/ui/cabin.tsx`) cuida muescas, barras del sistema y teclado.
- Gesto de atrás: `predictiveBackGestureEnabled` se mantiene en `false`. La tecla y el gesto de atrás funcionan igual; solo se evita la animación predictiva. Con un turno abierto, un gesto de atrás accidental sobre la pantalla del turno es un riesgo, y el emulador de pruebas (LDPlayer, Android 9) no puede validarlo. Reabrir cuando haya un Android 14 o superior real para probar login, selección, turno, incidente y GPS.
- Herramientas: `tsc --noEmit`, `expo lint`, `jest-expo`.
- `eas.json` con perfil `development` (APK).

Tests: cliente API (token, 401, errores de red) y estado de sesión.

Criterio de aceptación: el turno activo se recupera de `/me` al abrir (probado en `session.test.ts`). Login, token, 401 y red cubiertos en `client.test.ts`. `tsc --noEmit`, `expo lint` y Jest: PASS. Falta probar en emulador/tableta (fase 22).

## Fase 20. App: GPS en segundo plano

Archivos en `src/gps/`.

- `expo-location` con `startLocationUpdatesAsync`, alta precisión, intervalo de 10 s, servicio en primer plano con notificación persistente. La tarea se declara con `expo-task-manager` a nivel de módulo.
- Se inicia al empezar el turno con el id y la URL que devuelve `shift/start`, y se detiene al terminarlo o cerrar sesión.
- Envío: `GET {gps_url}/?id=…&lat=…&lon=…&timestamp=…&speed=…&bearing=…&altitude=…&accuracy=…&batt=…`.
  - `timestamp` en segundos, `speed` en nudos (m/s × 1,94384), batería con `expo-battery`.
- Cola local (SQLite o AsyncStorage) que guarda posiciones si falla el envío y las reenvía en orden al volver la red, con tope de antigüedad y de tamaño.
- Permisos: ubicación en primer plano, luego en segundo plano, y pedir la exclusión de optimización de batería. Pantalla de diagnóstico: permisos, última posición enviada, tamaño de la cola.
- Atribución a Traccar Client en `NOTICE`.

Tests: construcción de la URL OsmAnd (conversión de unidades), cola (orden, reintento, tope), tarea con ubicación simulada.

### Adaptación para iOS y corrección de reenvío Traccar (2026-11-04, DEF-035 a DEF-038)

- **Diferencia CoreLocation vs Android**: En Android `timeInterval: 10_000` emite pulsos periódicos continuos del proveedor GNSS. En iOS, Apple CoreLocation ignora `timeInterval` y suspende las emisiones si el dispositivo está detenido. El parámetro `deferredUpdatesInterval` agravaba esto congelando los eventos hasta detectar desplazamiento físico.
- **Stationary Heartbeat**: En `src/gps/tracker.ts`, se incorporó un latido periódico cada 10 s que verifica si han transcurrido más de 9.5 s sin eventos de posición. En reposo, ejecuta `Location.getCurrentPositionAsync` para emitir la coordenada fija a velocidad 0.0 km/h.
- **Configuración nativa iOS**: En `app.json` se definieron `UIBackgroundModes: ["location", "fetch"]`, `showsBackgroundLocationIndicator: true` y `activityType: Location.ActivityType.AutomotiveNavigation`.
- **Fallback en primer plano**: Si la app corre sin gestor de tareas en segundo plano (p. ej. Expo Go en iOS), conmuta de manera segura a `Location.watchPositionAsync`.
- **Reenvío en Traccar 6 (DEF-035)**: Se requiere `FORWARD_ENABLE: "true"` en docker-compose para que Traccar reenvíe por HTTP POST JSON las posiciones a Odoo.

Criterio de aceptación: URL OsmAnd (nudos, timestamp en segundos), cola (orden, reintento, topes) y tarea con ubicación simulada cubiertos por Jest. `tsc --noEmit`, `expo lint` y 20 tests: PASS. El id se pide en permisos **antes** de `shift/start`. Falta la prueba con pantalla apagada 30 min y cola 5 min sin red (fase 22, development build).

## Fase 21. App: recorrido, alertas e incidentes

- Pantalla de turno: lista de paradas con la siguiente destacada, marca de las ya alcanzadas con su hora, y mapa (`react-native-webview` con Leaflet y OSM, sin clave de Google) con la ruta y la posición del bus.
- Refresco con `/driver/state` cada 15 s mientras la pantalla está activa.
- Alertas del bus (exceso de velocidad, fuera de ruta, parada larga, sin señal) en un panel, con su `detail`.
- Botón de incidente con selección de tipo y nota opcional. Si no hay red, el incidente queda en cola y se reenvía.
- Terminar turno con confirmación.
- Idiomas es/en/qu: se reutilizan las cadenas de `models/portal_i18n.py` donde coincidan. El kichwa necesita revisión de un hablante, como en el portal.

Tests: estado de las paradas, cola de incidentes, textos en los tres idiomas.

Criterio de aceptación: `classifyStops`, cola de incidentes e i18n es/en/qu cubiertos por Jest. `tsc --noEmit`, `expo lint` y 29 tests: PASS. Falta el recorrido simulado en tableta/emulador (fase 22).

## Fase 22. Prueba real, QA y distribución

- **Prueba con la tableta real**, antes de dar nada por cerrado. Confirmar que el modelo tiene GPS (muchas tabletas solo Wi-Fi no lo tienen). Si no, probar con SIM/GNSS o con el celular del chofer.
- Extender `qa/` con casos del API de chofer (login, turno, estado, incidente) y repetir `python -X utf8 qa/ejecutar_todo.py`. Regenerar el informe con `qa/generar_informe.py`.
- Distribución: `eas build --profile production --platform android` y APK firmado instalado en cada tableta (instalación directa, sin Play Store en esta etapa). Documentar cómo actualizar.
- Documentación: reemplazar el uso de Traccar Client en `docs/GUIA-CHOFER.md`, nueva sección en `docs/PRODUCCION.md` (usuarios de chofer, tokens, revocación), entrada en `docs/BITACORA.md`, `docs/PLAN.md` y `README.md`, y actualizar la memoria del proyecto.
- Configuración de la tableta: pantalla siempre encendida, sin ahorro de batería para la app, cargador en el bus, modo de aplicación fija si el modelo lo permite.

Criterio de aceptación (código): guía del chofer, sección de producción, README/PLAN, perfil EAS `production`, casos F13–F14 y E23–E25 en `qa/qa_suite.py`. Criterio de campo **abierto**: jornada completa con chofer real y APK firmado en tableta con GPS.

## Fase 25. App: ergonomía de cabina, cadencia headway y SOS anti-vibración

> **Corrección (2026-11-02).** La barra de cadencia de esta fase usaba datos fijos y podía pedir a un bus fuera de ruta que acelerara; se eliminó en la fase 26. La confirmación de llegada no registraba nada y también se quitó. Los "72 px mínimos" no se cumplían en todos los botones. La cabina se rehízo en la fase 30 (`docs/PLAN-UX.md`); lo que sigue describe la versión anterior.

Hecho en la rama `feature/driver-tablet-shift` y merge `--no-ff` a `develop`.

- **Ergonomía visual y táctil para montaje en tablero (a 100 cm de los ojos):**
  - Paleta ultra oscura antirreflejos (`#0B0F17`, superficie `#151D2A`) para evitar encandilamiento en la noche y reflejos de luz solar.
  - Tamaño de toque mínimo de 72px (`cockpitHit = 72`) para interacción segura ante vibración y baches del camino.
- **Header de telemetría:**
  - Identificador gigante de unidad y línea, reloj digital monoespaciado en tiempo real, indicador de estado GPS y diálogo modal seguro para finalizar turno.
- **Barra de cadencia / Headway (`HeadwayBar.tsx`):**
  - Semáforo periférico respecto al bus delantero con feedback físico de resorte (`react-native-reanimated`):
    - 🟢 **A TIEMPO:** Intervalo óptimo de frecuencia.
    - 🟡 **ADELANTADO:** Alerta de reducción de velocidad.
    - 🔴 **RETRASADO:** Alerta de aceleración.
- **Próximas paradas (`StopAlertCard.tsx`):**
  - Parada inmediata en tipografía de 34px, distancia estimada en vivo por Haversine (`useCockpitTelemetry.ts`), botón de confirmación táctil de 72px con feedback háptico (`expo-haptics`) y riel de anticipación para las siguientes 2 paradas.
- **Acciones rápidas de emergencia (`IncidentActions.tsx`):**
  - Reporte de congestión/tráfico con 1 solo toque despachado a la cola offline de Odoo (`session.reportIncident`).
  - Alerta SOS con pulsación obligatoria sostenida de 1.5s (`holdProgress` continuo) para evitar activaciones accidentales por vibración del bus.
- **Pruebas y verificación:**
  - 10 suites Jest (44 tests) PASS, `tsc --noEmit` PASS (0 errores TypeScript).

## Riesgos

- Tabletas sin chip GPS. Se confirma en la fase 22, pero conviene saber el modelo antes de la fase 20.
- El id de dispositivo sigue siendo la única credencial del lado de Traccar. Mitigación: solo se entrega durante un turno autenticado. Opcional: rotarlo al terminar el turno.
- Android puede detener la tarea de GPS por ahorro de batería. Mitigación: servicio en primer plano y exclusión de optimización.
- Las contraseñas de los choferes las gestiona Odoo. Definir quién crea los usuarios y cómo se restablecen.
- Fuera de alcance, solo anotado: credenciales de Traccar en texto plano (parámetros `bus_tracking.traccar_user` y `bus_tracking.traccar_password`, que lee `bus.traccar.api._get_conf`) y defectos DEF-008 a DEF-010 del webhook.

## Flujo de trabajo en Git

Según `CLAUDE.md`: cada fase en su rama desde `develop`, commits pequeños con Conventional Commits, linter, tests y build antes de integrar, merge `--no-ff` a `develop`. Al cerrar cada fase se deja el resumen de rama, commits y estado de tests, linter y build.
