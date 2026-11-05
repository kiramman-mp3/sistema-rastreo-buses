# Mejora continua: Ishikawa, Pareto y PDCA de la etapa de la rúbrica

Evidencia de la Actividad 10 del proyecto final y del entregable 10 («Informe de mejora continua»). El registro completo de defectos está en `05-registro-de-defectos.md` (DEF-001 a DEF-048) y los diagramas de las etapas anteriores en
`07-pareto.md` y `08-ishikawa.md`. Aquí se analiza **lo que apareció al construir los recorridos, las reglas, las métricas, los tableros, Fleet y SonarQube** (4 y 5 de noviembre de 2026), con un ciclo PDCA por cada problema relevante y su
comparación antes y después.

## 1. Los problemas de la etapa

Diez defectos (DEF-039 a DEF-048), todos cerrados, cada uno con la prueba que lo protege:

| ID | Problema | Cómo apareció | Categoría |
|---|---|---|---|
| DEF-039 | El segundo escenario simulado de un bus no producía recorrido | Pruebas del simulador | Lógica |
| DEF-040 | La desviación promedio (T5) salía vacía con recorridos exactos | Pruebas de las métricas | Lógica |
| DEF-041 | Un indicador no veía el recorrido recién creado | Pruebas de las métricas | Lógica |
| DEF-042 | El registro de rechazos se caía con cargas raras | Pruebas de calidad | Validación de entrada |
| DEF-043 | El tablero se quedaba en «Cargando…» | **Navegador** (Playwright) | Lógica |
| DEF-044 | Las tarjetas del tablero salían apiladas | **Navegador** (Playwright) | Accesibilidad y diseño |
| DEF-045 | El módulo no se instalaba por el orden de las vistas SQL | Pruebas | Configuración |
| DEF-046 | Grafana se quedaba sin datos al vencer el token de 5 minutos | **Navegador** y contenedor real | Seguridad |
| DEF-047 | Los gestores no veían los vehículos de Fleet | Pruebas | Seguridad |
| DEF-048 | 16 bugs, un hash débil y código muerto | **SonarQube** | Lógica |

## 2. Ishikawa: por qué aparecieron

Problema: **«lo que se supuso de otra pieza no era cierto»** (cinco de los diez defectos nacen de un supuesto sobre cómo se comporta Odoo, OWL, Grafana o Fleet, y otros dos de nombres u órdenes compartidos que nadie coordinó).

| Rama | Causas |
|---|---|
| **Método** | Se escribió la funcionalidad antes de probar el comportamiento de la plataforma con un caso mínimo; las pruebas unitarias no ejercitan el navegador ni los contenedores reales |
| **Material (datos)** | Un 0,0 nunca escrito queda NULL en Odoo (DEF-040); lo rechazado no tiene forma fija (DEF-042) |
| **Máquina / herramientas** | Las plantillas de OWL no son JavaScript (DEF-043); Grafana con JWT no abre sesión (DEF-046); el grupo «Officer» de Fleet ve solo lo suyo (DEF-047) |
| **Medición** | Sin análisis estático antes de esta etapa: 16 bugs de promesas sin manejar llevaban semanas (DEF-048) |
| **Personas** | Una sola persona escribe y prueba; la lectura del código ajeno (CSS del mapa) no se hizo antes de nombrar clases (DEF-044) |
| **Entorno** | Orden de carga de los modelos de Odoo (DEF-045); el simulador chocaba con una regla propia: las posiciones viejas se ignoran (DEF-039) |

## 3. Pareto: qué priorizar

Por **causa de origen** de los diez defectos:

| Causa de origen | Defectos | % | % acumulado |
|---|---|---|---|
| Supuesto sobre el comportamiento de una plataforma (Odoo, OWL, Grafana, Fleet) | 5 (DEF-040, 041, 043, 046, 047) | 50 | 50 |
| Nombres y orden compartidos sin coordinar (CSS, carga de modelos) | 2 (DEF-044, 045) | 20 | 70 |
| Regla propia no tenida en cuenta en la prueba | 1 (DEF-039) | 10 | 80 |
| Entrada inesperada | 1 (DEF-042) | 10 | 90 |
| Código sin revisión estática | 1 (DEF-048) | 10 | 100 |

**Lectura:** la mitad de los defectos vienen de dar por hecho cómo se comporta una plataforma. **Tres de los diez se hallaron con pruebas en un navegador o contra un contenedor real, no con pruebas unitarias** (DEF-043, 044 y 046) y uno con análisis estático (DEF-048):
lo que se prioriza es probar contra la plataforma de verdad temprano.

## 4. PDCA

### Ciclo 1: análisis estático (DEF-048)

| Fase | Qué se hizo |
|---|---|
| **Planificar** | Problema: no había análisis estático; se sospechaba código con errores latentes. Meta: ningún bug ni vulnerabilidad sin justificar y Quality Gate aprobado |
| **Hacer** | SonarQube Community con cobertura de Python y Jest; se clasificaron 39 hallazgos; se corrigieron 27 (promesas sin manejar, SHA-1, `pytz`, comparación de NaN, regex, `Number.*`) |
| **Verificar** | Segundo y tercer análisis con las pruebas completas en verde |
| **Actuar** | Los 12 restantes son datos de prueba y un servidor simulado: aceptados con su justificación; se dejaron `scripts/sonar-*.sh` para repetir el análisis |

| Medida | Antes | Después |
|---|---|---|
| Bugs | 16 (fiabilidad C) | **0** (A) |
| Vulnerabilidades | 12 (seguridad D) | **0** (A) |
| Malos olores | 11 | **0** |
| Deuda técnica | 107 min | **0** |
| Pruebas | 512 Odoo + 167 Jest | 512 Odoo + 167 Jest (sin regresión) |

### Ciclo 2: acceso a Grafana (DEF-046)

| Fase | Qué se hizo |
|---|---|
| **Planificar** | Problema: el plan decía token de 5 minutos. Hipótesis: Grafana abre una sesión al primer acceso |
| **Hacer** | Se levantó Grafana 11.6 y se probó en un navegador real con un token de 15 s |
| **Verificar** | Antes: con el token vencido, volver a abrir el tablero mostraba el inicio de sesión de Grafana, sin cookie de sesión. Se comprobó que el navegador reenvía el token en cada consulta |
| **Actuar** | Duración configurable (480 min por defecto, 5 a 1440) con renovación al 90 % de su vida; el límite real es el rol de la base (solo vistas sin datos personales). `qa/grafana_smoke.py` lo vigila |

| Medida | Antes | Después |
|---|---|---|
| Tablero con la pantalla abierta pasado el token | Sin datos / inicio de sesión | Sigue funcionando (renovación automática) |
| Comprobaciones de la prueba de humo | — | 19 de 19 |

### Ciclo 3: confiabilidad de la medición de cobertura

| Fase | Qué se hizo |
|---|---|
| **Planificar** | Problema: el primer análisis daba 20,4 % de cobertura aunque las pruebas cubren más de 90 % de los modelos |
| **Hacer** | Se revisó el registro del escáner: ignoraba el informe de Python porque las rutas de archivo no coincidían |
| **Verificar** | `scripts/sonar-coverage.sh` reescribe las rutas; segundo análisis: 78,4 % |
| **Actuar** | La cifra de cobertura se defiende por área (`16-sonarqube.md` §4.1) y se reconoce el 0 % del JavaScript del módulo como siguiente punto de mejora |

| Medida | Antes | Después |
|---|---|---|
| Cobertura global | 20,4 % (mal medida) | **78,4 %** (líneas 75,9 %, ramas 87,1 %) |

### Ciclo 4: rendimiento por volumen (verificación preventiva)

| Fase | Qué se hizo |
|---|---|
| **Planificar** | Riesgo: el tablero suma sobre todos los recorridos del periodo y podría degradarse. Meta: p95 menor que 2 s |
| **Hacer** | `qa/rendimiento_volumen.py`: de 1 000 a 1 000 000 de posiciones y de 100 a 50 000 recorridos |
| **Verificar** | Peor caso: tablero 704 ms con 50 000 recorridos |
| **Actuar** | No se agregaron índices (ya cubren las consultas); se vigila S3 en producción |

## 5. Lo que cambió en el proceso

| Antes de la etapa | Después |
|---|---|
| 38 defectos, 289 pruebas de Odoo, 165 de Jest | **48 defectos (todos cerrados)**, **544 pruebas de Odoo**, **167 de Jest** |
| Sin análisis estático | SonarQube con informe e interpretación |
| Pruebas solo en el servidor | Pruebas también en el navegador y contra contenedores reales (Playwright, `qa/grafana_smoke.py`) |
| Indicadores no definidos formalmente | 12 indicadores con fórmula, consulta y prueba de que los dos tableros coinciden |
| Rendimiento no medido por volumen | Medido hasta 1 000 000 de posiciones |

**Acciones que quedan** (siguiente ciclo): pruebas unitarias del JavaScript del módulo (hoy 0 % de cobertura medida), análisis de dependencias (`npm audit`), una prueba de concurrencia, y la evidencia física con Traccar Client el día de la defensa.
