# Sistema de Aseguramiento de la Calidad (QA)

Entorno automatizado para pruebas unitarias, de integración, auditoría estática, accesibilidad visual, métricas de complejidad y generación determinista de informes de calidad.

---

## Módulos y Herramientas

| Script / Módulo | Propósito | Salida principal |
|---|---|---|
| [`qa_suite.py`](qa_suite.py) | Suite end-to-end de pruebas de integración contra Odoo y Traccar. | `docs/calidad/evidencias/suite.json` |
| [`ejecutar_todo.py`](ejecutar_todo.py) | Orquestador general del ciclo completo de verificación. | Ejecuta suite, auditoría, métricas y docs. |
| [`ejecutar_todo.sh`](ejecutar_todo.sh) | Envoltura Bash para entornos CI/CD y servidores Linux. | Retorno con código de salida 0/1. |
| [`auditoria.py`](auditoria.py) | Análisis estático de modelos, seguridad RPC, secretos y reglas de acceso. | `docs/calidad/evidencias/auditoria.json` |
| [`metricas.py`](metricas.py) | Análisis cuantitativo de complejidad, líneas de código y cobertura. | `docs/calidad/evidencias/metricas.json` |
| [`accesibilidad.py`](accesibilidad.py) | Auditoría de accesibilidad WCAG 2.1 sobre el portal con `axe-core`. | Reporte de violaciones de accesibilidad. |
| [`contraste.py`](contraste.py) | Medición de contraste de tokens de color según estándar WCAG AAA (7:1). | Verificación de legibilidad en cabina y web. |
| [`capturas_ui.py`](capturas_ui.py) | Capturas automatizadas del portal web y panel con Playwright. | `docs/calidad/evidencias/ux/` |
| [`capturas_movil.py`](capturas_movil.py) | Capturas del layout móvil y tablet en diferentes orientaciones. | `docs/calidad/evidencias/ux/` |
| [`capturas_tablet.py`](capturas_tablet.py) | Capturas de la pantalla de cabina en modo diurno y nocturno. | `docs/calidad/evidencias/ux/` |
| [`tablet_dispositivos.py`](tablet_dispositivos.py) | La app del chofer (versión web) en 16 tamaños y orientaciones: iPhone 16, Pixel Fold exterior, interior y pantalla dividida, tabletas, teléfonos pequeños. Avisa de lo que falte, quede cortado o fuera de alcance. | Informe en consola y capturas en `qa/salida/tablet/`. |
| [`tablet_errores_humanos.py`](tablet_errores_humanos.py) | Errores humanos en la app del chofer: doble toque, clave mala, SOS sin querer, alertas, pérdida de señal. 34 comprobaciones. | PASS/FAIL por comprobación. |
| [`tablet_datos_prueba.py`](tablet_datos_prueba.py) | Prepara y limpia en el Odoo de desarrollo lo que necesitan las dos pruebas anteriores (alertas abiertas, dirección GPS de prueba). | Se pasa a `odoo shell`. |
| [`datos_calidad.py`](datos_calidad.py) | Datos históricos de defectos (DEF-001 a DEF-038) y causas raíz. | Fuente para Pareto e Ishikawa. |
| [`generar_docs.py`](generar_docs.py) | Regenera los documentos 03, 04, 05 y 07 de `docs/calidad/` y gráficos PNG. | Documentación y figuras en `docs/calidad/`. |
| [`generar_informe.py`](generar_informe.py) | Compilador de PDF de auditoría formal usando ReportLab. | `docs/calidad/Informe_calidad_rastreo_buses.pdf` |
| [`mock_driver_api.py`](mock_driver_api.py) | Servidor mock de Odoo para pruebas de interfaz de la app del chofer. | Emula endpoints `/driver/*`. |
| [`traducciones.py`](traducciones.py) | Verifica que no existan cadenas sin traducir en el archivo `i18n/es.po`. | Validación de internacionalización. |

---

## Cómo ejecutar la suite de calidad

### 1. Ejecución completa determinista
Para correr todas las pruebas y regenerar gráficos y documentos de calidad:
```bash
python -X utf8 qa/ejecutar_todo.py
```

### 2. Generar únicamente documentación y figuras
Si se agregaron defectos o métricas a `qa/datos_calidad.py`:
```bash
python -X utf8 qa/generar_docs.py
```

### 3. Compilar el informe en PDF
```bash
python -X utf8 qa/generar_informe.py
```
El PDF resultante se ubicará en [`../docs/calidad/Informe_calidad_rastreo_buses.pdf`](../docs/calidad/Informe_calidad_rastreo_buses.pdf).
