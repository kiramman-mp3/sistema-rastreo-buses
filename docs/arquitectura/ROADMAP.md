# Roadmap del proyecto

Vista única de todo lo que se hizo y de lo que falta, en orden. El detalle de cada etapa está en su plan; la historia día a día en [`../academico/BITACORA.md`](../academico/BITACORA.md). Actualizado el 2026-11-21.

Estado: versión del módulo `16.0.1.11.0` en `main` y `develop` (multas como reales), app de tableta `1.4.1`, última etiqueta y release `v1.0.0` (21-nov-2026). La demostración está desplegada en un homelab con despliegue continuo desde `main` ([`../guias/DESPLIEGUE-HOMELAB.md`](../guias/DESPLIEGUE-HOMELAB.md)). Fases 38 a 45 de la segunda auditoría integradas. **No apto todavía para producción general**: falta la fase 46, las pruebas reales. El nombre `v1.0.0` se dio a la release de la demostración por decisión del usuario; no significa que la fase 46 esté superada.

## 1. Lo hecho

| Etapa | Fechas | Fases | Resultado | Plan |
|---|---|---|---|---|
| Construcción inicial | 26-oct | 0 a 8 | Odoo 16 + Traccar con Docker, modelos de buses, rutas y paradas, webhook y cron de Traccar, mapa en vivo, alertas, reporte diario, pruebas y despliegue con Caddy | [`PLAN.md`](PLAN.md) |
| Celulares, portal y avisos | 26-oct | 9 a 13 | Teléfonos como GPS (OsmAnd), portal público de pasajeros, quejas, correo y push, español, inglés y kichwa (borrador) | [`PLAN.md`](PLAN.md) |
| Recorridos de la UTA | 26 y 27-oct | 15 (parcial) | Recorridos oficiales, trazados por calle, puntualidad, simplificación del sistema | [`PLAN.md`](PLAN.md) |
| Calidad | 28-oct | — | Informe de calidad en PDF, carpeta `docs/calidad`, pipeline `qa/ejecutar_todo.sh`, guion de defensa; DEF-008 a DEF-010 | [`../calidad/README.md`](../calidad/README.md) |
| App del chofer | 30-oct | 16 a 22 | Autenticación de choferes, API de turnos e incidentes, app Expo con GPS en segundo plano y cola sin red | [`PLAN-APP-CHOFER.md`](PLAN-APP-CHOFER.md) |
| Rediseño de producto | 1 y 2-nov | 23 a 31 | Las fases 23 a 25 se reemplazaron por 26 a 31: verdad en los datos, sistema de diseño, portal, panel y cabina nuevos | [`PLAN-UX.md`](PLAN-UX.md) |
| Primera auditoría | 2-nov | Auditoría 1 a 9 | 58 hallazgos cerrados (seguridad de credenciales, choferes como usuarios de portal, turnos, cola GPS, CI completo); DEF-011 a DEF-026 | [`PLAN-AUDITORIA.md`](PLAN-AUDITORIA.md) |
| App adaptable | 2-nov | 32 a 37 | Diseño móvil y de tableta, accesibilidad, respuesta táctil; DEF-027 a DEF-034 | [`PLAN-UI-MOVIL.md`](PLAN-UI-MOVIL.md) |
| Endurecimiento previo a la preview | 3-nov | — | Dependencias, observabilidad, privacidad (LOPDP) y operación; etiqueta `v0.9-preview` | [`../academico/BITACORA.md`](../academico/BITACORA.md) |
| GPS en vivo e iOS | 4-nov | — | Reenvío de Traccar corregido, latido para iOS; DEF-035 a DEF-038; etiqueta `v0.9.5-beta` | [`../academico/BITACORA.md`](../academico/BITACORA.md) |
| Proyecto final (rúbrica) | 4 y 5-nov | R1 a R12 | Horarios y recorridos, reglas, simulador, 12 indicadores, tablero, Grafana, Fleet, SonarQube, pruebas de rendimiento, requisitos y trazabilidad; DEF-039 a DEF-048 | [`PLAN-RUBRICA.md`](PLAN-RUBRICA.md) |
| Integración con Fleet | 5-nov | — | Vehículos de Flota como única ficha del bus, pestaña de rastreo; DEF-049 y DEF-050 | [`FLEET.md`](FLEET.md) |
| Licencia | 12-nov | — | LGPL-3.0 | `LICENSE` |
| Segunda auditoría | 17-nov | — | 7 críticos, 14 medios, 7 de robustez y rendimiento y 15 menores; DEF-051 a DEF-062 | [`PLAN-AUDITORIA-2.md`](PLAN-AUDITORIA-2.md) |
| Pedidos del usuario tras la auditoría | 17 y 18-nov | — | Estado Resuelta en mensajes, gráficos sin repetir animación, Grafana retirado, reportes propios con PDF, menús Reportes y Notificaciones, flota en tablero, Conversaciones oculto, push del administrador en Windows, recordatorios de recorridos en la tableta; DEF-064 a DEF-075 | [`../academico/BITACORA.md`](../academico/BITACORA.md) |
| Control de multas | 20-nov | M1 a M6 | Tipos de multa parametrizables, detector que propone multas desde las alertas con evidencia congelada y comprobaciones, kanban de revisión con descarte y descargo, ficha con mapa y gráfico de velocidad, pantalla *Mis multas* con descargo en la tableta, pestaña del tablero y sección del PDF, escenarios del simulador; DEF-081 a DEF-084 | [`PLAN-MULTAS.md`](PLAN-MULTAS.md) |
| Multas como reales y cierre previo a `main` | 21-nov | MR1 a MR6 | Se retira el modo demostración de las multas (sin `demo` en la API, sin aviso en la ficha ni en la tableta, sin la casilla `fines_real`), migración 16.0.1.11.0, tableta 1.4.1, versiones alineadas, costo del detector y de la migración medidos; DEF-087 a DEF-089 | [`PLAN-MULTAS-REALES.md`](PLAN-MULTAS-REALES.md) |
| Release, despliegue en el homelab y datos de demostración | 21-nov | — | Compilación del APK y el IPA 1.4.1 con EAS, release `v1.0.0`, CI en verde; la demostración pasa de la VM de Azure a un homelab (túnel de Cloudflare, Postgres 17, despliegue continuo desde `main` con vuelta atrás); `scripts/demo_reportes.py` agrega 21 días de viajes simulados, multas y quejas para mostrar los reportes (local y homelab); corrección del error de zoom al salir del mapa en vivo (DEF-090) | [`../guias/DESPLIEGUE-HOMELAB.md`](../guias/DESPLIEGUE-HOMELAB.md) |
| Correcciones de la segunda auditoría | 17-nov | 38 a 45 | Portal sin XSS, colas de la tableta seguras, despliegue sobre Supabase, acceso al panel, turnos y alertas, servidor y GPS de la tableta, permisos de choferes, carga y purga, build; DEF-051 a DEF-062 cerrados | [`PLAN-AUDITORIA-2.md`](PLAN-AUDITORIA-2.md) |

Cifras al cierre de la etapa de la rúbrica (5-nov): 544 pruebas de Odoo, 167 de Jest, 96 % de cobertura de Python según `odoo_test.log`, SonarQube con el Quality Gate aprobado, 50 defectos registrados y cerrados.

Cifras tras la fase 45 (17-nov): 579 pruebas de Odoo, 179 de Jest, 97 % de cobertura de Python (medida ahora en el CI), 62 defectos registrados y cerrados.

Cifras al 18-nov: 555 pruebas de Odoo (bajan al retirar las de Grafana), 186 de Jest, 75 defectos registrados y cerrados.

Cifras al 21-nov (`develop`): 626 pruebas de Odoo (comando del CI, 0 fallos), 197 de Jest, flake8, lint y typecheck sin avisos; DEF-087 a DEF-089 cerrados. Con DEF-090 (zoom del mapa), 90 defectos registrados y 89 cerrados; el abierto es DEF-079.

Cifras al 20-nov (control de multas, tras reinstalar el entorno de desarrollo desde cero): 625 pruebas de Odoo, todas pasan (DEF-084 cerrado). 197 pruebas de Jest. 86 defectos registrados, 85 cerrados (abierto: DEF-079).

## 2. Lo que falta

Fases de [`PLAN-AUDITORIA-2.md`](PLAN-AUDITORIA-2.md). Tamaño: S (horas), M (un día), L (varios días).

| Orden | Fase | Rama | Corrige | Tamaño | Estado |
|---|---|---|---|---|---|
| 1 | 38 | `fix/xss-y-cola-sos` | X1, W1, W3 | S | Hecha |
| 2 | 39 | `fix/despliegue-produccion` | B1, B2, B4, X4, X6, S5 | M | Hecha |
| 3 | 40 | `fix/acceso-panel` | B3, S3, O1 | S | Hecha |
| 4 | 41 | `fix/turnos-y-alertas` | N1, X2, W2, N2, N3, N4, Y4 | M | Hecha |
| 5 | 42 | `fix/tableta-servidor-y-gps` | Y1, Y2, Y3, X3, Y5 | S | Hecha |
| 6 | 43 | `fix/permisos-choferes` | Z1, Z2, X5, S1, S2 | M | Hecha |
| 7 | 44 | `perf/carga-y-purga` | N5, N6, N7, X7, P1, W4 | M | Hecha (W4 documentado) |
| 8 | 45 | `chore/build-y-dependencias` | D1, D2, O3 | S | Hecha (quedan 3 avisos de build) |
| 9 | 46 | Pruebas reales y salida | B5 | L | **Pendiente**: necesita Supabase, VM Linux y tabletas |
| 10 | 47 | `docs/cierre-auditoria-2` | Documentación | S | Hecha |

Hitos:

- **Piloto vigilado** (`v0.9.6-beta`): fases 38, 39 y 40 integradas. Pocos buses, con alguien mirando el panel.
- **Candidata** (`v1.0.0-rc1`): fases 41 a 45 integradas y suite completa en verde. **Alcanzado el 18-nov-2026**: etiqueta en `main`, release en GitHub con el APK y el IPA 1.2.0, y la VM de Azure actualizada.
- **Producción**: fase 46 superada, es decir una jornada real sin defectos críticos y respaldos fuera del servidor. La etiqueta `v1.0.0` ya se usó el 21-nov-2026 para la release de la demostración (módulo 16.0.1.11.0, tableta 1.4.1), así que la salida a producción real necesitará otro número de versión.

Decisiones ya tomadas: base de producción en **Supabase** (17-nov), que amplía la fase 39 con soporte de base externa en los scripts.

### Control de multas

Detalle en [`PLAN-MULTAS.md`](PLAN-MULTAS.md) y, para el retiro del modo demostración, en [`PLAN-MULTAS-REALES.md`](PLAN-MULTAS-REALES.md). Decisiones del usuario (20-nov): columna *Apelada* y descargo desde la tableta, montos en dólares de ejemplo, multas también de los recorridos simulados, límite de 50 km/h con tolerancia hasta 70 km/h.

| Fase | Rama | Contenido | Estado |
|---|---|---|---|
| M1 | `feature/multas-modelo` | Tipos y multas, estados, permisos, ajustes, migración 16.0.1.10.0 | Hecha |
| M2 | `feature/multas-deteccion` | Detector, evidencia, comprobaciones, cron, parada larga al reanudar, simulador | Hecha |
| M3 | `feature/multas-panel` | Kanban, ficha con mapa y gráfico, menús, descarte con motivo | Hecha |
| M4 | `feature/multas-tableta` | API del chofer y pantalla *Mis multas* con descargo (app 1.4.0) | Hecha |
| M5 | `feature/multas-reportes` | Pestaña *Multas* del tablero y sección del PDF | Hecha |
| — | `chore/traducir-multas` | Español y kichwa de las multas y de textos que faltaban | Hecha |
| M6 | `docs/multas` | Documentación | Hecha |
| MR0 | — | Entorno y línea base (625/625 en Odoo, 197 en Jest) | Hecha |
| MR1 | `fix/version-tableta` | `package.json` igual a `app.json` (DEF-087) | Hecha |
| MR2 | `feature/multas-como-reales` | Sin modo demostración: API, ficha, tableta, Ajustes, migración 16.0.1.11.0 y tableta 1.4.1 (DEF-089) | Hecha |
| MR3 | — | Rendimiento del detector: 0,84 ms por disparo (p95 1,2 ms), sin cambios de código | Hecha (medido) |
| MR4 | — | Migración 16.0.1.10.0: 500.000 filas en 1,16 s y repetible, sin cambios de código | Hecha (medida) |
| MR5 | `docs/multas-reales` | Documentación, versiones (DEF-088) y defectos | Hecha |
| MR6 | — | Verificaciones finales, paso a `main`, CI en verde y release `v1.0.0` con el APK y el IPA 1.4.1 | Hecha |

Hito **Multas demostrables**: alcanzado el 20-nov-2026 en `develop` (sin etiqueta ni despliegue todavía). Hito **Multas como reales**: alcanzado el 21-nov-2026 en `develop`.

## 3. Pendientes que no son código

- Confirmar con la universidad los días de cada recorrido, las coordenadas de los campus y las anomalías del documento de rutas.
- Revisión del kichwa por una persona hablante (también el vocabulario de las multas).
- Multas en una empresa real (fuera del alcance de esta demostración): que se incluyan en el reglamento interno aprobado por el Ministerio del Trabajo, con montos y plazo de conservación fijados por la empresa.
- Pruebas de usabilidad con personas (fase 31).
- Confirmar con el docente que los reportes de Odoo sirven en lugar de Power BI (Grafana se retiró el 17-nov).
- Dominio institucional y correo real (el dominio actual, `madebyjohan.xyz`, es personal).
- Respaldo automático y copia fuera del equipo en el homelab: hoy solo hay volcados manuales en `~/backups/` (ver [`../guias/DESPLIEGUE-HOMELAB.md`](../guias/DESPLIEGUE-HOMELAB.md)).
- Cambiar la contraseña de los choferes de demostración (`chofer1` a `chofer4`) o desactivarlos si el sitio sigue público.
