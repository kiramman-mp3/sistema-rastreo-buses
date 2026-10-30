# Plan de implementación: app de tableta para choferes

Continúa la numeración de `docs/PLAN.md` (fases 0 a 15). Aquí van las fases 16 a 22.

## Objetivo

Una tableta en cada bus donde el chofer inicia sesión con su usuario de Odoo, elige bus y ruta, inicia y termina su turno, ve las paradas y el avance, ve sus alertas y reporta incidentes. La posición sigue yendo por Traccar (protocolo OsmAnd). Odoo solo gestiona login, rutas y turnos.

## Decisiones tomadas

- La app es **nueva, en Expo (TypeScript)**. Traccar Client es Flutter, así que no se puede hacer un fork literal con Expo. Se replica su comportamiento (envío OsmAnd en segundo plano, cola sin red). Licencia Apache 2.0: se cita el origen en un `NOTICE`.
- GPS por Traccar, igual que hoy (`GPS_DOMAIN` → Caddy → `traccar:5055`).
- Login con usuario de Odoo por chofer, en el grupo `group_bus_driver`. Token propio, porque Odoo 16 solo acepta API keys en sus endpoints RPC.
- Primera versión solo Android. iOS queda fuera.
- Se necesita *development build* (EAS Build): Expo Go no sirve para GPS en segundo plano.

## Mapa de fases

| Fase | Contenido | Rama | Depende de | Estado |
|---|---|---|---|---|
| 16 | Backend: grupo, turnos, tokens, login | `feature/driver-backend` | — | Integrada en develop |
| 17 | Backend: iniciar/terminar turno, ruta, estado, alertas, incidentes | `feature/driver-shifts-api` | 16 | Integrada en develop |
| 18 | Backend: vistas de staff, traducciones, avisos push de incidentes | `feature/driver-staff-views` | 17 | Pendiente |
| 19 | App: proyecto Expo, login, selección de bus y ruta | `feature/driver-app-base` | 16, 17 | Pendiente |
| 20 | App: GPS en segundo plano y cola sin red | `feature/driver-app-gps` | 17, 19 | Pendiente |
| 21 | App: paradas, avance, alertas, incidentes, idiomas | `feature/driver-app-route` | 17, 19 | Pendiente |
| 22 | Prueba real, QA, distribución y documentación | `feature/driver-app-release` | 18, 20, 21 | Pendiente |

Las fases 19 a 21 pueden avanzar en paralelo con la 18 una vez que la 17 fije el contrato de la API.

## Fase 16. Backend: base de autenticación y turnos

Hecho en la rama `feature/driver-backend` y merge `--no-ff` a `develop`.

- Grupo `group_bus_driver`, regla para que cada chofer vea solo sus turnos, accesos mínimos de lectura.
- `bus.shift` con un turno activo por chofer y por bus (índices únicos parciales).
- `bus.driver.token`: solo se guarda el hash, vence a los 30 días, cron diario de purga.
- Endpoints `POST /bus_tracking/driver/login`, `/logout`, `/me`, con límite de intentos y misma respuesta para clave mala y usuario sin rol.
- Tests en `tests/test_driver_auth.py`.
- El chofer se crea como usuario interno (`base.group_user`) más el grupo Driver. El grupo Driver no abre el panel por sí solo.
- Suite del módulo (2026-10-30): 216 tests, 0 fallos.

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

Criterio de aceptación: cubierto por `tests/test_driver_shift.py` (login → start → state/route/incident → end; el bus recibe `driver_id` = partner del chofer, que es lo que pinta el mapa en vivo). Suite del módulo 2026-10-30: 232 tests, 0 fallos.

## Fase 18. Backend: vistas de staff y avisos

Archivos: `views/bus_shift_views.xml`, `views/bus_incident_views.xml`, `views/menus.xml`, `i18n/es.po`, `models/bus_push.py`.

- Menús Turnos e Incidentes (lista, filtros por bus, ruta y fecha).
- El mapa en vivo muestra el chofer del turno, que ya sale de `driver_id`.
- Un incidente nuevo envía un aviso push a los gestores reutilizando `bus.push.subscription` y el mismo mecanismo que las alertas.
- Acción de gestor "Cerrar sesión de la tableta" que revoca los tokens de un chofer.
- Traducciones al español de todo texto nuevo.

Criterio de aceptación: un gestor ve turnos e incidentes, recibe el push y puede revocar una tableta.

## Fase 19. App: base, login y selección

Carpeta `apps/conductor-tablet/`. Expo SDK vigente, TypeScript, `expo-router`.

- Estructura: `app/` (rutas), `src/api/` (cliente), `src/state/` (sesión y turno), `src/i18n/`, `src/gps/`, `src/ui/`.
- Cliente de API con token en `expo-secure-store`. Un 401 cierra sesión y vuelve al login.
- URL del servidor desde `EXPO_PUBLIC_ODOO_URL`, con valor por defecto para desarrollo.
- Pantallas: Login, Selección de bus y ruta (buses con `available: false` aparecen deshabilitados), y recuperación del turno activo al abrir la app.
- Tableta: orientación horizontal, textos y botones grandes, `expo-keep-awake`.
- Herramientas: `tsc --noEmit`, `expo lint`, `jest-expo`.
- `eas.json` con perfil `development` (APK).

Tests: cliente API (token, 401, errores de red) y estado de sesión.

Criterio de aceptación: en emulador o tableta, iniciar sesión, elegir bus y ruta, cerrar y reabrir la app conservando el turno.

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

Criterio de aceptación: con la pantalla apagada 30 minutos, el bus sigue moviéndose en el mapa en vivo de Odoo. Tras cortar la red 5 minutos, la cola se vacía al volver.

## Fase 21. App: recorrido, alertas e incidentes

- Pantalla de turno: lista de paradas con la siguiente destacada, marca de las ya alcanzadas con su hora, y mapa (`react-native-webview` con Leaflet y OSM, sin clave de Google) con la ruta y la posición del bus.
- Refresco con `/driver/state` cada 15 s mientras la pantalla está activa.
- Alertas del bus (exceso de velocidad, fuera de ruta, parada larga, sin señal) en un panel, con su `detail`.
- Botón de incidente con selección de tipo y nota opcional. Si no hay red, el incidente queda en cola y se reenvía.
- Terminar turno con confirmación.
- Idiomas es/en/qu: se reutilizan las cadenas de `models/portal_i18n.py` donde coincidan. El kichwa necesita revisión de un hablante, como en el portal.

Tests: estado de las paradas, cola de incidentes, textos en los tres idiomas.

Criterio de aceptación: un chofer completa un recorrido simulado, ve avanzar las paradas, ve una alerta de velocidad y reporta un incidente que el gestor recibe.

## Fase 22. Prueba real, QA y distribución

- **Prueba con la tableta real**, antes de dar nada por cerrado. Confirmar que el modelo tiene GPS (muchas tabletas solo Wi-Fi no lo tienen). Si no, probar con SIM/GNSS o con el celular del chofer.
- Extender `qa/` con casos del API de chofer (login, turno, estado, incidente) y repetir `python -X utf8 qa/ejecutar_todo.py`. Regenerar el informe con `qa/generar_informe.py`.
- Distribución: `eas build --profile production --platform android` y APK firmado instalado en cada tableta (instalación directa, sin Play Store en esta etapa). Documentar cómo actualizar.
- Documentación: reemplazar el uso de Traccar Client en `docs/GUIA-CHOFER.md`, nueva sección en `docs/PRODUCCION.md` (usuarios de chofer, tokens, revocación), entrada en `docs/BITACORA.md`, `docs/PLAN.md` y `README.md`, y actualizar la memoria del proyecto.
- Configuración de la tableta: pantalla siempre encendida, sin ahorro de batería para la app, cargador en el bus, modo de aplicación fija si el modelo lo permite.

Criterio de aceptación: una jornada completa con un chofer real, con GPS, turno, alerta e incidente, sin intervención del desarrollador.

## Riesgos

- Tabletas sin chip GPS. Se confirma en la fase 22, pero conviene saber el modelo antes de la fase 20.
- El id de dispositivo sigue siendo la única credencial del lado de Traccar. Mitigación: solo se entrega durante un turno autenticado. Opcional: rotarlo al terminar el turno.
- Android puede detener la tarea de GPS por ahorro de batería. Mitigación: servicio en primer plano y exclusión de optimización.
- Las contraseñas de los choferes las gestiona Odoo. Definir quién crea los usuarios y cómo se restablecen.
- Fuera de alcance, solo anotado: credenciales de Traccar en texto plano (`traccar_api.py:84-85`) y defectos DEF-008 a DEF-010 del webhook.

## Flujo de trabajo en Git

Según `CLAUDE.md`: cada fase en su rama desde `develop`, commits pequeños con Conventional Commits, linter, tests y build antes de integrar, merge `--no-ff` a `develop`. Al cerrar cada fase se deja el resumen de rama, commits y estado de tests, linter y build.
