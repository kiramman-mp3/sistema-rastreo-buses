# Plan de implementación para cubrir la rúbrica del proyecto final

Fuente: `proyectoFinal_GC.pdf` (Proyecto final integrador, Gestión de Calidad del Software). Este plan lleva el proyecto desde el
estado verificado el **2026-11-04** hasta cubrir las 10 actividades, los 10 entregables y los 10 criterios de la rúbrica. El
resumen de la brecha está en la sección 1; las fases (R1 a R12) en la sección 4.

Estados: **[HECHO]** verificado en el código o en la documentación, **[PARCIAL]** existe pero no cubre todo lo que pide el PDF,
**[FALTA]** no existe.

## 0. Estado base verificado (2026-11-04)

| Pide el PDF | Hoy |
|---|---|
| Odoo 16 con el módulo **Fleet** (Act. 2) | **[FALTA]** `fleet` está disponible en la imagen pero no instalado, y `bus_tracking` no depende de él. Los vehículos están en un modelo propio, `bus.vehicle`. |
| Traccar Server, conectividad externa (Act. 2) | **[HECHO]** Azure con Caddy y HTTPS, aceptado por el PDF como alternativa equivalente a Cloudflare Tunnel. |
| Traccar Client y prueba con datos móviles (Act. 2 y defensa) | **[PARCIAL]** el proyecto usa su propia app de tableta (protocolo OsmAnd). Falta evidencia con Traccar Client y por datos móviles, y el servidor descarta posiciones de un bus sin turno abierto. |
| Integración Odoo–Traccar (Act. 3) | **[HECHO]** webhook y cron, sin duplicados, control de señal, historial y mapa. |
| Vehículos, rutas y paradas, con mínimos (Act. 4) | **[HECHO]** 6 buses, 4 rutas, de 4 a 6 paradas por ruta. |
| **Horarios previstos** de rutas y paradas; **asignación por fecha y horario** (Act. 4) | **[FALTA]** no hay ningún campo de horario. |
| Registro de recorridos con hora programada y real, distancia estimada y recorrida (Act. 5) | **[PARCIAL]** hay hora real, posiciones, velocidad y llegadas a paradas. Faltan hora programada, distancias y vínculo de las incidencias con el recorrido. |
| 10 recorridos de prueba documentados (Act. 5) | **[FALTA]** |
| Reglas: retraso, parada omitida, recorrido incompleto, tiempo estimado contra real (Act. 6) | **[FALTA]** solo existen 4 alertas: velocidad, sin señal, parada larga y fuera de ruta. |
| 8 métricas de transporte y 4 de software, con fórmula, fuente, unidad, resultado e interpretación (Act. 7) | **[PARCIAL]** el cuadro de mando de `04-resultados-y-metricas.md` mide la calidad del sistema; no hay tabla de las métricas pedidas. |
| Tablero en Odoo o Power BI integrado (Act. 8) | **[FALTA]** no hay vistas de gráfico ni pivote. |
| Pruebas, matriz de casos, ISO/IEC 25010 (Act. 9) | **[HECHO]** 289 pruebas de Odoo, 165 de la tableta, suite en vivo y auditoría. **[PARCIAL]** rendimiento por volumen de registros. |
| **SonarQube** (Act. 9) | **[FALTA]** sin configuración ni reporte. |
| Ishikawa, Pareto y PDCA (Act. 10) | **[HECHO]** 38 defectos, con causa raíz y comparación antes y después. |

> La documentación anterior marcaba como hechos los viajes con horario, la puntualidad y los recorridos oficiales. Ese código no está
> en el repositorio actual: aquí se reconstruye (R1 a R5) y `PLAN.md` ya lo refleja como pendiente.

## 1. Trazabilidad: criterio de la rúbrica → fases

| # | Criterio (puntos) | Hoy | Fases que lo cubren | Evidencia final |
|---|---|---|---|---|
| 1 | Análisis y requisitos (10) | Bueno | R12 | `docs/calidad/01-politica-y-alcance.md` con RF/RNF de horarios, métricas y tablero, cada uno con criterio de aceptación |
| 2 | Arquitectura e infraestructura (10) | Parcial | R8, R9 | Fleet instalado, capturas de Traccar Client por datos móviles, justificación de la alternativa a Cloudflare |
| 3 | Integración Odoo–Traccar y monitoreo GPS (15) | Bueno | R9, R5 (S2) | Prueba con Traccar Client, auditoría de sincronización |
| 4 | Rutas, paradas y recorridos: horarios y asignaciones (10) | Falta | R1, R2, R8 | Formularios de horarios, asignación por fecha y hora, recorridos |
| 5 | Historial e incidencias: retrasos, desvíos, incumplimientos (10) | Parcial | R2, R3, R4 | Alertas automáticas con sus reglas, 10 recorridos documentados |
| 6 | Métricas y tablero (15) | Falta | R5, R6, R7 | Tabla de 12 métricas con fórmulas y consultas, tablero en Odoo, Power BI opcional |
| 7 | Pruebas funcionales, integración y rendimiento (10) | Bueno | R11 (más las de cada fase) | Matriz ampliada, rendimiento por volumen |
| 8 | Calidad del software: ISO 25010 y SonarQube (10) | Parcial | R10, R12 | Reporte de SonarQube con el Quality Gate interpretado, ISO actualizada |
| 9 | Mejora continua (5) | Bueno | R12 | Ishikawa, Pareto y PDCA con defectos nuevos de esta etapa |
| 10 | Presentación y defensa (5) | Parcial | R9, R12 | Guion con las 11 preguntas y su consulta en pantalla, ensayo con un caso de cumplimiento y uno de incumplimiento |

## 2. Principios

1. **Sin valores estáticos.** Cada indicador se calcula de los registros (consulta SQL u ORM) y se actualiza al entrar un recorrido nuevo; la tabla de
   métricas incluye la consulta que lo comprueba. Es una restricción explícita del PDF.
2. **Los datos simulados se identifican.** Todo recorrido o posición generada por script lleva `simulated = True` y un `scenario`; no se mezcla en
   silencio con datos reales. Es lo que permite el PDF ("datos de prueba identificados como simulados").
3. **Todo con prueba.** Cada regla nueva trae pruebas de caja negra (válidos, inválidos y límites) y de caja blanca (ramas).
4. **Flujo Git del proyecto:** una rama por fase (`feature/r1-horarios`, ...), commits pequeños con Conventional Commits, integración a `develop` con
   `--no-ff` cuando pasan pruebas, linter y compilación; `main` solo con versiones estables.
5. **Migraciones seguras:** cada cambio de modelo trae migración y se prueba sobre una copia de la base de producción restaurada con `restore.sh`.

## 3. Orden y dependencias

```
R1 horarios y asignación ──► R2 recorrido y registro ──► R3 reglas ──► R4 10 recorridos simulados
                                                            │                    │
                                                            └────► R5 métricas ◄─┘
                                                                      │
                                                    R6 tablero Odoo ◄─┘ ──► R7 Power BI (opcional)
R8 Fleet   R9 Traccar Client   R10 SonarQube        (independientes, en paralelo)
R11 pruebas y rendimiento (después de R5)           R12 documentación y defensa (incremental, cierra al final)
```

| Fase | Tamaño relativo | Riesgo principal |
|---|---|---|
| R1 | Grande | Modelo de datos: es la base de todo lo demás |
| R2 | Mediano | Asociar posiciones al recorrido correcto |
| R3 | Grande | Reglas con tolerancias bien justificadas |
| R4 | Mediano | Que los datos simulados parezcan reales sin presentarse como reales |
| R5 | Grande | Definir cada fórmula sin ambigüedad |
| R6 | Grande | Que se vea bien y se actualice solo |
| R7 | Mediano | Licencias y autenticación de Power BI, ajenas al repositorio |
| R8 | Pequeño | Migración de los buses existentes |
| R9 | Pequeño | Prueba física con un celular |
| R10 | Pequeño a mediano | Ruido de hallazgos que hay que clasificar |
| R11 | Mediano | Generar volúmenes grandes sin ensuciar la base |
| R12 | Mediano | Consistencia entre documentos |

## 4. Fases

### R1. Horarios previstos y asignación de rutas por fecha y horario (Act. 4, criterio 4)

**Cubre:** "origen, destino, distancia estimada y horarios previstos", "horarios programados" en las paradas, "asignar una ruta a un vehículo
para una fecha y horario", "un mismo vehículo realiza diferentes rutas en distintos horarios".

**Diseño de datos**
- `bus.route`: `distance_km` (guardado, calculado del trazado o de las paradas), `origin_stop_id` y `destination_stop_id` (primera y última parada).
- `bus.route.stop`: `planned_offset_min` (minutos desde la salida del origen; no decrece a lo largo de la ruta; restricción).
- `bus.route.schedule` (horario): `route_id`, `name`, `departure_time` (hora local de Ecuador), días de la semana, `active`.
- `bus.trip` (recorrido asignado): `vehicle_id`, `route_id`, `schedule_id`, `date`, `planned_start`, `planned_end` (calculada), `driver_id`, `state`
  (`planned`, `running`, `done`, `incomplete`, `cancelled`), `simulated`, `scenario`. Restricción: un bus no puede tener dos recorridos que se solapen,
  pero sí rutas distintas en horas distintas.
- `bus.trip.stop`: `trip_id`, `stop_id`, `sequence`, `planned_time`, `actual_time`, `delay_min`, `status` (`pending`, `on_time`, `late`, `early`, `skipped`).

**Tareas:** modelos, seguridad y menús («Horarios», «Recorridos»); asistente «Asignar ruta a un bus» (rango de fechas y horario); cron que genera los
recorridos de los próximos días desde los horarios; vistas de lista, formulario, calendario y pivote.
**Pruebas:** el solapamiento se rechaza; el mismo bus con dos rutas en horas distintas se acepta; cálculo de `planned_time` por parada;
horarios que cruzan la medianoche; días de la semana.
**Evidencia:** formularios de horario y de asignación, captura del calendario de recorridos.
**Aceptación:** crear 3 rutas con horarios, asignar el mismo bus a dos de ellas en horas distintas y comprobar que un tercer recorrido solapado falla.
**Rama:** `feature/r1-horarios`.

### R2. Recorrido y registro completo de lo que pide la Actividad 5 (criterios 4 y 5)

**Cubre:** vehículo y ruta, fecha y hora, coordenadas, velocidad, hora programada y real de inicio y de llegada, distancia estimada y recorrida,
puntos de control visitados, incidencias detectadas.

**Tareas**
- Asociar cada `bus.stop.arrival` y cada posición al recorrido que corresponde (ventana entre `planned_start` menos un margen y `planned_end` más un margen).
- Máquina de estados: `planned → running` (primera llegada al origen o inicio de turno), `running → done` (última parada), `running → incomplete`
  (la ventana termina sin completar la ruta).
- `distance_real_km`: suma de distancias entre posiciones consecutivas del recorrido (con el filtro de ruido que ya usa `thin`); `distance_est_km` desde la ruta.
- `trip_id` en `bus.alert` y `bus.incident`; los incidentes y las alertas quedan en la línea de tiempo del recorrido.
- Tableta: la API de estado añade la hora prevista de la próxima parada y el retraso; la pantalla del turno muestra «Debes llegar 08:15 · +3 min».
**Pruebas:** el recorrido se cierra al llegar a la última parada; con una parada omitida pasa a `incomplete`; la distancia real contra una recta conocida;
posiciones fuera de ventana no se asocian.
**Evidencia:** formulario de un recorrido con paradas, tiempos, distancias e incidencias.
**Rama:** `feature/r2-recorridos`.

### R3. Reglas de incumplimiento con tolerancias justificadas (Act. 6, criterio 5)

**Cubre:** retrasos, incumplimiento de puntos de control, desviaciones, recorridos incompletos, diferencias de tiempo, pérdida de señal.

**Reglas nuevas** (las de velocidad, sin señal, parada larga y desvío ya existen):

| Regla | Condición por defecto | Justificación a escribir |
|---|---|---|
| Retraso | llegada a una parada más de `punctuality_tolerance_min` (5 min) después de la hora prevista | tráfico urbano de Ambato; ejemplo del PDF: 08:15 con 5 min y llegada 08:23 es un retraso de 8 min |
| Parada omitida | el recorrido termina y una parada no tiene llegada dentro de su radio | radio de 50 m y cobertura de GPS |
| Recorrido incompleto | la ventana termina con menos del 100 % de las paradas, o el bus nunca llegó al destino | |
| Salida tardía | el recorrido no inicia pasados 10 min de la hora prevista | |
| Diferencia de tiempo | duración real contra estimada fuera de ±`time_diff_pct` | |

**Tareas:** tipos nuevos de alerta (`late_arrival`, `skipped_stop`, `incomplete_trip`, `late_start`); el índice único actual (una alerta abierta por bus y tipo)
se revisa porque estas alertas son por recorrido; ajustes nuevos en *Configuración*; avisos push; `docs/calidad/02-estandares-y-reglas.md` con cada tolerancia y su porqué.
**Pruebas:** valores límite exactos (5 min 00 s, 5 min 01 s), llegada adelantada, parada omitida en el medio y al final, doble llegada.
**Evidencia:** demostración de un caso de cumplimiento y uno de incumplimiento (lo que pide la defensa).
**Rama:** `feature/r3-reglas`.

### R4. Diez o más recorridos de prueba documentados (Act. 5)

**Tareas**
- Script `scripts/seed_recorridos.py` que crea recorridos simulados y los reproduce por la misma ruta de ingesta que usa Traccar (no escribe los resultados a mano).
- Escenarios (mínimo 12 repartidos entre las 4 rutas): puntual, atrasado, adelantado, con parada omitida, con desvío, incompleto, con pérdida de señal,
  exceso de velocidad, doble vuelta, y uno real grabado con un celular (R9).
- Cada recorrido lleva `simulated = True` y `scenario`; el resultado esperado queda guardado para medir la detección (métrica S4).
- Documento `docs/calidad/13-recorridos-de-prueba.md` generado desde la base: tabla de recorridos, escenario, resultado esperado, resultado detectado, capturas del trazado sobre el mapa.
**Aceptación:** los 12 recorridos reproducibles con un solo comando, cada uno con el resultado detectado por el sistema coincidiendo con el esperado.
**Rama:** `feature/r4-recorridos-simulados`.

### R5. Métricas e indicadores (Act. 7, criterio 6)

Cada indicador tendrá fórmula, fuente de datos, unidad, resultado (calculado), interpretación y la consulta que lo reproduce.

**Transporte**

| # | Indicador | Fórmula | Unidad |
|---|---|---|---|
| 1 | Cumplimiento de rutas | recorridos `done` ÷ recorridos programados ya vencidos × 100 | % |
| 2 | Puntualidad | llegadas con retraso ≤ tolerancia ÷ llegadas registradas × 100 | % |
| 3 | Retraso promedio | promedio de `max(0, delay_min)` de las llegadas con retraso | min |
| 4 | Paradas cumplidas | paradas visitadas ÷ paradas previstas × 100 | % |
| 5 | Desviación respecto a la ruta | distancia media y máxima de las posiciones al trazado; % de posiciones dentro del corredor de 150 m | m, % |
| 6 | Distancia estimada contra recorrida | (km reales − km estimados) ÷ km estimados × 100 | % |
| 7 | Tiempo promedio de recorrido | promedio de la duración real, contra la estimada | min |
| 8 | Incidencias | número, por recorrido y por 100 km; frecuencia por tipo | n, n/100 km |

**Software**

| # | Indicador | Cómo se calcula con datos reales |
|---|---|---|
| S1 | Integridad de los registros GPS | posiciones válidas ÷ posiciones recibidas; hay que contar también las rechazadas (hoy se descartan sin contarlas) |
| S2 | Exactitud de la sincronización Traccar–Odoo | acción «Auditar sincronización»: compara `/api/positions` de Traccar con `bus.position` (mismo dispositivo y hora, coordenadas a 1e-6) |
| S3 | Tiempo de respuesta | muestras de tiempo de los endpoints de ingesta, mapa y tablero, con p50 y p95 |
| S4 | Detección correcta de incidencias | sobre los recorridos simulados: detectadas que coinciden con lo esperado ÷ esperadas (precisión y exhaustividad) |

**Tareas:** vistas SQL o consultas ORM por indicador; modelo de solo lectura `bus.kpi` para el tablero; contador de posiciones rechazadas; `qa/metricas_transporte.sql`;
regeneración de `docs/calidad/04-resultados-y-metricas.md` por `qa/generar_docs.py`.
**Pruebas:** cada indicador contra un conjunto de datos construido a mano con resultado conocido (caja blanca); cambiar un dato cambia el indicador (prueba de que no es estático).
**Rama:** `feature/r5-metricas`.

### R6. Tablero en Odoo (Act. 8, alternativa A, criterio 6)

**Diseño:** acción de cliente OWL «Indicadores» con la paleta de la marca (granate, amarillo de señal, tinta), Chart.js (ya viene en Odoo 16) y los
filtros de periodo, ruta y bus. Se actualiza solo al entrar recorridos nuevos (consulta cada 30 s).

| Pestaña | Contenido |
|---|---|
| Resumen | 12 tarjetas de indicador con semáforo, tendencia y comparación con el periodo anterior |
| Rutas | comparación entre rutas: puntualidad, retraso, cumplimiento, distancia real contra estimada (barras agrupadas) |
| Puntualidad | retraso por parada (mapa de calor), distribución de retrasos, llegadas por hora |
| Recorridos | tabla filtrable con estado, retraso total y distancia; al elegir uno, su trazado sobre el mapa y su línea de tiempo |
| Incidencias | por tipo (anillo), Pareto de causas, frecuencia por día y por ruta |
| Calidad del sistema | S1 a S4, latencias, estado de la sincronización |

Además, vistas `graph` y `pivot` sobre `bus.trip`, `bus.trip.stop` y `bus.alert` para análisis libre.
**Pruebas:** datos del tablero contra las consultas de R5; permisos por grupo; el tablero cambia al añadir un recorrido; capturas en escritorio y móvil.
**Evidencia:** tablero funcional dentro de Odoo con los indicadores y comparaciones entre rutas y periodos que enumera el PDF.
**Rama:** `feature/r6-tablero`.

### R7. Power BI integrado (Act. 8, alternativa B, opcional)

El PDF pide elegir una de las dos alternativas. R6 es la entrega que no depende de licencias; R7 la complementa.

**Lo que se entrega desde el repositorio**
- Capa de datos para Power BI: puntos de exportación autenticados `/bus_tracking/export/<conjunto>.csv|json` con token de gestor, sin datos personales
  (sin nombre del chofer ni placa), para los conjuntos de recorridos, paradas, alertas, posiciones diarias, rutas e indicadores.
- Carpeta `bi/powerbi/` con un proyecto de Power BI (formato PBIP): modelo con relaciones, las medidas DAX de los 12 indicadores, tema con la paleta de la marca y la
  especificación de las páginas.
- Un campo en *Configuración* con la dirección del informe y una pantalla «Power BI» dentro de Odoo que lo incrusta; cabecera de Caddy para permitir `app.powerbi.com`.

**Lo que no se puede hacer desde aquí**
- Publicar el informe en un espacio de trabajo y su licencia (Pro, Premium por usuario o capacidad Embedded). Lo hace la persona con la cuenta de Microsoft.
- Comprobar cómo se ve: Power BI Desktop solo corre en Windows y no está en este entorno. La entrega se marca **[HECHO*]** hasta abrirla en Desktop.
- **No se usará «Publicar en la web»:** hace público el informe y expondría posiciones de buses; contradice `docs/diseno/PRIVACIDAD.md`. Solo incrustación segura con inicio de sesión.
**Rama:** `feature/r7-powerbi`.

### R8. Módulo Fleet (Act. 2, criterio 2)

**Diseño:** `bus_tracking` depende de `fleet`; `bus.vehicle.fleet_vehicle_id` apunta a un `fleet.vehicle` que se crea solo (marca «UTA», modelo «Bus»), con la placa, el chofer
y la capacidad sincronizados. `bus.vehicle` sigue guardando lo propio del rastreo (Traccar, última posición, alertas, turnos).
**Tareas:** dependencia y datos del modelo «Bus UTA»; migración que enlaza los buses existentes; botón «Abrir en Fleet»; menú de Fleet visible para los gestores; documentación de la decisión de mantener `bus.vehicle`.
**Pruebas:** crear un bus crea su vehículo de Fleet; editar la placa en uno actualiza el otro; la migración enlaza los existentes sin duplicar.
**Evidencia:** captura de los buses en Fleet con su dispositivo GPS asociado.
**Rama:** `feature/r8-fleet`.

### R9. Traccar Client y conectividad externa (Act. 2, criterio 3, defensa)

**Tareas:** marca por bus «reporte de demostración» que acepta posiciones sin turno (más segura que el ajuste global que existe hoy); guía `docs/guias/DEMO-TRACCAR-CLIENT.md`
(instalar Traccar Client, identificador del dispositivo, dirección `https://gps.<dominio>`, intervalo de 5 s); lista de evidencias: captura del celular con Wi-Fi apagado y datos móviles, la posición
apareciendo en Odoo, y el recorrido; sección que argumenta por qué Azure con Caddy es la alternativa equivalente a Cloudflare Tunnel. La app de tableta sigue siendo el cliente de operación.
**Pruebas:** una posición de un bus marcado para demostración se guarda sin turno; sin la marca se sigue descartando.
**Rama:** `feature/r9-traccar-client`.

### R10. SonarQube (Act. 9, criterio 8)

**Tareas:** `sonar-project.properties` (Python y TypeScript, exclusiones de `node_modules` y de pruebas como código de prueba); `docker-compose.sonar.yml` solo para desarrollo con `sonarqube:community`;
cobertura de Python (Odoo) y de Jest en el análisis; ejecución con `sonar-scanner`; clasificación de hallazgos (bugs, vulnerabilidades, puntos de seguridad, deuda técnica, duplicaciones), corrección de los
críticos y justificación de los que se aceptan; `docs/calidad/14-sonarqube.md` con capturas del Quality Gate y la interpretación. Opcional: trabajo en el CI con `SONAR_TOKEN`.
**Evidencia:** reporte exportado, capturas y el antes y después de los hallazgos corregidos.
**Rama:** `chore/r10-sonarqube`.

### R11. Pruebas y rendimiento (Act. 9, criterio 7)

**Tareas**
- Caja negra de las reglas nuevas (válidos, inválidos, límite) y caja blanca de los cálculos de retraso, parada omitida y métricas (cobertura de ramas).
- Integración Traccar–Odoo: prueba de consistencia con la auditoría de sincronización (S2).
- Rendimiento por volumen: `qa/rendimiento_volumen.py` con 1.000, 10.000 y 100.000 posiciones y 100, 1.000 y 5.000 recorridos; mide el mapa en vivo, el historial de un bus,
  la lista de recorridos, los indicadores y el tablero (p50 y p95); añade índices donde haga falta (por ejemplo `(vehicle_id, fix_time)`).
- Matriz de casos ampliada (pasa de 10 casos mínimos a la matriz completa con entradas, esperados, obtenidos y evidencia) y actualización del mapa de ISO/IEC 25010.
**Rama:** `feature/r11-pruebas`.

### R12. Mejora continua, documentación y defensa (criterios 1, 9, 10)

**Tareas**
- Requisitos: RF y RNF nuevos (horarios, retrasos, métricas, tablero, Fleet) con criterio de aceptación; arquitectura y modelo de datos actualizados con los modelos de R1 y R2.
- Mejora continua: los defectos que aparezcan en R1 a R11 entran al registro, con Ishikawa, Pareto actualizado y un PDCA con la comparación antes y después.
- Documentos: `PLAN.md` y la bitácora al día, `docs/calidad/` regenerado, informe PDF regenerado.
- Guion de defensa con las 11 preguntas del PDF, cada una con la pantalla o consulta que la responde (sección 5), y un ensayo con un caso de cumplimiento y uno de incumplimiento.
- Matriz de trazabilidad final: cada actividad y cada entregable con su archivo de evidencia.
**Rama:** `docs/r12-cierre`.

## 5. Preguntas de la defensa y dónde se responden

| Pregunta | Dónde |
|---|---|
| ¿Dónde está el vehículo? | Mapa en vivo de Odoo y portal de pasajeros |
| ¿Qué ruta realiza? | Recorrido asignado (R1), cabecera del turno en la tableta |
| ¿Qué paradas visitó? | Línea de tiempo del recorrido (R2), tira de paradas |
| ¿Cumple los horarios? | `bus.trip.stop` con hora prevista y real (R2, R3) |
| ¿Cuánto retraso acumuló? | Retraso del recorrido y retraso promedio (R5 #3) |
| ¿Se desvió? | Alerta de desvío y desviación media (R5 #5) |
| ¿Cuántos recorridos hizo? | Pestaña Recorridos del tablero (R6) |
| ¿Qué porcentaje se cumplió bien? | Indicador de cumplimiento (R5 #1) |
| ¿Incidencias más frecuentes? | Pestaña Incidencias y Pareto (R6) |
| ¿Qué tan confiable es el sistema? | Calidad del sistema S1 a S4 (R5, R6) y rendimiento (R11) |
| ¿Qué mejoras se hicieron? | Registro de defectos y PDCA (R12), reporte de SonarQube (R10) |

## 6. Riesgos y decisiones abiertas

1. **Horarios reales.** No se tienen los horarios oficiales de la UTA: los de las 4 líneas serán simulados y se marcarán como tales hasta que la universidad confirme los reales.
2. **Power BI** depende de una licencia y de una cuenta que no están en el repositorio (R7). Por eso R6 es la entrega obligatoria.
3. **Traccar Client contra la app propia.** La defensa exige datos de Traccar Client: hace falta un celular real (R9).
4. **Producción.** Los cambios de R1, R2, R3 y R8 modifican el modelo de datos de la base que corre en Azure: respaldo antes y migración probada sobre una copia.
5. **Plazos.** R1 a R6 son el camino crítico; R8 a R10 se pueden hacer en paralelo para reducir el riesgo.

## 7. Definición de terminado de una fase

- Pruebas nuevas y las existentes en verde (Odoo, tableta y linters), y migración probada.
- Documentación y evidencia de la fase generadas desde datos reales o simulados identificados.
- Commits pequeños en su rama, integración a `develop` con `--no-ff`, y `PLAN.md` actualizado.
- La fila correspondiente de la sección 1 pasa a **[HECHO]** solo con la evidencia a la vista.
