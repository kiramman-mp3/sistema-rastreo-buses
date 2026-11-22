# Arquitectura y modelo de datos

Entregable 2 del proyecto final. Describe cómo está armado el sistema, cómo viaja una posición desde el celular hasta un indicador, qué datos se guardan y por qué.
Versión del módulo: **16.0.1.11.0**. Requisitos: `docs/arquitectura/REQUISITOS.md`. Despliegue: `docs/guias/PRODUCCION.md`.

## 1. Vista general

```
 Celular / tableta (Traccar Client o app Buses UTA)
        │  OsmAnd sobre HTTPS (gps.<dominio>)
        ▼
 ┌─────────────── Servidor (Docker) ──────────────────────────────────────────────────┐
 │  Caddy (HTTPS, cabeceras)                                                            │
 │    ├─ <dominio>          ──► Odoo 16 (módulo bus_tracking + Fleet)                  │
 │    ├─ gps.<dominio>      ──► Traccar :5055 (protocolo OsmAnd) ──webhook──► Odoo     │
 │    └─ traccar.<dominio>  ──► Traccar :8082 (panel y API)                             │
 │  PostgreSQL: base de Odoo y base de Traccar                                         │
 └──────────────────────────────────────────────────────────────────────────────────────┘
        ▲                                   ▲
 Navegador del gestor                 Pasajero (portal público, sin cuenta)
 (mapa, tablero, reportes)
```

| Pieza | Función | Dónde |
|---|---|---|
| **Traccar 6.16** | Recibe las posiciones por OsmAnd, las guarda y las reenvía a Odoo (webhook con secreto) | `docker-compose*.yml` |
| **Odoo 16 + `bus_tracking`** | Guarda posiciones, evalúa recorridos y reglas, calcula indicadores, sirve el mapa, el portal, la API del chofer y el tablero | `addons/bus_tracking/` |
| **Odoo Fleet** | Registro de los vehículos de la empresa, enlazado con cada bus | `models/bus_fleet.py` |
| **Caddy** | HTTPS automático, cabeceras de seguridad, bloqueo del webhook y del administrador de bases desde fuera | `proxy/Caddyfile` |
| **App Buses UTA (Expo)** | Cliente de operación del chofer: turno, GPS, incidentes, horario y retraso | `apps/conductor-tablet/` |
| **Homelab con túnel de Cloudflare** | Despliegue vigente de la demostración (desde el 21-nov-2026): Cloudflare pone el HTTPS, Caddy sirve HTTP y un cron despliega `main` cada 5 minutos | `docs/guias/DESPLIEGUE-HOMELAB.md` |
| **Azure con Caddy** | Despliegue anterior y alternativa para un servidor con IP pública (`docs/guias/DEMO-TRACCAR-CLIENT.md` §6) | `docs/guias/PRODUCCION.md` |

## 2. Cómo viaja un dato

1. El celular envía la posición a `https://gps.<dominio>` (OsmAnd). Traccar la guarda y **la reenvía** al webhook de Odoo; si el reenvío falla, la tarea periódica de Odoo **consulta** las últimas posiciones de Traccar.
2. `bus.vehicle._apply_position` **valida** (rango, NaN, hora), descarta duplicados (índice único `vehicle + hora`), exige un turno abierto (o un reporte de demostración) y guarda. Lo rechazado queda anotado sin su contenido (`bus.position.reject`).
3. Si hay un **recorrido programado** del bus a esa hora (`bus.trip`), una llegada a una parada actualiza su línea (`bus.trip.stop`): hora real, retraso y estado según la tolerancia.
4. Las **reglas** (`bus.alert`) escriben una vez por recorrido y parada: llegada tarde, parada omitida, recorrido incompleto, salida tarde; y mientras el bus anda: velocidad, sin señal, parada larga, fuera de ruta.
5. Al terminar la ventana del recorrido, la tarea de cierre lo **finaliza**: cuenta paradas, calcula duración, distancia recorrida y desviación (`bus.trip`).
6. Cuando una alerta se cierra, el **detector de multas** (`bus.fine._cron_detect`, cada 5 minutos y disparado al cerrar una alerta o un recorrido) la mide de nuevo con las posiciones guardadas. Si supera el umbral de su tipo (`bus.fine.type`), propone una multa con su evidencia congelada y sus comprobaciones (`bus.fine`). Las alertas de un recorrido esperan a que el recorrido se cierre. Ver [`PLAN-MULTAS.md`](PLAN-MULTAS.md).
7. Los **indicadores** (`bus.kpi`) se calculan con consultas SQL sobre esas tablas; el tablero de Odoo los pide por JSON y el reporte PDF los imprime.
8. Cada día, `bus.sync.audit` compara las posiciones de Traccar con las de Odoo y `bus.perf.sample` mide las consultas principales: de ahí salen S2 y S3.

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

bus.fine.type 1───* bus.fine *───1 bus.alert (única), bus.vehicle, res.users (chofer)
                       │  *───1 bus.trip / bus.shift / bus.route (opcionales)
                       └ evidence_json, checks_json (congelados al crearla)
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
| `bus.fine.type` | Regla de multa: alerta de origen, umbral, duración mínima, gravedad, monto, reincidencia (días y factor), días para el descargo | Una activa por regla (índice parcial); datos iniciales con `noupdate` |
| `bus.fine` | Multa propuesta: chofer, bus, ruta, viaje, turno, alerta, valor y duración medidos, evidencia y comprobaciones en JSON, montos propuesto y aplicado, estado (nueva, en revisión, multada, apelada, descartada), decisión, descargo y respuesta | Hereda `mail.thread`; única por alerta; los textos se escriben al leerla, en el idioma de quien lee |
| `bus.fine.discard` | Asistente para descartar con motivo y nota | Transitorio |
| `fleet.vehicle` (de Odoo) | El vehículo de la empresa | Sincronizado en los dos sentidos (`docs/arquitectura/FLEET.md`) |

La zona horaria de la operación es la de Ecuador (UTC−5, sin horario de verano): los horarios se escriben en hora local y se guardan en UTC; «un día» es siempre la fecha local.

## 4. Decisiones de diseño

| Decisión | Por qué |
|---|---|
| Mantener `bus.vehicle` y enlazarlo con Fleet, no reemplazarlo | Fleet no tiene dispositivo GPS, posición ni turnos; el enlace da lo mejor de los dos |
| Las reglas de recorrido son **eventos**: se escriben cerradas, una por hecho | No hay nada que «esperar» en un retraso ya ocurrido; evita alertas duplicadas |
| Los indicadores son **consultas SQL** mostradas junto a su cifra | La rúbrica prohíbe indicadores estáticos o que no puedan comprobarse |
| Los datos simulados se **marcan** (`simulated`, `scenario`) y se excluyen del mapa y del portal | Se pueden usar para probar sin presentarlos como reales |
| El simulador **solo produce posiciones** y entra por la misma ruta que el GPS real | Lo que se detecta lo deciden las reglas, no un guion escrito a mano |
| Las tolerancias son ajustes del gestor | La UTA puede cambiar el criterio sin tocar el código |
| El sistema **propone** multas y una persona decide | Una multa sin revisión humana no tendría debido proceso; la tasa de descarte mide la precisión del detector |
| La evidencia de una multa se **congela** en la multa | Las posiciones se borran a los 30 días; la multa debe seguir siendo verificable |
| Si falla una comprobación (sin chofer, incidente reportado, GPS insuficiente) la multa nace **descartada por el sistema** | Se ve que el sistema también sabe no multar, y queda la razón |
| Una sola infracción no se multa dos veces | Las paradas omitidas en medio son *parada omitida*; las que faltan al final, *recorrido incompleto*; un recorrido que no empezó es *salida tardía* |

## 5. Seguridad y privacidad (resumen)

El pasajero ve nombre, posición, rumbo y estado del bus, nunca placa, chofer ni historial. El identificador OsmAnd de un bus solo lo ven los gestores y viaja a la app al iniciar el turno. El webhook exige un secreto y no sale a Internet por el proxy.
