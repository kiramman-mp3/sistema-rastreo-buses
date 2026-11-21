# Multas como reales y cierre previo a `main`

Fecha: 2026-11-21. Base: `develop` en `15c6115` (módulo `16.0.1.10.0`, app de tableta `1.4.0`, última etiqueta `v1.0.6-rc3`). Continúa [`PLAN-MULTAS.md`](PLAN-MULTAS.md).

## 0. Propósito y decisiones

El sistema es una demostración de capacidades y no se pondrá en producción. Por eso las multas dejan de presentarse como "de demostración": se tratan como reales dentro del montaje. Los montos siguen siendo valores de ejemplo en dólares.

Decisiones del usuario (21-nov):

| Tema | Decisión |
|---|---|
| Modo demostración de las multas | Se retira: ya no hay aviso en pantalla ni interruptor `bus_tracking.fines_real` |
| Campo `demo` de la API del chofer | Se quita de la respuesta de `/bus_tracking/driver/fines` (no se deja en `false`) |
| Etiqueta `simulated` | Se mantiene: distingue datos de ejemplo de un GPS real; no es el aviso de demostración |
| Montos, reglas y tope mensual | Sin cambios ($5 a $25; tope mensual 0) |
| Aviso de demostración | Queda solo en la documentación (`PRIVACIDAD.md`), no en las pantallas |

Reglas de trabajo: las de `CLAUDE.md`. Una rama por tema desde `develop`, commits pequeños con Conventional Commits, linter, pruebas y build antes de integrar con `git merge --no-ff`. La documentación va en ramas `docs/*`, sin mezclarla con código.

## 1. Alcance en el código

El modo demostración está en estos sitios:

| Archivo | Qué hay |
|---|---|
| `controllers/driver_api.py` (`fines`) | La respuesta incluye `'demo': not real` |
| `models/bus_fine.py` | Campo calculado `demo_notice` y `_compute_demo_notice` |
| `views/bus_fine_views.xml` | Aviso amarillo en la ficha y campo invisible `demo_notice` |
| `models/res_config_settings.py` y `views/res_config_settings_views.xml` | Casilla *Las multas son reales* (`bus_fines_real`) |
| `apps/conductor-tablet/app/fines.tsx` | Estado `demo` y aviso `finesDemo` |
| `apps/conductor-tablet/src/i18n/index.ts` | Texto `finesDemo` en español, inglés y kichwa |
| `tests/test_fine_api.py`, `tests/test_fine_panel.py` | Pruebas del aviso y del parámetro |
| `i18n/bus_tracking.pot`, `es.po`, `qu.po` | Textos traducidos |

La plantilla del PDF no tiene el aviso y no cambia. El último defecto registrado es `DEF-086`; los nuevos empiezan en `DEF-087`.

## 2. Etapas

Tamaño: S (horas), M (un día).

| Etapa | Rama | Qué hace | Tamaño |
|---|---|---|---|
| 0 | — | Entorno y línea base | S |
| 1 | `fix/version-tableta` | Igualar `package.json` con `app.json` | S |
| 2 | `feature/multas-como-reales` | Quitar el modo demostración | M |
| 3 | `fix/multas-rendimiento` | Medir y, si hace falta, sacar el detector de la ruta caliente | M |
| 4 | `fix/migracion-alertas` | Probar el costo de la migración de alertas | S |
| 5 | `docs/multas-reales` | Documentación del cambio | S |
| 6 | — | Cierre y paso a `main` | S |

Dependencias: 0, 1, 2, luego 3 y 4 (independientes entre sí), luego 5 y 6. La etapa 5 usa las cifras de las etapas 2 a 4.

### Etapa 0: preparación

1. Iniciar Docker Desktop y levantar el entorno con los pasos del README (el Odoo del proyecto queda en el puerto 8070 por `ODOO_PORT`).
2. Línea base en `develop` antes de cambiar nada: suite de Odoo, `flake8`, y en la tableta `lint`, `typecheck` y Jest.
3. Revisar `git status`. El `CLAUDE.md` local difiere del commiteado (le faltan la sección de documentación y la línea de la app de tableta); no se toca sin orden del usuario.

### Etapa 1: `fix/version-tableta`

- `apps/conductor-tablet/package.json`: de `1.0.0` a `1.4.0`, igual que `app.json`. Revisar `package-lock.json`.
- Commit: `fix: align package.json version with app.json`.
- Verificación: `npm run lint`, `npm run typecheck`, `npm test`.

### Etapa 2: `feature/multas-como-reales`

Un commit por paso:

1. `refactor: drop the demo flag from the driver fines API`: quitar `demo` de la respuesta y de `real` en `driver_api.py`.
2. `refactor: remove the demo notice from the tablet fines screen`: quitar el estado `demo` y el aviso de `fines.tsx`, `finesDemo` en los tres idiomas, y `demo` en `src/api/types.ts` y `client.test.ts`.
3. `refactor: remove the demo notice from the fine form`: quitar `demo_notice` del modelo y de la ficha.
4. `refactor: remove the fines_real setting`: quitar `bus_fines_real` del modelo y de la vista de Ajustes.
5. `test: update the fine tests for real fines`: reescribir `test_fine_api.py` y `test_fine_panel.py` para comprobar que la respuesta no trae `demo`, que la ficha no tiene aviso y que `simulated` se conserva.
6. `feat: clean the old fines_real parameter`: migración `16.0.1.11.0` con `post-migrate.py` corto que borra `bus_tracking.fines_real` de `ir.config_parameter`; subir la versión del manifest.
7. `chore: refresh the fines translations`: regenerar `.pot`, `es.po` y `qu.po`; correr `qa/traducciones.py`.
8. `chore: bump tablet app to 1.4.1`: en `app.json` y `package.json`.

Verificación: suite de Odoo completa, `flake8 addons/bus_tracking`, Jest, `lint`, `typecheck` y `expo export`. Revisión visual del kanban, la ficha y *Mis multas* sin aviso.

La app 1.4.0 ya instalada seguirá funcionando: lee `data.demo` y, al faltar, `setDemo(undefined)` deja el aviso oculto.

### Etapa 3: `fix/multas-rendimiento`

`bus.alert.create` y el cierre de alertas llaman a `bus.fine._trigger_detection()`, que dispara el cron en la ruta de ingreso de posiciones.

1. Medir con `qa/rendimiento_volumen.py` con y sin el disparo.
2. Si el costo es visible, dejar la detección al cron periódico o agrupar los disparos. Commit: `perf: defer fine detection out of the ingest path`.
3. Si no lo es, no se toca el código; las cifras se anotan en la documentación.

### Etapa 4: `fix/migracion-alertas`

La migración `16.0.1.10.0` marca las alertas existentes con `fine_checked`. Probar cuánto tarda con el volumen de `qa/rendimiento_volumen.sql` y que se pueda repetir sin daño. Se cambia solo si hay un problema real.

### Etapa 5: `docs/multas-reales`

Un commit `docs:` por tema:

1. `PLAN-MULTAS.md`: enlazar este plan y registrar que el modo demostración se retiró.
2. `PRIVACIDAD.md`: nota de que el montaje es de demostración, sin choferes reales ni descuentos.
3. Guías: `GUIA-CHOFER.md`, `OPERACION.md`, `PERSONALIZACION.md` y `PRODUCCION.md`, sin el interruptor ni el aviso.
4. `ARQUITECTURA-Y-DATOS.md` y `DISENO.md`: sin `demo_notice` ni la casilla de Ajustes.
5. `qa/datos_calidad.py`: defectos desde `DEF-087`; regenerar con `python -X utf8 qa/generar_docs.py`.
6. `ROADMAP.md`: marcar lo hecho, corregir la última etiqueta (`v1.0.6-rc3`) y las versiones; entrada del día en `BITACORA.md`.
7. README: sección de multas, capturas si la ficha cambió y contribuidores con `git shortlog -sn`.

### Etapa 6: cierre

1. Con todo en `develop`, repetir las verificaciones completas y documentar los resultados en `docs/calidad/`.
2. `git merge --no-ff develop` en `main` y etiqueta (por ejemplo `v1.0.7-rc3`), solo con confirmación del usuario.
3. El `push` y la etiqueta también esperan confirmación.

## 3. Riesgos

| Riesgo | Mitigación |
|---|---|
| La tableta 1.4.0 ya instalada lee `demo` | Se trata como ausente; se prueba con la API nueva |
| La migración borra un parámetro que alguien usa | Es el interruptor que se retira; se cubre con una prueba |
| Textos sin traducir tras quitar claves | `qa/traducciones.py` en la etapa 2 |
| Suite roja por el estado de la base | Línea base de la etapa 0; reinstalar con los pasos del README si hace falta |

## 4. Verificaciones al cerrar

Se entrega el resumen que pide `CLAUDE.md`: rama, commits y resultado de pruebas de Odoo y de Jest, linter y build, con las cifras sacadas de las ejecuciones.
