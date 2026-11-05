# Documentación de calidad y pruebas

Aquí vive todo lo que se documenta sobre la calidad del sistema de rastreo de buses: política, reglas, pruebas, resultados, defectos, análisis de causas, cumplimiento de las ISO y evidencias. Se basa en el Taller de la Unidad 2 (`Taller ACS`) y en el informe de la Unidad 3 (`Manzano_Rodriguez_trabajoFinalU3`).

Regla del proyecto: **cada vez que se pruebe, se mida o se corrija algo relacionado con la calidad, se actualiza esta carpeta** (además de `docs/academico/BITACORA.md` y `docs/arquitectura/PLAN.md`).

## Índice

| Documento | Contenido |
|---|---|
| [01-politica-y-alcance.md](01-politica-y-alcance.md) | Propósito, alcance, siete reglas de calidad, matriz RACI, flujo de aseguramiento y criterio de aprobación |
| [02-estandares-y-reglas.md](02-estandares-y-reglas.md) | Reglas de negocio R1 a R16, semántica de las respuestas HTTP, convenciones y análisis estático |
| [03-plan-y-casos-de-prueba.md](03-plan-y-casos-de-prueba.md) | Estrategia, criterios de aceptación y todos los casos de prueba *(generado)* |
| [04-resultados-y-metricas.md](04-resultados-y-metricas.md) | Cuadro de mando, tiempos, cobertura y estado de los datos *(generado)* |
| [05-registro-de-defectos.md](05-registro-de-defectos.md) | Defectos DEF-001 a DEF-048 con causa raíz y estado *(generado)* |
| [06-lluvia-de-ideas.md](06-lluvia-de-ideas.md) | 94 ideas del proyecto, categorizadas, con su estado |
| [07-pareto.md](07-pareto.md) | Tres diagramas de Pareto: fallos de la evaluación, defectos y problemas de la construcción *(generado)* |
| [08-ishikawa.md](08-ishikawa.md) | Dos diagramas de Ishikawa con los cinco porqués |
| [09-cumplimiento-iso.md](09-cumplimiento-iso.md) | ISO/IEC 25010, ISO/IEC/IEEE 12207, CMMI e ISO/IEC/IEEE 29119-3 |
| [10-evidencias-y-reproduccion.md](10-evidencias-y-reproduccion.md) | Evidencias por entrega, lista de comprobación y cómo repetir todo |
| [11-elementos-acs.md](11-elementos-acs.md) | Elementos del ACS que existen y que faltan, y mejoras futuras |
| [13-recorridos-de-prueba.md](13-recorridos-de-prueba.md) | 12 recorridos simulados: lo esperado contra lo detectado |
| [14-metricas-de-transporte.md](14-metricas-de-transporte.md) | Los 12 indicadores con fórmula, fuente, umbrales, SQL y resultado *(generado de `scripts/doc_metricas.py`)* |
| [15-tablero-grafana.md](15-tablero-grafana.md) | Tablero de Odoo y Grafana incrustado |
| [16-sonarqube.md](16-sonarqube.md) | SonarQube: antes y después, interpretación |
| [17-rendimiento-por-volumen.md](17-rendimiento-por-volumen.md) | Tiempos de cada pantalla hasta 1 000 000 de posiciones |
| [18-mejora-continua-pdca.md](18-mejora-continua-pdca.md) | Ishikawa, Pareto y cuatro ciclos PDCA de la etapa del proyecto final |
| [19-matriz-de-trazabilidad.md](19-matriz-de-trazabilidad.md) | Actividades, entregables y criterios con su evidencia |

Otros contenidos de la carpeta:

- `Informe_final_proyecto_rastreo_buses.pdf`: informe final del proyecto (resultados de la etapa de la rúbrica), generado por `qa/generar_informe_final.py` con las evidencias actuales.
- `Informe_calidad_rastreo_buses.pdf`: informe técnico de 25 páginas con el formato del curso, **fotografía de la evaluación del 28-oct-2026** (se conserva tal cual; `qa/generar_informe.py` ya no puede reproducirlo porque las evidencias en bruto son las de la corrida más reciente).
- `evidencias/`: registros y resultados en bruto (JSON y logs).
- `figuras/`: gráficos del informe y diagramas de Pareto e Ishikawa.

Los documentos marcados *(generado)* los escribe `qa/generar_docs.py` desde las evidencias: **no se editan a mano**, se vuelve a ejecutar el script.

## Estado resumido (ejecución del 28-oct-2026)

| Medida | Resultado |
|---|---|
| Pruebas de Odoo | 150, 0 fallos |
| Suite en vivo | 42 casos, 3 fallos (DEF-008 a DEF-010) |
| Auditoría aleatoria | 1000 peticiones, 5,7 % de error |
| Cobertura de código | 93,8 % |
| Defectos | 10 registrados, 7 cerrados, 3 abiertos |
| Decisión | Apto para un piloto controlado; producción abierta tras cerrar los defectos y probar con un celular real |

## Cómo se genera cada cosa

```bash
sh qa/ejecutar_todo.sh                 # suite en vivo, auditoría y métricas (evidencias/)
python -X utf8 qa/generar_docs.py      # documentos 03, 04, 05, 07 y figuras
python -X utf8 qa/generar_informe_final.py   # informe final en PDF
```

Pasos completos y requisitos: [10-evidencias-y-reproduccion.md](10-evidencias-y-reproduccion.md).
