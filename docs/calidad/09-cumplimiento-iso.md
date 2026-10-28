# Cumplimiento de ISO/IEC 25010, ISO/IEC/IEEE 12207, CMMI e ISO/IEC/IEEE 29119-3

Cómo se cumple (o no) cada estándar, con la evidencia. Es una **autoevaluación del equipo**, no una auditoría ni una certificación. Niveles: **Cumple** (hay evidencia directa), **Parcial** (hay evidencia pero falta algo), **No evaluado** (no se midió) y **No aplica**; en CMMI, **No cumple** es que no hay evidencia. Las cifras son las de la ejecución del 28-oct-2026 (`04-resultados-y-metricas.md`).

## 1. ISO/IEC 25010: calidad del producto

Ocho características y sus subcaracterísticas.

| Característica | Subcaracterística | Nivel | Evidencia |
|---|---|---|---|
| Adecuación funcional | Completitud funcional | Parcial | Las funciones del alcance reducido existen (mapa, recorridos, alertas, push, portal, quejas); el kichwa está en borrador |
| | Corrección funcional | Parcial | 12 de 12 casos funcionales y 150 pruebas de Odoo pasan; DEF-008 a DEF-010 abiertos |
| | Pertinencia funcional | Parcial | Recorridos automáticos y pasajero sin login, como pidió el cliente; sin validar con personas usuarias |
| Eficiencia de desempeño | Comportamiento temporal | Cumple | Media de 0,037 s en la auditoría; 0,043 s en P1; p95 de 1,6 s con 20 hilos |
| | Uso de recursos | No evaluado | No se midió CPU ni memoria |
| | Capacidad | Parcial | 39 req/s con 20 hilos en un proceso (se necesitan 10); falta el volumen de 30 días y varios procesos |
| Compatibilidad | Coexistencia | Parcial | Convive con otros contenedores (`ODOO_PORT` resolvió el conflicto del puerto 8069) |
| | Interoperabilidad | Parcial | Traccar 6 por webhook y REST verificado con GPS simulado; sin celular real |
| Usabilidad | Reconocimiento de la adecuación | Parcial | Landing y portal con textos claros; sin prueba con personas |
| | Capacidad de aprendizaje | Parcial | `docs/GUIA-CHOFER.md`; sin medir |
| | Operabilidad | Parcial | Panel de Odoo y mapa; portal revisado a 390 px |
| | Protección ante errores del usuario | Cumple | U1: 7 de 7 mensajes de rechazo claros, sin SQL ni trazas; el formulario conserva lo escrito |
| | Estética de la interfaz | Parcial | Diseño pulido el 28-oct; fotos provisionales |
| | Accesibilidad | Parcial | Tipografía legible, foco visible, `prefers-reduced-motion`; sin auditoría formal |
| Fiabilidad | Madurez | Parcial | 0 fallos en 150 pruebas; 25 respuestas 500 en la auditoría |
| | Disponibilidad | No evaluado | Hay `/health` y healthchecks; no se midió en un servidor real |
| | Tolerancia a fallos | Parcial | Cron de respaldo del webhook; sobrevive a errores de Traccar (`test_cron_survives_traccar_errors`); falla ante datos mal formados |
| | Capacidad de recuperación | Cumple | Respaldo y restauración (en base paralela y completa) probados |
| Seguridad | Confidencialidad | Parcial | Privacidad por diseño, contacto restringido y borrado a 90 días; sin 2FA ni límite de login |
| | Integridad | Parcial | Restricciones únicas, `@api.constrains` en quejas, P6 y P7 correctos; coordenadas imposibles guardadas (DEF-008) |
| | No repudio | No evaluado | |
| | Responsabilidad (accountability) | No evaluado | Odoo guarda autor y fecha de cada registro; no se evaluó como control |
| | Autenticidad | Parcial | Secreto del webhook en tiempo constante y login de Odoo; el identificador del celular es la única credencial del GPS |
| Mantenibilidad | Modularidad | Cumple | Un modelo y un controlador por responsabilidad |
| | Reusabilidad | Parcial | `RateLimiter`, `TtlCache` y `geo` compartidos entre portal y quejas |
| | Analizabilidad | Parcial | Bitácora y pruebas con nombres descriptivos; sin análisis estático |
| | Modificabilidad | Cumple | Umbrales, marca, mapa y retención se cambian en Ajustes; cobertura de 93,8 % protege los cambios |
| | Capacidad de ser probado | Cumple | 150 + 42 pruebas y la auditoría; los límites en memoria exigen reiniciar para medir |
| Portabilidad | Adaptabilidad | Parcial | Configurable por Ajustes e idiomas por diccionario |
| | Instalabilidad | Cumple | `docker compose up` y `scripts/init-prod.sh`, repetidos desde cero |
| | Capacidad de reemplazo | No evaluado | |

**Resumen:** de 31 subcaracterísticas, 19 parcial, 7 cumple, 5 no evaluado.

## 2. ISO/IEC/IEEE 12207: procesos del ciclo de vida del software

Los 30 procesos de la norma (2017), agrupados como en ella.

| Grupo | Proceso | Nivel | Evidencia |
|---|---|---|---|
| Acuerdo | Adquisición | No aplica | Proyecto propio; el cliente pide, no hay proveedor |
| | Suministro | Parcial | Se entrega a la UTA sin acuerdo formal escrito |
| Habilitación del proyecto | Gestión del modelo de ciclo de vida | Parcial | Fases en `docs/PLAN.md` |
| | Gestión de la infraestructura | Cumple | Docker Compose, proxy Caddy, scripts |
| | Gestión del portafolio | No aplica | Un solo proyecto |
| | Gestión de recursos humanos | Parcial | RACI propuesto en `01-politica-y-alcance.md` |
| | Gestión de la calidad | Parcial | Esta carpeta; sin auditor externo |
| | Gestión del conocimiento | Cumple | `docs/` y bitácora al día |
| Gestión técnica | Planificación del proyecto | Cumple | `docs/PLAN.md` |
| | Evaluación y control del proyecto | Cumple | Bitácora con pendientes y estados |
| | Gestión de decisiones | Cumple | Fase 0 y simplificación documentadas |
| | Gestión de riesgos | Parcial | Riesgos listados; sin plan formal de mitigación |
| | Gestión de la configuración | Cumple | Git con `main`, `develop` y ramas; Conventional Commits |
| | Gestión de la información | Cumple | Documentos versionados |
| | Medición | Cumple | `qa/metricas.py` y `04-resultados-y-metricas.md` |
| | Aseguramiento de la calidad | Parcial | Política y pruebas; sin evaluación independiente |
| Técnicos | Análisis del negocio o la misión | Parcial | Fase 0; sin estudio de uso de pasajeros |
| | Definición de necesidades de los interesados | Parcial | Respuestas del cliente; sin entrevistas a pasajeros ni choferes |
| | Definición de requisitos | Parcial | `docs/PLAN.md`; sin especificación formal ni trazabilidad a pruebas |
| | Definición de la arquitectura | Cumple | Esquema del README y decisiones del plan |
| | Definición del diseño | Cumple | `docs/DISENO.md`, modelos y vistas |
| | Análisis del sistema | Parcial | Volumen estimado de posiciones; capacidad medida solo en un proceso |
| | Implementación | Cumple | Módulo `bus_tracking` |
| | Integración | Cumple | Celular simulado, Traccar, webhook y Odoo probados de punta a punta |
| | Verificación | Cumple | 150 pruebas, 42 casos en vivo, auditoría y cobertura |
| | Transición | Parcial | Producción probada en local; Azure pendiente |
| | Validación | Parcial | Sin celular real ni usuarios reales |
| | Operación | Parcial | `docs/PRODUCCION.md` y `docs/GUIA-CHOFER.md`; sin operación real |
| | Mantenimiento | Parcial | Actualización documentada; sin versionado semántico |
| | Disposición | No aplica | |

**Resumen:** de 30 procesos, 3 no aplica, 14 parcial, 13 cumple.

## 3. CMMI para Desarrollo v1.3: áreas de proceso

Autoevaluación contra las 22 áreas de proceso. **No es una evaluación SCAMPI.**

| Nivel | Área de proceso | Valoración | Evidencia |
|---|---|---|---|
| 2 | REQM, gestión de requisitos | Parcial | Decisiones del cliente en el plan; sin matriz requisito-prueba |
| 2 | PP, planificación del proyecto | Cumple | `docs/PLAN.md` por fases |
| 2 | PMC, seguimiento y control | Cumple | Bitácora con estado y pendientes |
| 2 | MA, medición y análisis | Cumple | `qa/metricas.py` y cuadro de mando |
| 2 | PPQA, aseguramiento de la calidad del proceso y del producto | Parcial | Política y pruebas; sin evaluación objetiva independiente |
| 2 | CM, gestión de la configuración | Cumple | Git flow y versionado de documentos |
| 2 | SAM, gestión de acuerdos con proveedores | No aplica | Odoo y Traccar son de código abierto, sin proveedor contratado |
| 3 | RD, desarrollo de requisitos | Parcial | Sin especificación formal |
| 3 | TS, solución técnica | Cumple | Diseño y arquitectura documentados |
| 3 | PI, integración del producto | Cumple | Integración Traccar, Odoo y proxy probada |
| 3 | VER, verificación | Cumple | Pruebas y cobertura |
| 3 | VAL, validación | Parcial | Sin usuarios reales |
| 3 | OPF, enfoque en el proceso de la organización | No cumple | |
| 3 | OPD, definición del proceso | Parcial | `CLAUDE.md` define el flujo Git; no hay proceso de calidad estándar |
| 3 | OT, formación | No cumple | |
| 3 | IPM, gestión integrada del proyecto | Parcial | |
| 3 | RSKM, gestión de riesgos | Parcial | Riesgos listados sin plan de mitigación |
| 3 | DAR, análisis de decisiones y resolución | Parcial | Decisiones registradas sin método formal |
| 4 | OPP, desempeño del proceso | Parcial | Primera línea base de métricas (28-oct); sin histórico |
| 4 | QPM, gestión cuantitativa | No cumple | |
| 5 | OID, innovación y despliegue | No cumple | |
| 5 | CAR, análisis causal y resolución | Parcial | Pareto e Ishikawa de esta carpeta |

**Nivel resultante: 2 en consolidación.** De las seis áreas del nivel 2 que aplican, cuatro se cumplen (PP, PMC, MA, CM) y dos son parciales (REQM y PPQA). Para cerrar el nivel 2 hacen falta una matriz que una cada requisito con sus pruebas y una evaluación de calidad hecha por una persona distinta de quien desarrolla. El nivel 3 y superiores no se alcanzan: no hay proceso estándar de calidad ni gestión cuantitativa.

## 4. ISO/IEC/IEEE 29119-3: documentación de pruebas

| Documento de la norma | Dónde está |
|---|---|
| Plan de pruebas | `03-plan-y-casos-de-prueba.md`, secciones 1 y 2 |
| Especificación del diseño de pruebas | `03-plan-y-casos-de-prueba.md` |
| Especificación de casos de prueba | `03-plan-y-casos-de-prueba.md`, secciones 3 a 5 |
| Procedimiento de pruebas | `10-evidencias-y-reproduccion.md` |
| Requisitos de datos de prueba | `qa/common.py` (función `prepare`), `qa/auditoria.py` (semilla fija) |
| Requisitos del entorno de pruebas | `10-evidencias-y-reproduccion.md` |
| Registro de ejecución | `evidencias/suite.log`, `evidencias/odoo_test.log`, `evidencias/auditoria.log` |
| Informe de incidencias | `05-registro-de-defectos.md` |
| Informe de estado y cierre | `04-resultados-y-metricas.md` y `Informe_calidad_rastreo_buses.pdf` |

## 5. Qué hace falta para subir de nivel

1. Cerrar DEF-008 a DEF-010 y portar sus pruebas (Eficiencia, Fiabilidad, Integridad).
2. Medir uso de CPU y memoria, y repetir la carga con varios procesos (Eficiencia).
3. Probar un celular y un Traccar reales y hacer pruebas de usabilidad con pasajeros (Validación, Usabilidad, Compatibilidad).
4. Configurar flake8, pylint-odoo y SonarQube (Analizabilidad).
5. Escribir una matriz requisito-prueba y nombrar a una persona de QA independiente (REQM y PPQA de CMMI).
6. Plan de mitigación de riesgos (RSKM) y versionado semántico con notas de versión (Mantenimiento).
