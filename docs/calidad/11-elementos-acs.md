# Elementos del ACS: qué existe, cómo se evidencia y qué mejorar

Formato de los anexos del Taller de la Unidad 2, aplicado a este proyecto. Estado a la evaluación del 28-oct-2026.

## 1. Elementos del ACS

| Elemento | ¿Existe? | ¿Cómo se evidencia? | Mejora |
|---|---|---|---|
| **Políticas** | Sí | Siete reglas en `01-politica-y-alcance.md`: despliegue con pruebas al 100 %, validación en modelo o controlador, integridad transaccional, prioridad de defectos, regresiones, privacidad por diseño y trazabilidad | Checklist de revisión por pares antes de fusionar; hoy la regla 1 y la 2 no se cumplen del todo (DEF-008 a DEF-010) |
| **Estándares** | Sí | Reglas de negocio R1 a R16, semántica de códigos HTTP, convenciones de Git y de código en `02-estandares-y-reglas.md`; ISO 25010, 12207, CMMI y 29119-3 en `09-cumplimiento-iso.md` | Configurar flake8, pylint-odoo y SonarQube; documentar las rutas HTTP con OpenAPI |
| **Procesos** | Sí | Flujo de cuatro pasos (implementar, probar, retroalimentar, aprobar), flujo Git y `sh qa/ejecutar_todo.sh` | Automatizar el paso de pruebas con integración continua en lugar de ejecutarlo a mano |
| **Roles** | Parcial | RACI propuesto (desarrollador, tester y QA, cliente) en `01-politica-y-alcance.md` | Confirmar los roles con el equipo y nombrar a una persona de QA distinta de quien desarrolla |
| **Pruebas** | Sí | 150 pruebas de Odoo, 42 casos en vivo, auditoría de 1000 peticiones, 16 mutaciones manuales y cobertura de 93,8 % (`03-plan-y-casos-de-prueba.md`) | Pruebas de interfaz extremo a extremo (Playwright), pruebas de carga con varios procesos y pruebas de usabilidad con pasajeros |
| **Métricas** | Sí | Cuadro de mando con 12 metas (`04-resultados-y-metricas.md`): error, 5xx, tiempo, p95, capacidad, cobertura, defectos cerrados y datos inválidos | Guardar las métricas de cada versión para tener línea base y límites de control |
| **Evidencias** | Sí | `evidencias/` con logs y JSON, `figuras/`, informe en PDF y registro de defectos (`10-evidencias-y-reproduccion.md`) | Publicar y archivar los reportes de análisis estático cuando existan |
| **Análisis de causas** | Sí | Pareto (3 series) e Ishikawa (2 diagramas) en `07-pareto.md` y `08-ishikawa.md` | Repetirlo con cada versión y vincular cada causa a una acción con responsable |
| **Lluvia de ideas** | Sí | 94 ideas categorizadas en `06-lluvia-de-ideas.md` | Hacer una sesión real con la universidad y registrar el acta |

## 2. Tareas del ACS y su evidencia en el sistema

| Tarea ACS | Evidencia en el sistema |
|---|---|
| Validación de datos | `@api.constrains` y restricciones SQL (posición única, alerta abierta única, descripción de 2000 caracteres); validación de formato de correo y teléfono en el formulario. **Falta** la validación de rango de la posición. |
| Control de errores | Códigos HTTP 400, 403, 404, 405, 413 y 429 con mensajes en el idioma de la persona; el webhook ignora lo que no entiende (200) para no provocar reintentos. **Falta** responder 400 en vez de 500 ante datos mal formados. |
| Pruebas | 150 pruebas de Odoo, 42 casos en vivo y auditoría de 1000 peticiones. |
| Monitoreo | `/bus_tracking/health` (503 si no llegan posiciones), healthchecks de Postgres, Odoo y Traccar; registro de tiempos en las evidencias. **Falta** conectar un servicio externo que avise. |
| Integridad transaccional | Prueba P6 (1 guardada de 20 envíos iguales) y P7 (60 de 60 de un mismo bus), sin errores; restricciones únicas de la base. |
| Trazabilidad | Registro de defectos DEF-001 a DEF-010 con causa raíz, bitácora cronológica y Git con commits pequeños. |
| Medición de rendimiento | Media, desviación, p95 y máximo por escenario (P1 a P7) y por área de la auditoría. |
| Análisis estático | **No hay.** Es el faltante principal respecto al taller de referencia. |

## 3. ¿El sistema es de calidad?

**Condicionado.** En uso normal responde bien (0,037 s en promedio en la auditoría), sus funciones principales funcionan, los datos son coherentes, las pruebas cubren el 93,8 % del código y la privacidad está cuidada por diseño. Pero tiene tres defectos abiertos en la validación de la posición que llega por el webhook (DEF-008 a DEF-010), y casi todo se probó con un GPS simulado. Es apto para un **piloto controlado** con el personal de la universidad; la producción abierta espera a que se cierren esos defectos y se pruebe con un celular real.

## 4. ¿Qué elemento del ACS sigue faltando?

1. **Análisis estático** con SonarQube, flake8 y pylint-odoo.
2. **Integración continua** que ejecute pruebas, cobertura y análisis en cada cambio.
3. **Verificación independiente**: una persona de QA distinta de quien desarrolla, y revisiones de código con acta.
4. **Gestión de la configuración formal**: versionado semántico, notas de versión y migraciones controladas de la base de datos.
5. **Validación con personas usuarias** (pasajeros y choferes) y con un celular real.

## 5. ¿Qué mejorarían a futuro?

Por orden de prioridad:

1. Cerrar DEF-008 a DEF-010 y portar E7, E8 y E9 a la suite de Odoo.
2. Probar un turno completo con celular y Traccar reales.
3. Repetir la prueba de carga con varios procesos y con el volumen estimado de 30 días.
4. Configurar el análisis estático y la integración continua.
5. Mover los límites de uso a un almacén común o al proxy; agregar límite de login y 2FA.
6. Pruebas de interfaz extremo a extremo y pruebas de usabilidad.
7. Monitoreo con alertas en producción (Azure Monitor sobre `/bus_tracking/health`) y copia de los respaldos fuera del servidor.
8. Revisión del kichwa por una persona hablante y revisión legal del aviso de privacidad.
