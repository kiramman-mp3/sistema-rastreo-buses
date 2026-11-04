# Política de calidad, alcance y responsabilidades

Adaptado del Taller de la Unidad 2 (política de calidad, matriz RACI, flujo de aseguramiento). Aquí se aplica al sistema de rastreo de buses de la UTA (Odoo 16 y Traccar).

## 1. Propósito

Asegurar que cada cambio en el sistema reciba, guarde y muestre bien la posición de los buses, proteja los datos de las personas (pasajeros y choferes) y no deje datos imposibles en la base. Se logra con tres medios: pruebas automatizadas, revisión continua y métricas verificables (ver `04-resultados-y-metricas.md`).

## 2. Alcance

La política aplica a todo `addons/bus_tracking` y a lo que lo hace funcionar:

| Componente | Dónde está |
|---|---|
| Modelos (lógica de negocio y datos) | `models/` (`bus.vehicle`, `bus.route`, `bus.position`, `bus.run`, `bus.alert`, `bus.complaint`, `bus.push.subscription`, …) |
| Controladores (HTTP y JSON-RPC) | `controllers/` |
| Vistas y menús | `views/` |
| Seguridad | `security/ir.model.access.csv` y `security/security.xml` (grupos User y Manager) |
| Datos y tareas programadas | `data/ir_cron.xml`, `data/sequences.xml` |
| Interfaz (mapa, portal, push) | `static/src/` |
| Traducciones | `i18n/` |
| Infraestructura | `docker-compose*.yml`, `docker/`, `proxy/Caddyfile`, `scripts/` |
| App de tableta | `apps/conductor-tablet/` (login, turnos, GPS OsmAnd, incidentes) |

Rutas HTTP que se validan: las del portal y el webhook, más `/bus_tracking/driver/login`, `/logout`, `/me`, `/shift/start`, `/shift/end`, `/state`, `/route` e `/incident` (suite en vivo F13–F14, E23–E25 y tests de Odoo).

Fuera de alcance: Odoo y Traccar (terceros); Expo y el sistema operativo de la tableta; el contenido legal del aviso de privacidad (lo revisa la universidad). La app de chofer *sí* está en alcance: es código de este repositorio.

## 3. Política de calidad

Siete reglas obligatorias. La columna "Estado hoy" dice si se cumplen en la versión evaluada el 28-oct-2026.

| N.º | Regla | Cómo se verifica | Estado hoy |
|---|---|---|---|
| 1 | **Criterio de despliegue.** Nada se integra a `main` si las pruebas de Odoo no pasan al 100 % y la suite en vivo (`qa/qa_suite.py`) tiene respuestas 5xx. | `docker compose run … --test-enable` y `sh qa/ejecutar_todo.sh` | Pruebas de Odoo: 150 de 150. Suite en vivo: 3 fallos (DEF-008 a DEF-010). **No se cumple del todo.** |
| 2 | **Validación en el modelo o el controlador, nunca solo en la vista.** Todo dato externo se valida donde entra (webhook, formulario público, JSON-RPC), con `@api.constrains`, restricciones SQL o validación explícita. | Casos E (error) y auditoría aleatoria | Cumplida en quejas, portal y permisos. **No cumplida en la posición del webhook** (DEF-008 a DEF-010). |
| 3 | **Integridad de las transacciones.** Una petición que falla no deja datos a medias: se deja que la excepción salga del controlador para que Odoo revierta la transacción, y no se captura una excepción del ORM sin relanzarla. | P6 (20 envíos iguales a la vez: 1 guardado) y P7 (60 de 60 de un mismo bus) | Cumplida. |
| 4 | **Prioridad de defectos.** Un defecto hallado por las pruebas bloquea las funciones nuevas hasta corregirse. | `05-registro-de-defectos.md` | Aplica desde esta evaluación: DEF-008 a DEF-010 van primero. |
| 5 | **Prevención de regresiones.** Todo defecto corregido deja una prueba nueva en la suite de Odoo. | Prueba citada en cada defecto | Cumplida en DEF-001 a DEF-007; pendiente portar E7, E8 y E9. |
| 6 | **Privacidad por diseño.** El pasajero solo ve nombre, posición, rumbo y estado del bus (nunca placa, conductor, velocidad exacta ni historial); el contacto de una queja solo lo ven los administradores y se borra a los 90 días de resuelta; el identificador del GPS del celular solo lo ven los administradores. | F9, tests de portal y de quejas | Cumplida. Falta el consentimiento escrito de los choferes y la revisión legal. |
| 7 | **Trazabilidad.** Flujo Git (`main`, `develop`, `feature/*`, `fix/*`), commits pequeños con Conventional Commits, y cada trabajo registrado en `docs/academico/BITACORA.md` y `docs/arquitectura/PLAN.md`. | Historial de Git y bitácora | Cumplida. |

## 4. Matriz de roles y responsabilidades (RACI)

**Propuesta a confirmar por el equipo.** Los roles se tomaron del Taller de la Unidad 2 (Johan Rodríguez, desarrollador; José Manzano, tester y QA). La universidad figura como cliente. R = responsable, A = aprueba, C = consultado, I = informado.

| Actividad | Desarrollador | Tester / QA | Cliente (UTA) |
|---|---|---|---|
| Implementar y corregir código | R, A | I | I |
| Diseñar y mantener casos de prueba | C | R, A | I |
| Ejecutar la suite de pruebas | I | R, A | I |
| Registrar defectos encontrados | C | R, A | I |
| Corregir defectos | R | A | I |
| Aprobar el despliegue | C | R, A | A (piloto) |
| Definir alcance, nombre, textos legales y variante de kichwa | C | I | R, A |
| Mantener esta política | R | A | I |

Nota: Claude Code ayuda al desarrollador a escribir y probar código, pero no aprueba despliegues ni sustituye al QA independiente (ver "Qué falta" en `11-elementos-acs.md`).

## 5. Flujo del proceso de aseguramiento

1. **Implementación y reinicio.** El desarrollador cambia el código en una rama `feature/*` o `fix/*` y reinicia el servicio: `docker compose restart odoo` (o actualiza el módulo con `-u bus_tracking`).
2. **Ejecución de pruebas.** El QA corre `sh qa/ejecutar_todo.sh` (suite en vivo, auditoría y métricas) y las pruebas de Odoo con cobertura (ver `10-evidencias-y-reproduccion.md`).
3. **Retroalimentación.** Si algo falla, el QA registra el defecto con fallo observado, defecto localizado y causa de origen en `05-registro-de-defectos.md`; el desarrollador lo corrige y se vuelve al paso 2.
4. **Aprobación.** Solo con las pruebas de Odoo al 100 %, la suite en vivo sin 5xx, ningún registro inválido y las evidencias archivadas, el QA aprueba la integración a `develop`; `develop` pasa a `main` cuando está estable y probado.

## 6. Criterio de aprobación final

Se aprueba un despliegue a producción abierta solo si se cumplen todas las metas del cuadro de mando (sección 1 de `04-resultados-y-metricas.md`) y, además, se probó un turno completo con un celular y un Traccar reales. Hoy se aprueba únicamente un **piloto controlado** con el personal de la universidad.
