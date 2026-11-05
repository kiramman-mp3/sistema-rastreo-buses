# Arquitectura y modelo de datos

Entregable 2 del proyecto final. Describe cómo está armado el sistema, cómo viaja una posición desde el celular hasta un indicador, qué datos se guardan y por qué.
Versión del módulo: **16.0.1.6.0**. Requisitos: `docs/arquitectura/REQUISITOS.md`. Despliegue: `docs/guias/PRODUCCION.md`.

## 1. Vista general

```
 Celular / tableta (Traccar Client o app Buses UTA)
        │  OsmAnd sobre HTTPS (gps.<dominio>)
        ▼
 ┌─────────────── Servidor Azure (Docker) ────────────────────────────────────────────┐
 │  Caddy (HTTPS, cabeceras)                                                            │
 │    ├─ <dominio>          ──► Odoo 16 (módulo bus_tracking + Fleet)                  │
 │    ├─ gps.<dominio>      ──► Traccar :5055 (protocolo OsmAnd) ──webhook──► Odoo     │
 │    ├─ traccar.<dominio>  ──► Traccar :8082 (panel y API)                             │
 │    └─ grafana.<dominio>  ──► Grafana (solo lectura, dentro de un iframe de Odoo)     │
 │  PostgreSQL: base de Odoo (+ vistas kpi_*) y base de Traccar                         │
 └──────────────────────────────────────────────────────────────────────────────────────┘
        ▲                                   ▲
 Navegador del gestor                 Pasajero (portal público, sin cuenta)
 (mapa, tablero, Grafana)
```

| Pieza | Función | Dónde |
|---|---|---|
| **Traccar 6.16** | Recibe las posiciones por OsmAnd, las guarda y las reenvía a Odoo (webhook con secreto) | `docker-compose*.yml` |
| **Odoo 16 + `bus_tracking`** | Guarda posiciones, evalúa recorridos y reglas, calcula indicadores, sirve el mapa, el portal, la API del chofer y el tablero | `addons/bus_tracking/` |
| **Odoo Fleet** | Registro de los vehículos de la empresa, enlazado con cada bus | `models/bus_fleet.py` |
| **Caddy** | HTTPS automático, cabeceras de seguridad, bloqueo del webhook y del administrador de bases desde fuera | `proxy/Caddyfile` |
| **Grafana 11.6** | Segundo tablero, incrustado; lee vistas SQL con un rol de solo lectura | `bi/grafana/` |
| **App Buses UTA (Expo)** | Cliente de operación del chofer: turno, GPS, incidentes, horario y retraso | `apps/conductor-tablet/` |
| **Azure con Caddy** | Alternativa equivalente a Cloudflare Tunnel (`docs/guias/DEMO-TRACCAR-CLIENT.md` §6) | `docs/guias/PRODUCCION.md` |

## 2. Cómo viaja un dato

1. El celular envía la posición a `https://gps.<dominio>` (OsmAnd). Traccar la guarda y **la reenvía** al webhook de Odoo; si el reenvío falla, la tarea periódica de Odoo **consulta** las últimas posiciones de Traccar.
2. `bus.vehicle._apply_position` **valida** (rango, NaN, hora), descarta duplicados (índice único `vehicle + hora`), exige un turno abierto (o un reporte de demostración) y guarda. Lo rechazado queda anotado sin su contenido (`bus.position.reject`).
3. Si hay un **recorrido programado** del bus a esa hora (`bus.trip`), una llegada a una parada actualiza su línea (`bus.trip.stop`): hora real, retraso y estado según la tolerancia.
4. Las **reglas** (`bus.alert`) escriben una vez por recorrido y parada: llegada tarde, parada omitida, recorrido incompleto, salida tarde; y mientras el bus anda: velocidad, sin señal, parada larga, fuera de ruta.
5. Al terminar la ventana del recorrido, la tarea de cierre lo **finaliza**: cuenta paradas, calcula duración, distancia recorrida y desviación (`bus.trip`).
6. Los **indicadores** (`bus.kpi`) se calculan con consultas SQL sobre esas tablas; el tablero de Odoo los pide por JSON y Grafana los lee por las vistas `kpi_*`.
7. Cada día, `bus.sync.audit` compara las posiciones de Traccar con las de Odoo y `bus.perf.sample` mide las consultas principales: de ahí salen S2 y S3.

## 3. Modelo de datos

```
bus.route 1───* bus.route.stop (minutos planificados por parada)
   │ 1                 ▲
   │                   │ stop_id
   ├───* bus.route.schedule (hora de salida, días, bus por defecto)
   │            │ 1
   │            └───* bus.trip ◄──────────────┐
   │                    │ 1                    │ trip_id
   │                    ├───* bus.trip.stop ───┘ (una línea por parada: planificada, real, retraso, estado)
   │                    ├───* bus.alert   (trip_id, stop_id, delay_min)
   │                    └───* bus.incident (trip_id)
bus.vehicle 1───* bus.position  (único vehicle + hora)
   │ 1  \──────* bus.shift ───* bus.incident
   │ *──1 bus.route        1──1 fleet.vehicle (placa, chofer, asientos, activo)
   └───* bus.alert / bus.trip / bus.sync.audit / bus.position.reject
```

| Modelo | Qué guarda | Notas |
|---|---|---|
| `bus.route`, `bus.route.stop` | Línea, color, trazado, distancia estimada; paradas con coordenadas, radio y minutos planificados | Los minutos no retroceden (restricción) |
| `bus.route.schedule` | Hora local de salida, días de la semana, bus por defecto | Genera los recorridos |
| `bus.trip` | Un recorrido programado: bus, ruta, inicio y fin planificados y reales, estado (programado, en curso, hecho, incompleto, cancelado), distancias, duración, desviación, retrasos, `simulated`, `scenario`, marcas esperadas y detectadas | Sin traslape de un mismo bus |
| `bus.trip.stop` | La parada de un recorrido: hora planificada y real, retraso (min) y estado | Es la base de T2, T3 y T4 |
| `bus.vehicle` | El bus que se rastrea: dispositivo Traccar, última posición, conexión, `simulated`, reporte de demostración, `fleet_vehicle_id` | Nombre único |
| `bus.position` | Cada posición válida | Índice único `(vehicle_id, fix_time)`; se borran las de más de 30 días |
| `bus.alert` | Alertas de las reglas con su recorrido y parada | Una por recorrido, tipo y parada |
| `bus.incident`, `bus.shift`, `bus.driver.token` | Incidentes y SOS del chofer, turnos, sesión de la tableta | Solo el chofer ve los suyos |
| `bus.position.reject`, `bus.sync.audit`, `bus.perf.sample` | Rechazos, auditoría de sincronización y tiempos de respuesta | Alimentan S1, S2 y S3 |
| `fleet.vehicle` (de Odoo) | El vehículo de la empresa | Sincronizado en los dos sentidos (`docs/arquitectura/FLEET.md`) |
| Vistas SQL `kpi_*` | Nueve vistas de solo lectura para Grafana, sin datos personales | `models/bus_kpi_views.py` |

La zona horaria de la operación es la de Ecuador (UTC−5, sin horario de verano): los horarios se escriben en hora local y se guardan en UTC; «un día» es siempre la fecha local.

## 4. Decisiones de diseño

| Decisión | Por qué |
|---|---|
| Mantener `bus.vehicle` y enlazarlo con Fleet, no reemplazarlo | Fleet no tiene dispositivo GPS, posición ni turnos; el enlace da lo mejor de los dos |
| Las reglas de recorrido son **eventos**: se escriben cerradas, una por hecho | No hay nada que «esperar» en un retraso ya ocurrido; evita alertas duplicadas |
| Los indicadores son **consultas SQL** mostradas junto a su cifra | La rúbrica prohíbe indicadores estáticos o que no puedan comprobarse |
| Los datos simulados se **marcan** (`simulated`, `scenario`) y se excluyen del mapa y del portal | Se pueden usar para probar sin presentarlos como reales |
| El simulador **solo produce posiciones** y entra por la misma ruta que el GPS real | Lo que se detecta lo deciden las reglas, no un guion escrito a mano |
| Grafana lee **vistas** con un rol de solo lectura y entra solo con un token de Odoo | Aunque un lector escriba SQL a mano, la base solo le deja leer las vistas |
| Dos tableros (Odoo y Grafana) con las mismas fórmulas, comprobadas por pruebas | El de Odoo cubre la rúbrica; Grafana añade análisis y mapas |
| Las tolerancias son ajustes del gestor | La UTA puede cambiar el criterio sin tocar el código |

## 5. Seguridad y privacidad (resumen)

El pasajero ve nombre, posición, rumbo y estado del bus, nunca placa, chofer ni historial. El identificador OsmAnd de un bus solo lo ven los gestores y viaja a la app al iniciar el turno. El webhook exige un secreto y no sale a Internet por el proxy.
Grafana no tiene registro ni acceso anónimo; su rol de base lee nueve vistas sin datos personales. Detalle: `docs/diseno/PRIVACIDAD.md` y `docs/guias/GRAFANA.md`.
