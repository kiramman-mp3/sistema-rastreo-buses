# Control de multas a choferes

Fecha: 2026-11-20. Base: `develop` en `aa20274` (módulo `16.0.1.9.0`, app de tableta `1.3.1`).

## 0. Propósito y alcance

Demostrar cómo el sistema apoyaría a la empresa en el control de multas a choferes. Las multas son **ficticias** (montos de demostración en dólares), pero cada una es **verificable**: el administrador ve con los datos reales del GPS por qué el sistema la recomienda.

El sistema **no multa solo**. Detecta una infracción, hace las comprobaciones y propone una multa *Nueva*. Una persona la revisa, la confirma o la descarta, y el chofer puede presentar su descargo desde la tableta.

Decisiones del usuario (20-nov):

| Tema | Decisión |
|---|---|
| Columna *Apelada* y descargo desde la tableta | Sí |
| Moneda | Dólares (ficticios) |
| Viajes simulados | También generan multas fuera del modo demostración; quedan marcadas como simuladas |
| Velocidad | Límite de 50 km/h, con tolerancia hasta 70 km/h: entre 50 y 70 hay alerta, pero no multa |

Marco legal (para la empresa real, no lo aplica el sistema): en Ecuador una multa al trabajador solo vale si consta en el reglamento interno aprobado por el Ministerio del Trabajo, y el Código del Trabajo (art. 44, literal b) prohíbe descontar más del 10 % de la remuneración por multas. Por eso hay un tope mensual configurable.

## 1. Reglas de multa

Cada regla nace de una alerta que el sistema ya genera (`bus.alert`). Son parametrizables en *Buses > Multas > Configuración > Tipos de multa*. Los valores de la tabla son los que vienen por defecto.

| Regla | Alerta de origen | Umbral de multa | Duración mínima | Gravedad | Monto |
|---|---|---|---|---|---|
| Exceso de velocidad | `speeding` (abre sobre 50 km/h) | más de 70 km/h | 30 s seguidos | Grave | $25 |
| Desvío de ruta | `off_route` (corredor de 150 m) | más de 300 m de la ruta | 3 min | Grave | $20 |
| Parada prolongada | `long_stop` | — | 20 min detenido lejos de una parada | Leve | $10 |
| Parada omitida | `skipped_stop` | pasó a más del radio de la parada | — | Leve | $10 |
| Salida tardía | `late_start` | más de 10 min de retraso real | — | Leve | $5 |
| Viaje incompleto | `incomplete_trip` | al menos 1 parada sin llegar | — | Grave | $15 |

Nunca generan multa: *sin señal* (`offline`), porque puede fallar la tableta o la cobertura, y *llegada tardía* (`late_arrival`), que casi siempre es tráfico.

Reincidencia: si el chofer tiene una multa confirmada del mismo tipo en los últimos 30 días, el monto se multiplica por 1,5. Ambos valores se configuran por tipo.

Tope mensual: en Ajustes, por defecto 0 (sin tope). Al confirmar una multa, el monto aplicado no supera lo que queda del tope del mes del chofer; si se recorta, la multa lo dice.

## 2. Comprobaciones

Antes de proponer una multa, el sistema verifica:

1. **Chofer identificado:** había un turno (`bus.shift`) del bus a esa hora o, si no, el viaje programado tenía chofer asignado.
2. **Sin incidentes:** el bus no reportó avería, accidente, tráfico, SOS u otro incidente entre 30 minutos antes y el final del evento, ni durante el viaje en las reglas de viaje.
3. **Señal GPS suficiente:** hay al menos 2 posiciones en el tramo y ningún hueco de más de 2 minutos entre ellas.
4. **Umbral superado:** valor y duración por encima de lo configurado en el tipo.

Si falla la 4, no hay infracción: no se crea nada. Si falla la 1, la 2 o la 3, la multa se crea directamente en *Descartada* con el motivo "Descartada por el sistema", para que se vea que el sistema también sabe no multar.

Las reglas de viaje (parada omitida, salida tardía, viaje incompleto) se evalúan cuando el viaje se cierra, así la salida tardía usa el retraso real y no el aviso de los 10 minutos.

## 3. Estados (Kanban)

```
Nueva ──► En revisión ──► Multada ──► Apelada ──► Multada (apelación rechazada)
  │            │                         │
  └────────────┴──► Descartada ◄─────────┘ (apelación aceptada)
```

| Estado | Quién la mueve | Qué guarda |
|---|---|---|
| Nueva | El sistema | Evidencia, comprobaciones, monto propuesto |
| En revisión | Supervisor | Quién la tomó |
| Multada | Supervisor | Quién decidió, cuándo, monto aplicado y plazo de apelación |
| Apelada | Chofer, desde la tableta, dentro del plazo (3 días por defecto) | Texto del descargo y fecha |
| Descartada | Supervisor (con motivo) o el sistema | Motivo de una lista y nota |

Arrastrar tarjetas respeta las mismas reglas: no se puede descartar sin motivo (se abre el asistente), ni mover a *Apelada* desde el panel, ni volver a *Nueva*. Una apelación se resuelve una sola vez.

## 4. Evidencia verificable

La evidencia se **congela** en la multa al crearla (posiciones del tramo, línea de la ruta, paradas): la retención borra las posiciones a los 30 días y la multa no puede quedarse sin pruebas.

| Regla | Mapa | Datos |
|---|---|---|
| Exceso de velocidad | Recorrido en gris y tramo sobre 70 km/h en rojo, inicio y fin | Gráfico velocidad/tiempo con las líneas de 50 y 70; segundos, máxima, promedio y metros en exceso |
| Desvío de ruta | Ruta planificada, corredor y recorrido real en rojo donde salió | Distancia máxima, minutos y km fuera, punto de salida y de regreso |
| Parada prolongada | Puntos donde estuvo detenido y la parada más cercana | Minutos, hora de inicio y fin, distancia a la parada más cercana |
| Parada omitida | La parada con su radio y el recorrido pasando de largo | Distancia mínima a la que pasó y a qué hora |
| Salida tardía | Dónde estaba el bus a la hora planificada | Hora planificada, hora real y minutos de retraso |
| Viaje incompleto | Paradas alcanzadas y faltantes, último punto | Paradas alcanzadas sobre el total |

## 5. Modelo de datos

- `bus.fine.type`: nombre, regla, activa, gravedad, monto base, umbral, duración mínima, días y factor de reincidencia, días para apelar, descripción.
- `bus.fine` (con `mail.thread`): número (`MUL-0001`), tipo, regla, estado, chofer, bus, ruta, viaje, turno, alerta de origen (única), inicio y fin del evento, valor medido, duración medida, umbral, resumen en texto, evidencia (JSON), comprobaciones (JSON), monto propuesto, monto aplicado, reincidencia, simulada, revisor y fecha de decisión, motivo y nota de descarte, descargo, fecha y plazo de apelación, resultado de la apelación.
- `bus.alert.fine_checked`: la alerta ya pasó por el detector. La migración `16.0.1.10.0` marca las alertas existentes para no multar retroactivamente.
- Ajustes: tope mensual y aviso de "multas de demostración" visible en la ficha.

Permisos: el usuario del transporte lee las multas; el gerente las gestiona. El chofer no entra al panel: la API le da solo sus multas confirmadas, apeladas o resueltas.

## 6. Tableta

- `POST /bus_tracking/driver/fines`: las multas del chofer desde *Multada* (nunca las *Nuevas* ni *En revisión*), con resumen, monto, plazo y si puede apelar.
- `POST /bus_tracking/driver/fines/appeal`: `{id, text}` dentro del plazo; un solo descargo por multa.
- Pantalla *Mis multas* en la app, con el detalle y el formulario de descargo; en español, inglés y kichwa.

## 7. Reportes

- Tablero: pestaña *Multas* con multas por estado y chofer, por tipo, evolución por semana, tasa de descarte por regla (precisión del detector), monto por estado y mapa de dónde ocurren.
- PDF de operación: tabla de multas por chofer y estado.
- Vistas de lista, gráfico y pivote del modelo.

## 8. Simulador

- El asistente *Simular viajes* recibe un chofer opcional, que queda como chofer del viaje, para que sus multas tengan a quién atribuirse.
- El escenario *Exceso de velocidad* pasa a 82 km/h (antes 68) para superar la tolerancia, y se agrega *Exceso tolerado* (62 km/h: alerta sin multa).
- Nuevo escenario *Parada prolongada* (25 min detenido lejos de las paradas). Para detectarlo en un viaje reproducido, la regla de parada prolongada se evalúa también cuando el bus vuelve a moverse, no solo en el cron.

## 9. Fases

| Fase | Rama | Contenido | Tamaño |
|---|---|---|---|
| M1 | `feature/multas-modelo` | Modelos, datos iniciales, permisos, secuencia, ajustes, migración | M |
| M2 | `feature/multas-deteccion` | Detector, comprobaciones, evidencia, cron, simulador, pruebas | L |
| M3 | `feature/multas-panel` | Kanban, ficha con mapa y gráfico, transiciones, descarte con motivo, menú | M |
| M4 | `feature/multas-tableta` | API del chofer, pantalla *Mis multas* y descargo, pruebas de Jest | M |
| M5 | `feature/multas-reportes` | Pestaña del tablero, sección del PDF | M |
| M6 | `docs/multas` | Roadmap, bitácora, arquitectura, privacidad, guías, README, calidad | S |

Cada fase se integra a `develop` con `git merge --no-ff` después de pasar la suite de Odoo, `qa/traducciones.py` y, en M4, lint, typecheck y Jest de la tableta.
