# Diseño de Buses UTA

Guía de identidad para el portal público, el panel de Odoo y la tableta del chofer. Reemplaza la versión anterior, que describía una identidad que el código ya no usaba. Plan y hallazgos: `docs/PLAN-UX.md`.

## La idea: la línea

Un bus es una línea con paradas. Esa forma es lo único decorativo del sistema y sale siempre de **datos reales** (`bus.route.stop`), nunca de un dibujo genérico:

| Dónde | Cómo aparece |
|---|---|
| Marca | Un tramo de línea con tres paradas; la del medio en amarillo de señal: "estás aquí". |
| Portal, portada | La línea con más buses, dibujada con sus paradas y sus buses en vivo. Se toca la parada propia. |
| Portal, ruta | La línea vertical de paradas junto al mapa. "Mi parada" se recuerda en el navegador. |
| Panel | La tarjeta del bus muestra su línea en horizontal: de dónde viene y qué le falta. |
| Tableta | La franja superior es la misma línea, con la próxima parada en grande. |

Lo interactivo de la portada sale de esa idea: la persona toca su parada y ve cuántas paradas le faltan al bus más cercano.

## Voz

Tú, español de Ecuador, frases cortas. **Nunca prometemos lo que el sistema no sabe.**

- Sin superlativos ni jerga: nada de "integral", "garantizado", "neurálgico", "satelital", "cinemático".
- Sin mayúsculas sostenidas, sin etiquetas pequeñas sobre los títulos.
- Todo número sale de la base de datos o de Ajustes. Si no hay dato, no se muestra.
- Decir lo que pasa, también cuando no hay nada: "Ahora no hay buses con señal en esta línea."

| Antes | Ahora |
|---|---|
| Muévete seguro hacia el campus | ¿Dónde viene tu bus? |
| Red operativa: 8 buses en servicio regular | 3 buses con señal ahora |
| Sincronizando satélite... | Buscando buses… |
| Llega en 5–8 min | Está a 3 paradas de tu parada |
| ¡Reporte registrado exitosamente! | Recibimos tu mensaje |

## Color

Medido con `python qa/contraste.py`, que falla si un par baja de su mínimo.

| Token | Valor | Uso | Contraste medido |
|---|---|---|---|
| `--papel` | `#F1F3F2` | Fondo (gris verdoso frío, no crema) | — |
| `--papel-2` | `#E3E8E6` | Paneles y fragmentos: un paso de tono, no una línea ni una sombra | — |
| `--blanco` | `#FFFFFF` | Solo campos de formulario | — |
| `--tinta` | `#172025` | Texto | 14,8:1 sobre papel |
| `--tinta-2` | `#3E4C51` | Texto secundario | 8,0:1 sobre papel; 7,2:1 sobre papel-2 |
| `--granate` | `#7A1A22` | La acción principal y el color de ruta por defecto | blanco encima 10,5:1; como enlace 9,4:1 |
| `--senal` | `#FFC62B` | "Ahora", "tu parada", el anillo de foco | tinta encima 10,5:1 |
| `--ok` / `--alerta` / `--peligro` | `#1D6B44` / `#7A5000` / `#A1221B` | Estados, siempre con palabra o forma | 5,8 / 6,3 / 6,8:1 |

Tableta: modo día sobre blanco (tinta 16,5:1) para sol directo y modo noche sobre `#0E1316` (texto `#F2F5F4`, 17,0:1). Objetivo: **7:1 (AAA) para texto de cuerpo** en portal y tableta; 4,5:1 como mínimo en el panel.

## Tipografía

- **Bricolage Grotesque** (variable, en `static/fonts/`) para títulos y números grandes.
- **Atkinson Hyperlegible** (400 y 700) para el texto: pensada para baja visión, se lee bien en movimiento y al sol.
- Cinco tamaños en el portal (`--t-1` a `--t-5`: 14, 17, 20–24, 28–44 y 40–88 px). Campos con 16 px o más para que el teléfono no haga zoom.
- Tableta: nada visible por debajo de 20 px; datos a 32 px; la próxima parada a 56–64 px.
- Teléfono (lado corto menor a 600 dp): nada por debajo de 16 px; datos a 24 px; la próxima parada a 40 px; controles de 56 px (72 px en tableta). El tamaño de letra del sistema se respeta: textos pequeños y de cuerpo hasta el 200 %, los números grandes hasta el 130 % (`MAX_FONT_SCALE`).

## Fotos

- **Nunca imágenes generadas por IA**, ni la marca de la UTA puesta sobre cosas que no son suyas.
- Hoy se usan seis fotos reales de Ambato de Wikimedia Commons, con licencia CC y su crédito en el pie de cada página (`static/img/ambato/CREDITOS.md`). Muestran la ciudad, no los buses ni el personal.
- Cuando la universidad entregue fotos propias de sus buses y paradas (con consentimiento de quien salga), reemplazan a estas. WebP, 800 y 1200 px, menos de 200 KB.

## Movimiento

Una sola cosa con significado por superficie; lo demás es inmediato.

- Portal: los buses avanzan **linealmente** entre posiciones (sin el frenazo de *ease-out*); el punto de "en vivo" respira cada 2 s solo mientras los datos son recientes; las secciones entran una vez, 18 px, escalonadas 70 ms.
- Panel: igual para los buses; el bucle de animación se detiene si nada se mueve o la pestaña está oculta.
- Tableta: cambio de parada con un deslizamiento corto (200 ms, solo opacidad y 8 px, sin movimiento si el sistema pide reducir animaciones).
- Háptica: una sola vibración por acción que confirma algo, en el mismo instante que el efecto visual y nunca como única señal: el SOS al cumplirse el segundo y medio, terminar turno al confirmar, y el aviso de problema al quedar enviado (éxito) o al fallar (error).
- SOS: el relleno crece con una transformación nativa (1,5 s lineal) y se vacía en 200 ms al soltar; con "reducir animaciones" aparece de una vez, pero se sigue exigiendo el segundo y medio.
- `prefers-reduced-motion` desactiva todo desplazamiento y deja el contenido.

## Espaciado, esquinas y bordes

- **Cuadrícula de 4 px.** Todo `padding`, `margin` y `gap` sale de `space[n]` en `theme.ts` (`space[2]` es 8, `space[4]` es 16). `src/ui/spacing.test.ts` falla si un número suelto cae fuera de la cuadrícula.
- **Una esquina para todos los controles:** radio de 8 px con `borderCurve: 'continuous'` (`shape.control`). Los círculos usan `border.round`.
- **Bordes finos y parejos:** 2 px (`border.thin`). No hay franjas gruesas de color en un solo lado.
- **Avisos.** Un solo componente (`Notice`): el estado se dice con una palabra y una forma (rombo para peligro, cuadrado para aviso, punto para buena noticia, las mismas formas que el estado del GPS), nunca solo con color. Primero lo que sigue pendiente (un SOS que nadie vio, luego las alertas abiertas) y al final la buena noticia; lo que no cabe se cuenta ("2 avisos más"). Los avisos nunca se van con el scroll.
- **Color de la línea.** El texto del código sobre el chip de la línea es blanco o la tinta, según cuál contraste más con el color que puso la oficina (`readableOn`).
- **Texto grande.** Con la fuente del sistema al 130 % o más no hay forma de que todo quepa en una vista: el turno y la selección pasan a hacer scroll, con los botones principales abajo, y las listas y la franja de paradas se acortan para que ningún nombre se parta.

## No hacer

Emojis como íconos · etiquetas en mayúsculas sobre los títulos · degradados · sombras en cosas quietas · *glassmorphism* · pulsos decorativos infinitos · tarjetas iguales en fila · números de ejemplo que parecen datos · imágenes IA · *mockups* de teléfono · `!important` salvo para ganarle a Odoo.

## Archivos

| Archivo | Qué tiene |
|---|---|
| `static/src/css/brand.css` | Tokens y fuentes (portal, login y panel) |
| `static/src/portal/site.css` | Componentes del sitio público: marco, cabecera, botón, campo, línea de paradas, "en vivo", avisos, pie |
| `static/src/portal/pages.css` | Composición de cada página pública |
| `static/src/scss/primary_variables.scss` | Colores y fuentes del panel de Odoo |
| `apps/conductor-tablet/src/ui/theme.ts` | Los mismos tokens para la tableta, modos día y noche |
| `qa/contraste.py` | Medición de contrastes |
| `qa/capturas_ui.py` | Capturas del portal y del panel para revisión visual |

## Créditos

Fuentes con licencia OFL. Fotos: ver `static/img/ambato/CREDITOS.md`.
