# Plan de implementación: calidad de diseño, espaciado y movimiento de la app móvil

Continúa la numeración de `docs/PLAN.md` y `docs/BITACORA.md` (última fase: 31). Aquí van las fases 32 a 37.

Nace de la auditoría del 2-nov-2026 sobre `apps/conductor-tablet`, hecha con las skills de diseño (impeccable nativo/Android, emil-design-eng, apple-design, animate-expo, find-animation-opportunities, break-ui y vercel-react-native) y con `docs/DISENO.md` como regla propia del proyecto.

## Punto de partida y meta

| Dimensión | Hoy | Meta | Qué la sube |
|---|---|---|---|
| Accesibilidad | 3 | 4 | Escala de fuente real, contraste del chip, estados vacíos |
| Rendimiento | 3 | 4 | SOS con driver nativo, listas virtualizadas |
| Apariencia y tema | 3 | 4 | Tokens de espaciado, radio y borde; un solo componente de aviso |
| Conformidad con la plataforma | 3 | 4 | Haptics, respuesta al pulsar, borde continuo |
| Adaptabilidad | 3 | 4 | Avisos críticos siempre visibles, probado con fuente grande |
| **Total** | **15/20** | **19/20** | |

Lo que **no** se toca porque ya cumple: pila nativa con `fade` de 160 ms, escala 0,97 al pulsar, `Pressable`, áreas seguras, objetivos de 48 a 72 dp, paletas día y noche medidas, Atkinson Hyperlegible, radio 8 px, `gap` en vez de márgenes, cero emojis, degradados y sombras.

## Corrección a la auditoría

El detalle de la alerta ("Up to 9545927 m away from its route…") **no** está sin traducir. `driver_api.py` ya lo calcula con `with_context(lang=user.lang)` y existe `i18n/es.po`. Salió en inglés porque el usuario de Odoo `johan` tiene el idioma en inglés, mientras la app estaba en español. El defecto real es que **el idioma del texto lo decide el usuario de Odoo y no el de la app**. Se corrige en la fase 33.

## Decisiones

Resueltas el 2-nov-2026 con quien dirige el proyecto, salvo D1 y D4, que siguen la recomendación.

| # | Decisión | Opciones | Elegida |
|---|---|---|---|
| D1 | Dónde probar el turno | Producción (ensucia datos, genera alertas reales) · Odoo local sembrado con `scripts/dev_seed.py` | **Odoo local** (recomendada). La app acepta `http://` en redes locales (`isLocalHost`) |
| D2 | Idioma del detalle de alertas | `lang` opcional en `/driver/state` · fijar el idioma de Odoo al crear el chofer · las dos | **Las dos**: la app manda `lang` y los choferes nuevos nacen con Odoo en español |
| D3 | Borde izquierdo de 8 px en avisos | A: conservarlo y documentarlo como excepción · B: marca de forma a la izquierda (como el punto de `GpsBadge`) con borde de 2 px | **B**: mantiene "palabra más forma" y sale de lo que las skills desaconsejan |
| D4 | `predictiveBackGestureEnabled: false` | Dejarlo · activarlo | **Dejarlo** (recomendada) hasta probar en un Android 14+ real; en turno abierto un gesto de atrás accidental es un riesgo. Documentar el motivo |
| D5 | "Deslizamiento corto" al cambiar de parada (prometido en `DISENO.md`, no construido) | Construirlo (200 ms, solo opacidad y 8 px) · quitar la promesa del documento | **Construirlo pequeño**; sin movimiento si hay "reducir animaciones" |

## Mapa de fases

**Rama de trabajo:** se decidió no fusionar todavía `feature/responsive-layout`. Cada fase sale de esa rama (no de `develop`), en su propia rama hija, y se fusiona de vuelta con `--no-ff`. Al terminar la fase 37 se fusiona todo a `develop`. Commits pequeños en Conventional Commits y sin coautoría de IA.

| Fase | Contenido | Rama | Depende de | Hallazgos | Tamaño |
|---|---|---|---|---|---|
| 32 | Entorno de pruebas sin producción y capturas base | `chore/qa-movil` | — | proceso | M |
| 33 | Avisos siempre visibles e idioma de las alertas | `fix/avisos-fijos` | 32 | P1, P2 | M |
| 34 | Respuesta táctil: haptics, SOS nativo, pulsación | `feature/feedback-cabina` | 32 | P2, P3 | M |
| 35 | Tokens de diseño: espaciado, radio, borde, contraste del chip | `refactor/tokens-diseno` | 33 | P2, P3 | M |
| 36 | Accesibilidad y contenido: fuente, vacíos, plurales, formatos | `feature/accesibilidad-contenido` | 35 | P2, P3 | M |
| 37 | Listas, plataforma y movimiento opcional | `chore/pulido-plataforma` | 36 | P3 | S |

Las fases 33 y 34 pueden ir en paralelo (tocan archivos distintos salvo `cabin.tsx`; si chocan, 34 espera a 33).

## Estado de la ejecución (2-nov-2026)

Las seis fases están hechas en `feature/responsive-layout`, a la espera de fusionarla a `develop`. Lo que cambió respecto al plan:

| Fase | Estado | Diferencias con lo planeado |
|---|---|---|
| 32 | Hecha | Servidor simulado en vez de Odoo con Docker; capturas base fuera del repo (ver más abajo) |
| 33 | Hecha | Las alertas abiertas van antes que la buena noticia de un SOS ya visto (en una pantalla con un solo aviso mostraba el SOS y ocultaba la alerta); tests de Python escritos pero sin correr aquí |
| 34 | Hecha | Sin Reanimated: el SOS usa `Animated` con `scaleX` y driver nativo. La vibración queda por sentir en un dispositivo real |
| 35 | Hecha | `space` es numérico (`space[4]` es 16); se añadieron `space[12]` (48) y `border.round`. El guarda corre en Jest, sin dependencias nuevas |
| 36 | Hecha, más trabajo del previsto | La matriz de fuente 1,3 y 2,0 en el emulador destapó cinco defectos reales que el plan no tenía (ver abajo) |
| 37 | Hecha | D4: el gesto de atrás predictivo sigue apagado. D5: el movimiento de la parada se construyó |

Defectos que solo apareció al probar con letra grande en Android, todos corregidos:

1. El turno se desbordaba: a 1,3× desaparecía la próxima parada y a 2,0× el SOS y Terminar turno eran inalcanzables. Ahora la página hace scroll entera.
2. Android informa 130 % como `1.2999999`: la comparación fallaba. Ahora hay tolerancia.
3. En selección, incidente y GPS el botón del encabezado dejaba al título casi sin ancho. Ahora se apilan.
4. El chip de la línea tenía alto fijo y recortaba el código. Ahora crece con el texto.
5. La selección quedaba sin listas visibles. Ahora el botón de inicio queda fijo abajo y el contenido hace scroll.

---

## Fase 32: entorno de pruebas sin producción

Objetivo: poder ver el turno, las alertas y los casos extremos sin tocar datos reales. Lo hecho hasta ahora creó un turno y una alerta "Fuera de ruta" en producción.

**Cambio respecto al plan original:** no se levantó Odoo con Docker (el daemon no corría y la imagen, la base y la siembra pesan mucho). Se escribió un **servidor simulado de la API del chofer**, que además permite el peor caso de forma determinista. Odoo sigue siendo la referencia: los tests de Python del backend se ejecutan en el CI.

1. `qa/mock_driver_api.py`: API del chofer con escenarios `normal`, `worst` (nombres largos, 9 buses, 12 paradas largas, alerta de ruta y SOS ya visto, ruta amarilla y ruta blanca), `onestop`, `empty` y `busy`, conmutables en caliente (`POST /__scenario`). Acepta cualquier login. El detalle de la alerta sigue el `lang` que mande la app.
2. `qa/capturas_movil.py`: matriz web de 4 tamaños (390×844, 844×390, 800×1280, 1280×800) × pantallas × día y noche × escenarios, con comprobación de desborde horizontal y errores de página. Genera 88 capturas.
3. `qa/capturas_android.py`: recorre el flujo real en el emulador (login, selección, turno, incidente, GPS, terminar, salir) por tamaño y escala de fuente, nunca pulsa SOS y **siempre restaura** tamaño, densidad y escala. Borra los datos de Expo Go al empezar para que no quede guardada la dirección de producción.
4. Trampas documentadas en los propios scripts: Metro no recarga en la ruta con "ó" (reiniciar el servidor en cada corrida), LDPlayer necesita "Abrir conexión remota", y Expo Go se abre con `--go`.
5. Las capturas base se guardan **fuera del repo** (≈90 PNG); solo se versionará evidencia final seleccionada en `docs/calidad/evidencias/movil/`.

Resultado de la base: 88 capturas web sin desbordes ni errores. En el peor caso la alerta de ruta y el SOS **no se ven** en horizontal ni en Android (quedan bajo el pliegue), y el chip de una ruta amarilla lleva texto blanco casi ilegible.

## Fase 33: avisos siempre visibles e idioma de las alertas

Hallazgo P1 más el idioma de las alertas. Los avisos de SOS y "Fuera de ruta" viven dentro del scroll de la columna izquierda y se cortan en horizontal.

1. `src/ui/Notice.tsx`: un solo componente de aviso (tono `danger` / `ok` / `warn`, título, detalle de hasta 2 líneas, `accessibilityLiveRegion`). Hoy el mismo cuadro está copiado en `shift`, `login`, `select` e `incident`. Aquí se aplica D3.
2. `app/shift.tsx`: sacar los avisos del `ScrollView`. En horizontal quedan **fijos arriba** de la columna izquierda; en vertical, entre el encabezado y el bloque de parada. Orden: confirmación de SOS, luego alerta. Máximo dos; el resto se resume en una línea ("+1 aviso").
3. Función pura `visibleNotices(sos, alerts)` en `src/shift/` con tests (orden, tope, SOS antes que alerta).
4. API: `POST /bus_tracking/driver/state` acepta `lang` opcional (`es`/`en`/`qu`; `qu` cae a español) y lo usa en `with_context(lang=…)`. La app lo envía desde `LangProvider`. Test de Python con `lang=es` y `lang=en`.
5. Al crear un chofer en `res_users.py`, fijar un idioma por defecto (`es_EC` si está instalado) sin pisar uno elegido.

Terminado cuando: con SOS y alerta abiertos, en los 4 tamaños y con fuente 1,3, ambos avisos se ven completos y el nombre de la parada sigue legible.

## Fase 34: respuesta táctil

1. **Haptics.** Antes de escribir código, leer los docs de Expo SDK 58 (regla de `AGENTS.md`). `npx expo install expo-haptics`. `src/ui/haptics.ts` con tres funciones (`commit`, `done`, `fail`) que no hacen nada en web ni lanzan errores. **Una por acción**, en el mismo instante que el efecto visual, nunca como única señal:
   - SOS: impacto medio cuando se cumple el 1,5 s.
   - Terminar turno: impacto medio al confirmar.
   - Aviso de problema: éxito al quedar enviado o en cola; error si falla.
   Test con el módulo simulado. Expo Go ya incluye `expo-haptics`, pero un build de producción necesita un EAS nuevo.
2. **SOS nativo** (`SosButton` en `src/ui/cabin.tsx`):
   - Reemplazar el ancho en porcentaje (hilo de JS) por una capa a todo el botón con `scaleX` 0→1, `transformOrigin: 'left'` y `useNativeDriver: true`. No hace falta Reanimated.
   - Un solo origen de verdad: el disparo sale del `finished` de la animación, no de un `setTimeout` aparte.
   - Al soltar, vuelve a 0 en **200 ms con `ease-out`** (`Easing.bezier(0.23, 1, 0.32, 1)`), en vez de saltar. Mantener 1,5 s lineal al pulsar.
   - Con "reducir animaciones": sin recorrido; el botón cambia de estado al instante y el texto dice "Mantén presionado", pero se sigue exigiendo el 1,5 s.
   - La lógica de mantener, cancelar y disparar pasa a `src/ui/hold.ts` (pura) con tests: cancelar antes de tiempo nunca dispara, dispara una sola vez, reanudar no acumula.
3. **Pulsación.** `src/ui/Press.tsx`: `Pressable` con respuesta inmediata (escala 0,98 y paso de tono) para filas de bus y ruta, tipos de incidente, chips de idioma y los botones del encabezado (GPS, día/noche). `Action` conserva su 0,97. Sin transición: son acciones de decenas al día.

Terminado cuando: el SOS se llena y se vacía fluido aunque el mapa esté cargando, y **se siente** la vibración en un dispositivo real (el emulador no sirve para esto).

## Fase 35: tokens de diseño

1. `src/ui/theme.ts`: `space` (4, 8, 12, 16, 24), `radius` (control 8), `border` (fino 2, marca 3) y un estilo `shape` que añade `borderCurve: 'continuous'`. `layout.ts` pasa a leer `space`.
2. Migrar los valores sueltos, **una pantalla por commit**, con capturas antes y después y sin desplazamientos de más de 4 px:

   | Hoy | Pasa a | Dónde |
   |---|---|---|
   | 10 (relleno y `gap`) | 8 o 12 según el contexto | listas, avisos |
   | 14 | 12 o 16 | `gap` de la marca, chips de idioma, botones |
   | 18 | 16 | relleno horizontal de los campos |
   | 6, 9 | derivados del tamaño de la marca | marcas del GPS |
   | `borderLeftWidth: 8` | según D3 | cuatro sitios, ya reunidos en `Notice` |

3. Guarda contra regresiones: `src/ui/spacing.test.ts` lee `app/*.tsx` y `src/ui/*.tsx` y falla si un `padding`, `margin` o `gap` usa un valor fuera de {0, 1, 2, 4, 8, 12, 16, 20, 24, 32}. Sin dependencias nuevas.
4. **Color del chip.** `src/ui/contrast.ts` con `readableOn(fondo)`: calcula la razón de contraste WCAG y elige entre blanco y tinta (`#172025`). Con un color inválido usa blanco sobre el acento. Tests con el azul de la ruta Quero (la tinta da ≈4,8:1 y el blanco ≈3,4:1), un amarillo y un granate. Aplicarlo en `shift.tsx` y `select.tsx`, y añadir el caso a `qa/contraste.py`.

Terminado cuando: no queda un valor fuera de la cuadrícula, el chip de cualquier color de ruta cumple 4,5:1 si es posible, y las capturas no cambian más de lo previsto.

## Fase 36: accesibilidad y contenido

1. **Escala de fuente.** En `Txt`, tope por tamaño en lugar de 1,3 para todo: `small` y `body` hasta 2,0; `data` hasta 1,6; `title` y `stop` hasta 1,3 (ya son enormes). Crear `Field` en `cabin.tsx` (campo de texto con el mismo tope y estilo) para reemplazar los `TextInput` duplicados de `login` e `incident`. Verificar con `font_scale` 1,3 y 2,0 en todas las pantallas: ningún control recortado ni inalcanzable (el scroll de `Screen` cubre los formularios; en el turno, el mapa conserva sus 150 px).
2. **Estados vacíos** en `select.tsx`: claves `noBuses`, `noRoutes` y `allBusesTaken` en es/en/qu (el test de paridad de claves ya existe) y el botón de inicio deshabilitado con su motivo.
3. **Plurales.** `tp(clave, n)` en `src/i18n/` con `Intl.PluralRules` (`_one`/`_other`; `qu` solo `_other`). Aplicar a `gpsSaving` ("1 punto guardado") y reemplazar el caso especial de `cabinStopsLeft`.
4. **Formatos.** `formatDistance(metros, lang)` con `Intl.NumberFormat` (coma decimal en español; sin decimales sobre 100 km). Usarlo en `shift.tsx` ("8837.9 km" pasa a "8838 km"). Con tests.
5. **Documentación.**
   - `DISENO.md`: tamaños de teléfono (16 a 40 px) y controles de 56, los tokens de espaciado, haptics reales, el movimiento del SOS y la decisión D3.
   - `GUIA-CHOFER.md`: rotación y celular.
   - `BITACORA.md`: entradas de las fases 32 a 37.
   - `qa/datos_calidad.py`: defectos nuevos (ver abajo) y regenerar con `qa/generar_docs.py`.

Terminado cuando: las pruebas pasan, la matriz de fuente 1,0/1,3/2,0 queda en `evidencias/movil/` y los textos nuevos están en los tres idiomas.

## Fase 37: listas, plataforma y movimiento opcional

1. `select.tsx`: `FlatList` (ya viene con RN) con `BusRow` y `RouteRow` memoizados y callbacks estables, en lugar de `ScrollView` con `map`. Una sola flota crece sin que esto duela.
2. `borderCurve: 'continuous'` ya llega por `shape` (fase 35); verificar que Android no se ve afectado.
3. D4: dejar `predictiveBackGestureEnabled: false`, con el motivo escrito en `PLAN-APP-CHOFER.md`; reabrir cuando haya un Android 14+ real. LDPlayer es Android 9 y no puede validarlo.
4. D5, si se aprueba: al cambiar `next_stop_id`, el bloque de parada entra con `opacity` 0→1 y `translateY` 8→0, **200 ms** `ease-out`, `useNativeDriver: true`. No corre en el primer montaje y se omite con "reducir animaciones". Una sola cosa animada por superficie, como pide `DISENO.md`.

Terminado cuando: las listas de 1 y de 200 buses se desplazan sin tirones en un dispositivo, y D5 se siente bien al llegar a una parada.

---

## Matriz de verificación (vale para cada fase)

| Qué | Cómo | Dónde |
|---|---|---|
| Tipos, linter y pruebas | `npx tsc --noEmit`, `npx expo lint`, `npx jest` | CI |
| Layout en los 4 tamaños | `qa/capturas_movil.py` contra Odoo local, normal y peor caso, día y noche | navegador |
| Android real | `qa/capturas_android.sh` en LDPlayer: 4 tamaños y fuente 1,0/1,3/2,0 | emulador |
| Sin desbordes | `scrollWidth <= innerWidth` en cada captura | navegador |
| Contraste | `python qa/contraste.py` | tokens |
| Accesibilidad | `qa/accesibilidad.py` (axe-core) en la versión web | navegador |
| Sensación (haptics, SOS, gestos, 120 Hz) | **dispositivo real**, build de release | a mano |

Lo que solo se puede juzgar en un dispositivo y queda fuera de la automatización: vibración, fluidez del SOS bajo carga, gestos de atrás, TalkBack y el teclado en pantalla.

## Registro de defectos (para `qa/datos_calidad.py`)

El último registrado es DEF-026. Todos nacen "Abiertos" y se cierran con su fase.

| ID | Hallazgo | Fase | Prueba que lo protege |
|---|---|---|---|
| DEF-027 | Los avisos de SOS y de alerta se cortan bajo el pliegue en horizontal | 33 | `visibleNotices` y capturas con ambos avisos |
| DEF-028 | El idioma del detalle de alertas lo decide el usuario de Odoo, no la app | 33 | Test de Python con `lang` |
| DEF-029 | Sin retroalimentación háptica, aunque `DISENO.md` la promete | 34 | Prueba del módulo y revisión en dispositivo |
| DEF-030 | El SOS anima en el hilo de JS y no vuelve suave al soltar | 34 | `hold.test.ts` |
| DEF-031 | Texto blanco fijo sobre el color de ruta del servidor, sin chequear contraste | 35 | `contrast.test.ts` y `qa/contraste.py` |
| DEF-032 | Valores de espaciado fuera de la cuadrícula y sin tokens | 35 | `spacing.test.ts` |
| DEF-033 | Tope de fuente de 1,3 y campos de texto que lo ignoran | 36 | Matriz de fuente en el emulador |
| DEF-034 | Sin estados vacíos en la selección de bus y ruta | 36 | Captura con cero buses |

## Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| Fuente 2,0 rompe el turno | Controles fuera de pantalla | `Screen` con scroll, mapa con mínimo de 150 px; si aun así no cabe, el bloque de parada pasa a una línea |
| `expo-haptics` exige un EAS nuevo | La vibración no llega a las tabletas ya instaladas | Avisar en la entrega; Expo Go sirve para probar |
| El emulador es Android 9 | No valida gesto de atrás, vibración ni 120 Hz | Una pasada en un celular real antes de cerrar la fase 34 |
| Migrar espaciados mueve el diseño | Regresión visual sin querer | Una pantalla por commit, capturas antes y después, tolerancia de 4 px |
| Pruebas en producción | Datos y alertas falsos en la oficina | D1: solo Odoo local; producción únicamente para sesiones de solo lectura |
