# Roadmap del proyecto

Vista única de todo lo que se hizo y de lo que falta, en orden. El detalle de cada etapa está en su plan; la historia día a día en [`../academico/BITACORA.md`](../academico/BITACORA.md). Actualizado el 2026-11-18.

Estado: versión del módulo `16.0.1.9.0`, app de tableta `1.2.0`, última etiqueta `v1.0.0-rc1`. Fases 38 a 45 de la segunda auditoría integradas en `develop`. **No apto todavía para producción general**: falta la fase 46, las pruebas reales.

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
| Correcciones de la segunda auditoría | 17-nov | 38 a 45 | Portal sin XSS, colas de la tableta seguras, despliegue sobre Supabase, acceso al panel, turnos y alertas, servidor y GPS de la tableta, permisos de choferes, carga y purga, build; DEF-051 a DEF-062 cerrados | [`PLAN-AUDITORIA-2.md`](PLAN-AUDITORIA-2.md) |

Cifras al cierre de la etapa de la rúbrica (5-nov): 544 pruebas de Odoo, 167 de Jest, 96 % de cobertura de Python según `odoo_test.log`, SonarQube con el Quality Gate aprobado, 50 defectos registrados y cerrados.

Cifras tras la fase 45 (17-nov): 579 pruebas de Odoo, 179 de Jest, 97 % de cobertura de Python (medida ahora en el CI), 62 defectos registrados y cerrados.

Cifras al 18-nov: 555 pruebas de Odoo (bajan al retirar las de Grafana), 186 de Jest, 75 defectos registrados y cerrados.

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
- **Producción** (`v1.0.0`): fase 46 superada, es decir una jornada real sin defectos críticos y respaldos fuera del servidor.

Decisiones ya tomadas: base de producción en **Supabase** (17-nov), que amplía la fase 39 con soporte de base externa en los scripts.

## 3. Pendientes que no son código

- Confirmar con la universidad los días de cada recorrido, las coordenadas de los campus y las anomalías del documento de rutas.
- Revisión del kichwa por una persona hablante.
- Pruebas de usabilidad con personas (fase 31).
- Confirmar con el docente que los reportes de Odoo sirven en lugar de Power BI (Grafana se retiró el 17-nov).
- Dominio institucional, correo real y suscripción de Azure definitiva.
