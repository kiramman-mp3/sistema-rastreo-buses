# Registro de defectos y análisis de causa raíz

Formato del taller de la Unidad 2: bitácora de incidencias y evaluación de la causa raíz. Los defectos DEF-001 a DEF-007 salen de `docs/BITACORA.md` (se hallaron y cerraron al construir); DEF-008 a DEF-010 los halló la evaluación de calidad del 28-oct-2026 y siguen **abiertos**. Generado por `qa/generar_docs.py` desde `qa/datos_calidad.py`.

Cada defecto se registra con tres campos separados: fallo observado, defecto localizado y causa de origen.

## 1. Bitácora de defectos

| ID | Fecha | Detectado por | Defecto | Ubicación | Estado |
|---|---|---|---|---|---|
| DEF-001 | 26-oct-2026 | Prueba manual con Traccar real | El webhook respondía 405 porque Traccar reenviaba con GET | docker-compose.yml | Cerrado |
| DEF-002 | 26-oct-2026 | Prueba de respaldo y restauración | El respaldo del filestore salía con 0 archivos y no avisaba | config/odoo.conf, scripts/backup.sh | Cerrado |
| DEF-003 | 26-oct-2026 | Revisión del log durante la prueba de punta a punta | El secreto del webhook aparecía completo en el log de Odoo | controllers/main.py | Cerrado |
| DEF-004 | 26-oct-2026 | Arranque de Odoo tras instalar pywebpush | Odoo dejó de arrancar (module lib has no attribute GEN_EMAIL) | docker/odoo/Dockerfile | Cerrado |
| DEF-005 | 26-oct-2026 | Test del asistente de respuesta | El pasajero habría visto la etiqueta <br/> como texto | asistente de respuesta (retirado después) | Cerrado |
| DEF-006 | 27-oct-2026 | Suite de Odoo | Un bus sin ruta rompía el cálculo de desvío de ruta | models/bus_alert.py | Cerrado |
| DEF-007 | 26-oct-2026 | Revisión en el navegador | El navegador seguía mostrando un CSS viejo del portal | controllers/portal.py | Cerrado |
| DEF-008 | 28-oct-2026 | Suite en vivo (E7) y auditoría | Se guardan posiciones con latitud o longitud imposibles (p. ej. 95°) | models/bus_vehicle.py (_apply_position), models/bus_position.py | ABIERTO |
| DEF-009 | 28-oct-2026 | Suite en vivo (E8) y auditoría | Una latitud no numérica produce HTTP 500 en el webhook | models/bus_vehicle.py, controllers/main.py | ABIERTO |
| DEF-010 | 28-oct-2026 | Suite en vivo (E9) y auditoría | Una hora GPS inválida produce HTTP 500 en el webhook | models/utils.py (parse_traccar_dt), controllers/main.py | ABIERTO |

Resumen: 10 registrados, 7 cerrados (70 %), 3 abiertos. Densidad: 5,9 defectos por KLOC (1,686 KLOC de Python sin pruebas).

## 2. Análisis de causa raíz e impacto

### DEF-001: El webhook respondía 405 porque Traccar reenviaba con GET

- **Causa raíz:** Traccar 6 renombró la clave de reenvío (forward.json pasó a forward.type) y el proyecto asumía la versión anterior; no había prueba contra la versión vigente.
- **Categoría:** Configuración
- **Prueba que lo protege:** F12 y test_http (webhook con cabecera); probado con Traccar real

### DEF-002: El respaldo del filestore salía con 0 archivos y no avisaba

- **Causa raíz:** La configuración de producción sustituía el archivo de la imagen y no definía data_dir; el script no comprobaba que hubiera archivos.
- **Categoría:** Configuración
- **Prueba que lo protege:** Respaldo y restauración repetidos de principio a fin (bitácora, 4.ª sesión)

### DEF-003: El secreto del webhook aparecía completo en el log de Odoo

- **Causa raíz:** El secreto viajaba en la URL y el servidor registra las URL; se priorizó la compatibilidad y no la confidencialidad.
- **Categoría:** Seguridad
- **Prueba que lo protege:** F1 y F12; test_webhook_accepts_secret_in_header; 0 apariciones del secreto en el log

### DEF-004: Odoo dejó de arrancar (module lib has no attribute GEN_EMAIL)

- **Causa raíz:** pip instaló la última cryptography, incompatible con el pyOpenSSL de la imagen; las dependencias no tenían versión fijada.
- **Categoría:** Configuración
- **Prueba que lo protege:** Imagen reconstruida; test_push (cifrado y firma)

### DEF-005: El pasajero habría visto la etiqueta <br/> como texto

- **Causa raíz:** html_escape devuelve Markup y .replace sobre Markup escapa el <br/> nuevo.
- **Categoría:** Lógica
- **Prueba que lo protege:** Función retirada en la simplificación del 27-oct

### DEF-006: Un bus sin ruta rompía el cálculo de desvío de ruta

- **Causa raíz:** La regla asumía que todo bus tiene ruta y ningún test cubría el caso sin ruta.
- **Categoría:** Lógica
- **Prueba que lo protege:** test_simple.TestOffRoute

### DEF-007: El navegador seguía mostrando un CSS viejo del portal

- **Causa raíz:** Odoo sirve los estáticos con caché larga y la URL no cambiaba al modificar el archivo.
- **Categoría:** Configuración
- **Prueba que lo protege:** test_public_assets_are_versioned_so_browsers_never_keep_stale_copies

### DEF-008: Se guardan posiciones con latitud o longitud imposibles (p. ej. 95°)

- **Causa raíz:** Los campos float no tienen restricción de rango y _apply_position no valida lo que recibe; ninguna prueba enviaba coordenadas fuera de rango.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E7 (falla hoy); falta portarla a las pruebas de Odoo

### DEF-009: Una latitud no numérica produce HTTP 500 en el webhook

- **Causa raíz:** El valor llega sin convertir al ORM, que lanza una excepción no controlada.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E8 (falla hoy)

### DEF-010: Una hora GPS inválida produce HTTP 500 en el webhook

- **Causa raíz:** parse_traccar_dt llama a isoparse sin capturar el error de formato.
- **Categoría:** Validación de entrada
- **Prueba que lo protege:** E9 (falla hoy)

## 3. Qué falta para cerrar los abiertos

1. Validar en `_apply_position` la latitud (−90 a 90), la longitud (−180 a 180) y el tipo de cada campo; responder 400 y no guardar.
2. Capturar el error de formato en `parse_traccar_dt` y responder 400.
3. Agregar una restricción `@api.constrains` de rango en `bus.position`.
4. Portar E7, E8 y E9 a `addons/bus_tracking/tests/test_http.py` para que la suite de Odoo los proteja, y volver a ejecutar `qa/ejecutar_todo.sh`.
5. Limpiar las posiciones inválidas ya guardadas en las bases de desarrollo.
