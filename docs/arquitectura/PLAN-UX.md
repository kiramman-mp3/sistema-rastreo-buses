# Plan de rediseño de experiencia: portal público, panel Odoo y tableta del chofer

Continúa la numeración de `docs/arquitectura/PLAN.md` y `docs/arquitectura/PLAN-APP-CHOFER.md` (fases 26 a 31).
Fecha del análisis: 2026-11-01. Base revisada: `develop` en `9118fc7`.

**Estado (2026-11-02):** fases 26 a 30 hechas e integradas en `develop`; fase 31 con la medición automática hecha y las pruebas con personas pendientes (`docs/calidad/12-validacion-ux.md`). Desvíos respecto del plan: la tableta no recibió `react-native-svg` (los íconos se dibujan con vistas), el portal no usa Lighthouse sino axe y el inspector de diseño, y la hoja de incidentes no tiene dictado por voz.

## 1. Resumen

El sistema funciona, pero la interfaz actual, sobre todo desde las fases 23 a 25, **dice cosas que no son ciertas** y **se ve como una plantilla**. Esas dos cosas explican la sensación de que "no tiene alma":

1. **Contenido inventado.** Noticias con fechas ficticias, "15,000+ estudiantes", un teléfono y redes sociales que no son de la UTA, tiempos de llegada calculados con `índice × 3`, un contador que muestra "8 buses" cuando hay cero, y en la tableta una barra de "cadencia" con un "Bus #02" que no existe. Una persona lo nota en segundos y deja de confiar en todo lo demás, incluido el mapa, que sí es real.
2. **Estética genérica.** Paleta *slate* de Tailwind, fuentes del sistema, emojis como íconos, *glassmorphism*, pulsos infinitos, etiquetas en mayúsculas con "人", flechas "→" en cada enlace, un *mockup* de teléfono y una foto generada por IA de un bus con un logo UTA falso. Además, el commit `f1c8a5c` dice que copia el layout de "CasaBus". Es justo lo que `docs/diseno/DISENO.md` prohibía, y la identidad original (la línea de la ruta, Bricolage Grotesque y Atkinson Hyperlegible) se perdió: las fuentes siguen en `static/fonts/`, pero ya no se cargan.

La propuesta: **primero la verdad, después el estilo**. La fase 26 quita lo falso y corrige los fallos. Las fases 27 a 30 reconstruyen las tres interfaces alrededor de una sola idea visual, la línea de la ruta con sus paradas, y de una voz cercana y honesta. La fase 31 lo valida con personas reales.

## 2. Hallazgos

Severidad: **S1** engaña al usuario o pone en riesgo a alguien; **S2** rompe una función; **S3** degrada la experiencia; **S4** es cosmético.

### 2.1 Portal público

| # | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| P1 | S1 | Tiempos de llegada falsos: "Llega en (i×3+2)–(i×3+5) min" para cada parada, sin importar dónde estén los buses. | `views/portal_templates.xml:215` |
| P2 | S1 | Si no hay buses, la página dice "8 buses en servicio activo" (`total_active_buses or 8`). | `views/portal_templates.xml:37` |
| P3 | S1 | Datos fijos que no salen del sistema: "Frecuencia 8-12 min", "~10 min", "♿ Accesible", "24 a 48 horas", "Comprobante oficial". | `portal_templates.xml:37,78,80,323,523`; `landing_templates.xml:188` |
| P4 | S1 | Noticias ficticias con fechas (31, 28 y 24 de octubre), "15,000+ estudiantes", "100% gratuito", teléfono `+593 3 284-8487`, correo `transporte@uta.edu.ec` y redes a `facebook.com` genérico. Nada de esto lo entregó la universidad (ver `docs/guias/PERSONALIZACION.md`). | `landing_templates.xml:76-98,330-352,363-430` |
| P5 | S1 | La foto de portada es una imagen generada por IA: un bus con el logo y el nombre de la UTA inventados, texto deformado ("Side 838") y una placa falsa. Se presenta como si fuera real y usa la marca institucional sin aprobación. | `static/img/landing/hero-bus.jpg` (y probablemente el resto de `img/landing/`) |
| P6 | S2 | Los tipos de queja del formulario (`lost_item`, `conduct`) no existen en el modelo, que solo admite `delay`, `behavior`, `safety`, `cleanliness` y `other`. Todo lo que no es "Demora" se guarda **en silencio** como "Otro", así que el filtro por tipo del panel no sirve. | `portal_templates.xml:384,389` frente a `models/bus_complaint.py:8-14` |
| P7 | S2 | Las tarjetas de motivo son `<div>` con clic: no se alcanzan con teclado ni las anuncia un lector de pantalla. | `portal_templates.xml:379-398`, `portal/complaint.js` |
| P8 | S2 | El buscador de la portada (`?q=`) y los atajos de campus (`?campus=`) no hacen nada: `routes()` ignora esos parámetros. El filtro por campus de `/rutas` busca la palabra "huachi" dentro del nombre de la línea (Troncal, Izamba, Pelileo, Píllaro), así que casi siempre deja la página vacía. | `landing_templates.xml:201,222`; `controllers/portal.py:129`; `portal_templates.xml:108-128` |
| P9 | S2 | Íconos de Font Awesome (`fa fa-bus`, `fa fa-undo`) y clases de Bootstrap (`d-flex`, `badge`, `form-select`, `mt-4`) en páginas que usan `web.layout` sin esos recursos: el centro del marcador del bus queda vacío y el botón de restablecer no tiene ícono ni texto. | `portal/portal_map.js:130`, `portal_templates.xml:186-190,251` |
| P10 | S2 | El selector de idioma cambia muy poco: casi todo el texto de la portada, de las tarjetas y del formulario está escrito en español dentro de la plantilla, sin pasar por `portal_i18n.py`. En inglés o kichwa la página sale mezclada. | `landing_templates.xml` y `portal_templates.xml` completos; `portal_map.js:216,232` |
| P11 | S2 | El botón "Portal Chofer / Operaciones" lleva a `/web/login`, pero el chofer usa la tableta y su grupo no abre el panel. Un chofer que entra ahí no encuentra nada útil. | `landing_templates.xml:55` |
| P12 | S3 | Peso: ocho fotos JPG de 0,8 a 1 MB cada una más un PNG de 650 KB, sin `srcset` ni WebP/AVIF; la portada carga cerca de 8 MB. En la parada, con datos móviles, eso son segundos de espera. | `static/img/landing/` |
| P13 | S3 | Sin `prefers-reduced-motion` ni `:focus-visible` en ninguna hoja pública; 87 `!important` en `landing.css`; pulsos infinitos. Antes estaban (ver `DISENO.md`). | `landing/landing.css`, `portal/portal.css` |
| P14 | S3 | Jerga que no ayuda: "satelital", "cinemático", "neurálgicos", "Sincronizando satélite...", "Rastreo Satelital Activo". | varias |
| P15 | S3 | `/inicio` está declarado en dos rutas del mismo controlador. | `controllers/landing.py:12,19` |
| P16 | S4 | Etiquetas "人 RED DE TRANSPORTE 人", emojis como íconos, *mockup* de teléfono con datos inventados. | `landing_templates.xml`, `portal_templates.xml` |

### 2.2 Panel de administración (Odoo)

| # | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| A1 | S1 | Los incidentes de la tableta, incluido el SOS, **no aparecen en el mapa en vivo**. Solo llegan por push y quedan en *Administración de Buses > Incidentes*. Quien vigila el mapa no ve una emergencia. | `static/src/js/live_map.js`, `controllers/main.py` |
| A2 | S2 | El filtro "Alertas" mezcla buses con alertas y buses simplemente detenidos. "Detenidos" no muestra contador. "Sin señal" no tiene filtro. | `live_map.js:112`, `xml/live_map.xml` |
| A3 | S2 | Todo el texto del mapa está fijo en español en el JS/XML, sin `_t`: un usuario en inglés lo ve en español y no entra en `i18n/es.po`. | `live_map.js`, `live_map.xml` |
| A4 | S3 | El bucle `requestAnimationFrame` corre siempre, aunque no haya nada que mover, y llama a `setLatLng` en cada cuadro para cada bus. En un portátil de oficina gasta CPU y batería todo el día. Además, la curva *ease-out* frena al final de cada intervalo de 10 s y el bus parece avanzar a tirones. | `live_map.js:84,164-200` |
| A5 | S3 | `live_map.css` no tiene ni una regla `@media`: el cajón y la tarjeta tapan el mapa en pantallas de 1366 px o menos y en tabletas. | `css/live_map.css` |
| A6 | S3 | "Hace 340s": el tiempo desde la última sincronización no pasa a minutos. | `live_map.js:79` |
| A7 | S3 | No hay una vista de "qué requiere atención ahora". El menú raíz dice "Bus Tracking" (en inglés) y las quejas solo tienen lista, sin kanban por estado. | `views/menus.xml`, `views/bus_complaint_views.xml` |
| A8 | S4 | El login dice "Buen día" a cualquier hora y muestra "Manage Databases / Powered by Odoo" en inglés. | `views/login_templates.xml` |

### 2.3 Tableta del chofer

| # | Sev. | Hallazgo | Dónde |
|---|---|---|---|
| T1 | S1 | **La barra de cadencia es inventada y peligrosa.** El "Bus #02", los 8 minutos de intervalo y los ±3/5 min están fijos en el código. El estado sale de las alertas: con `long_stop` u `off_route` le dice al chofer **"RETRASADO · AGILIZA EL PASO"**. Pedir más velocidad a alguien que está fuera de ruta o detenido por un motivo real es un riesgo de seguridad. | `app/shift.tsx:62-72,198-203`, `src/ui/HeadwayBar.tsx` |
| T2 | S1 | El SOS se envía como `kind: 'accident'`, igual que un choque leve. En el panel no se distingue una emergencia de un incidente cualquiera, y el chofer nunca sabe si alguien lo vio. | `app/shift.tsx:142`, `models/bus_incident.py:3-8` |
| T3 | S2 | "Confirmar llegada" no hace nada en el servidor: pone una marca local durante 5 segundos. El chofer cree que registró algo. | `app/shift.tsx:153-157` |
| T4 | S2 | La pantalla completa de incidentes (`app/incident.tsx`: avería, accidente, otro, con nota) **no se puede abrir desde ninguna parte**: ningún `router.push('/incident')`. Solo quedan "tráfico" y SOS. | `app/incident.tsx`, `app/shift.tsx` |
| T5 | S2 | "GPS ACTIVO" depende de si respondió `/driver/state`, no del GPS. Con el GPS sin permiso o la cola llena, la pantalla sigue en verde. | `app/shift.tsx:185` |
| T6 | S2 | Al abrir, si la sesión tarda más de 2,5 s, `index.tsx` manda al login aunque haya un token guardado: con mala señal, el chofer tiene que volver a escribir la clave. | `app/index.tsx:10-27` |
| T7 | S2 | Casi todo el texto de la cabina está fijo en español (`'GPS ACTIVO'`, `'FINALIZAR TURNO'`, `'Tráfico Reportado'`) aunque existe `t()` con es/en/qu. | `app/shift.tsx`, `src/ui/*.tsx`, `app/incident.tsx:63` |
| T8 | S3 | Letra pequeña para leer a 1 m en un bus que vibra: 11 a 14 px en el estado del GPS, la línea, los botones auxiliares y los rieles de paradas. Los botones auxiliares miden 46 px (el plan dice 72). | `app/shift.tsx` (estilos), `StopAlertCard.tsx`, `IncidentActions.tsx` |
| T9 | S3 | Valores de relleno que parecen datos: `'L-01'`, `'UTA TRANSIT'`, `'BUS #01'`, `'CONDUCTOR AUTORIZADO'`. | `app/shift.tsx:168-173,236` |
| T10 | S3 | Dos sistemas visuales: login y selección claros (`colors`), cabina oscura (`cockpitColors`), y `_layout` pinta fondo claro; al pasar a la cabina hay un destello blanco. Una pantalla oscura bajo sol directo además se lee peor que una clara. | `src/ui/theme.ts`, `app/_layout.tsx` |
| T11 | S3 | Nada impide tocar la tableta en marcha: todos los botones responden a cualquier velocidad. | `app/shift.tsx` |
| T12 | S4 | Emojis en botones y alertas (🛰️, 🛑, ⚠️, 🚨). | `app/shift.tsx`, `src/ui/*.tsx` |

### 2.4 Documentación

| # | Sev. | Hallazgo |
|---|---|---|
| D1 | S2 | `PLAN.md` y `BITACORA.md` dan por hechas cosas que no existen o no se midieron: "ETA probabilísticos", "comprobante `#UTA-XXXX`", "headway semafórico", "contrastes WCAG AAA verificados", "touch targets mínimo 72 px". En un proyecto de gestión de calidad, la trazabilidad entre lo documentado y el código es parte de lo que se evalúa. |
| D2 | S3 | `ROADMAP.md` no existe. El roadmap vive en las tablas de `PLAN.md`. |
| D3 | S3 | `DISENO.md` describe una identidad (papel, línea de ruta, Bricolage, Atkinson) que ya no es la del código. |

## 3. Las tres personas y su recorrido

### 3.1 Pasajera: "¿Ya viene mi bus?"

**Quién.** Estudiante o docente en una parada de Ambato, con el celular en una mano, quizá bajo la lluvia, con datos limitados. Abre el enlace desde un grupo de WhatsApp o desde un QR en la parada. Tiene 20 segundos de paciencia.

**Hoy.** Portada de unos 8 MB → foto IA → banner con datos inventados → buscador que no busca → atajos que vacían la lista → tarjeta → página de ruta con un aviso de "estimaciones probabilísticas" → lista de paradas con minutos falsos → mapa con marcadores sin ícono.

**Objetivo.** Dos toques desde el enlace hasta saber dónde está el bus respecto de *su* parada.

1. `/` muestra **directamente las líneas** con su estado real ("2 buses ahora", "Sin buses en este momento"). Lo institucional va abajo y es breve.
2. En la ruta, la persona toca **su parada** una vez; la página la recuerda (`localStorage`) y la próxima vez abre ahí.
3. Para esa parada se muestra lo que el sistema sabe de verdad: "El bus 04 pasó por *Ingahurco* hace 3 min, va a 4 paradas de ti". Los minutos aproximados solo aparecen cuando haya un cálculo con datos reales (ver 27.4) y siempre como "unos 6 min".
4. Sin buses: decirlo, sin dramatismo, y ofrecer algo útil ("Revisa de nuevo en unos minutos" o, si hay horario cargado, "El próximo sale a las 13:00 desde Huachi").
5. Quejas: un formulario corto, con los tipos reales, que se puede llenar con el pulgar y que dice con honestidad qué pasa después.

### 3.2 Administrador o despachador: "¿Está todo bien ahora?"

**Quién.** Personal de Bienestar Universitario o de transporte, en un escritorio, con el panel abierto toda la jornada y otras tareas a la vez.

**Hoy.** El mapa muestra buses, pero un SOS no aparece en él, el filtro de alertas mezcla cosas, y las quejas y los incidentes están en menús distintos sin una cola común.

**Objetivo.** Que el mapa sea la mesa de trabajo y que lo urgente se imponga.

1. **Cola de atención** en el mapa, ordenada por gravedad: SOS → incidentes → alertas → quejas nuevas. Cada elemento con "Ver en el mapa" y "Atendido".
2. **SOS imposible de ignorar:** banda roja fija arriba, sonido y notificación del navegador, el bus parpadea en el mapa hasta que alguien lo marca como atendido; el chofer ve en la tableta que la central lo recibió.
3. Filtros honestos con contador: En ruta · Detenidos · Sin señal · Con alerta.
4. Quejas en kanban (Nueva → En revisión → Resuelta) con la ruta y el bus a la vista.
5. Todo el texto en español de Ecuador a través de `_t` y `es.po`.

### 3.3 Chofer: "Que la tableta no me distraiga"

**Quién.** Conductor con años de oficio, no necesariamente cómodo con la tecnología, con la tableta en el tablero a un metro, sol o noche, vibración y la atención en la vía.

**Hoy.** Pantalla cargada (reloj con segundos, barra de cadencia inventada, riel de paradas, alertas, cuatro botones), letra pequeña, un botón de llegada que no hace nada y una pantalla de incidentes que no se puede abrir.

**Objetivo.** Una mirada de medio segundo basta. Tocar solo detenido, salvo el SOS.

1. Arriba, enorme: **próxima parada** y cuántas faltan. Abajo, el mapa. Nada más compite.
2. Estado del GPS **verdadero** (permisos, último envío, cola) con tres estados en texto, color y forma: "Enviando", "Sin red, guardando", "GPS apagado".
3. Por encima de 10 km/h se bloquean los botones menos SOS y aparece "Detén el bus para usar la pantalla".
4. Tres acciones claras: **Avisar un problema** (abre la hoja de incidentes con tipos grandes), **SOS** (mantener 1,5 s) y **Terminar turno**.
5. Tras un SOS: "Enviado. Esperando a la central" → "La central vio tu alerta · 10:42".
6. Modo día (claro, alto contraste para sol directo) y modo noche (oscuro), automático según la hora con cambio manual.

## 4. Dirección de diseño: de dónde sale el alma

### 4.1 Idea central: la línea

Un bus es una línea con paradas. Esa forma se repite en las tres interfaces y es lo único "decorativo":

- **Portal:** cada ruta se dibuja como su propia línea con sus paradas reales (SVG generado desde `bus.route.stop`, no una ilustración genérica). En la ruta, la línea vertical de paradas con el bus colocado donde realmente está.
- **Panel:** la tarjeta del bus seleccionado muestra la misma línea en horizontal: dónde va y qué le falta.
- **Tableta:** la franja superior es la misma línea, con la próxima parada grande.

Así el sistema tiene un gesto propio, que viene del dominio y no de una plantilla.

### 4.2 Voz

Cercana, de tú, español de Ecuador, frases cortas. Nunca promete lo que el sistema no sabe.

| Antes | Después |
|---|---|
| Muévete seguro hacia el campus | ¿Dónde está tu bus? |
| Red Operativa: 8 buses en servicio regular | 3 buses en la vía ahora |
| Sincronizando satélite... | Buscando buses… |
| Rastreo Satelital Activo | En vivo · hace 4 s |
| Llega en 5–8 min | Está a 3 paradas de ti |
| ¡Reporte Registrado Exitosamente! | Recibimos tu mensaje |
| COMPROBANTE OFICIAL DE ATENCIÓN | Tu número es Q-00042. Guárdalo si quieres preguntar por él. |
| RETRASADO · AGILIZA EL PASO | *(se elimina)* |
| 🛑 FINALIZAR TURNO | Terminar turno |

Guía corta en `docs/diseno/DISENO.md`: tuteo, sin mayúsculas sostenidas, sin superlativos ("integral", "garantizado", "neurálgico"), sin "satelital", números siempre del sistema.

### 4.3 Paleta

Se recupera la base de `DISENO.md` y se integra el granate como color de marca, a la espera del manual de la UTA:

| Token | Valor | Uso |
|---|---|---|
| `--papel` | `#F1F3F2` | Fondo (gris verdoso frío, no crema) |
| `--tinta` | `#172025` | Texto, bordes fuertes |
| `--tinta-suave` | `#4A5A5F` | Texto secundario (≥ 7:1 sobre papel; se verifica en 27.1) |
| `--granate` | `#7A1A22` | Marca, botón principal, línea de ruta por defecto |
| `--senal` | `#FFC62B` | "Ahora / en vivo", foco, paradas encendidas: el amarillo de los letreros de parada |
| `--ok` / `--alerta` / `--peligro` | verde, ámbar, rojo con texto y forma | Estados (nunca solo color) |

Contraste objetivo: **AAA (7:1) en texto de cuerpo** del portal y de la tableta; AA (4,5:1) como mínimo en el panel. Cada par se calcula y se anota en `DISENO.md` (no se declara sin medir).

### 4.4 Tipografía

- **Bricolage Grotesque** (ya en `static/fonts/`) para títulos y números grandes.
- **Atkinson Hyperlegible** (ya en `static/fonts/`) para el cuerpo: pensada para baja visión, encaja con lectura en movimiento y al sol.
- En la tableta, las mismas dos con `expo-font`; números tabulares para la hora y las distancias.
- Escala portal: 16 / 18 / 22 / 28 / 40 px. Tableta: **mínimo 20 px** para todo texto visible en la cabina, 32 px para datos, 56–64 px para la próxima parada.

### 4.5 Fotos e imágenes

- **Ninguna imagen generada por IA** ni con la marca de la UTA sin autorización. Se eliminan las de `img/landing/`.
- Mientras no haya fotos propias, ninguna foto: la línea de la ruta y el mapa son la imagen.
- Cuando existan: fotos tomadas por el equipo en paradas reales de Ambato, con consentimiento de quienes salgan, en WebP/AVIF con `srcset` y menos de 120 KB cada una.

### 4.6 Movimiento

Una sola animación con significado por superficie; todo lo demás es inmediato.

- **Portal:** al cargar una ruta, la línea se dibuja una vez (≈600 ms, *ease-out*). Los buses se desplazan **linealmente** durante el intervalo de refresco (no *ease-out*, que frena y produce tirones). El punto de "en vivo" late lento (2 s) y se apaga si los datos tienen más de 30 s.
- **Panel:** igual para los buses; el bucle de animación se detiene cuando no hay movimiento pendiente o la pestaña está oculta. El SOS parpadea hasta que alguien lo atiende.
- **Tableta:** cambio de parada con un deslizamiento corto (200 ms, Reanimated en el hilo de UI); háptica solo al confirmar acciones; nada se mueve mientras se conduce salvo el mapa.
- Siempre: `prefers-reduced-motion` / `AccessibilityInfo.isReduceMotionEnabled` desactivan todo lo que no sea información.
- Sin *hover* que escale tarjetas, sin pulsos infinitos decorativos, sin *glassmorphism*.

## 5. Fases

Cada fase en su rama desde `develop`, commits pequeños con Conventional Commits, linter, pruebas y build antes del merge `--no-ff`, según `CLAUDE.md`.

### Fase 26. Verdad y fallos críticos — `fix/*` (prioridad máxima, antes de cualquier rediseño)

Varias ramas cortas, una por tema, para poder revertirlas por separado.

**`fix/portal-datos-reales`**
1. Quitar ETAs por índice (P1), el `or 8` (P2) y los textos fijos de frecuencia, accesibilidad y plazos (P3). Si no hay dato, no se muestra.
2. Quitar noticias, cifras, teléfono, correo y redes no entregados por la universidad (P4). Contacto y redes pasan a **Ajustes** (`res.config.settings`): si están vacíos, no se muestran.
3. Retirar las imágenes IA de `img/landing/` y el *mockup* de teléfono (P5, P16).
4. Botón del encabezado: "Ingreso del personal" (sin "Chofer") (P11).
5. Prueba: `test_portal.py` verifica que con cero buses no aparece ningún número y que la página de ruta no contiene "Llega en".

**`fix/quejas-tipos`**
1. Tarjetas de motivo con los cinco tipos reales del modelo, como `<input type="radio">` con `<label>` estilizadas (P6, P7). El texto sale de `kind_*` en `portal_i18n.py`.
2. Prueba: enviar cada tipo y comprobar que se guarda tal cual.

**`fix/portal-busqueda`**
1. Decidir: implementar la búsqueda por parada en `routes()` (filtrar rutas cuyas paradas contengan el texto, sin distinguir tildes) o quitar el buscador. Recomendación: implementarla; es lo que la persona quiere hacer.
2. Quitar los atajos por campus hasta que exista un dato de campus por parada (P8).
3. Reemplazar `fa-*` y clases de Bootstrap en las páginas públicas por SVG propios y CSS del módulo (P9).
4. Unificar `/inicio` (P15).

**`fix/tablet-cabina-segura`**
1. Eliminar `HeadwayBar` y su uso (T1). Se reintroduce solo si existe un cálculo real de intervalo en el servidor (fuera de este plan).
2. Agregar `sos` a `bus.incident.KINDS`, con prioridad alta y push inmediato; la tableta lo envía como `sos` (T2). Prueba en `test_driver_shift.py`.
3. Quitar "Confirmar llegada" o conectarlo a un endpoint real que registre `bus.stop.arrival` manual (T3). Recomendación: quitarlo; la llegada ya se detecta sola.
4. Botón "Avisar un problema" que abre `/incident` (T4).
5. `index.tsx`: si hay token guardado, ir a `/shift` o `/select` con datos en caché y reintentar `/me` en segundo plano; solo un 401 manda al login (T6). Prueba en `session.test.ts`.
6. Quitar valores de relleno (T9).

**`fix/docs-trazabilidad`**
1. Corregir en `PLAN.md` y `BITACORA.md` lo que no es cierto de las fases 23 a 25 (D1), con una entrada nueva que explique la corrección.

Criterio de aceptación: ningún número, plazo, nombre o dato de contacto en las tres interfaces que no salga de la base de datos o de Ajustes. Revisión manual con la tabla de hallazgos P1–P5, T1–T4 marcada.

### Fase 27. Sistema de diseño compartido — `chore/sistema-diseno`

1. **Tokens** (4.3 y 4.4) en `brand.css`, `primary_variables.scss` y `apps/conductor-tablet/src/ui/theme.ts`, con los mismos nombres. Un solo tema de tableta con variantes día y noche.
2. **Fuentes:** `@font-face` con `font-display: swap` para Bricolage y Atkinson en web; `expo-font` en la tableta.
3. **Componentes base del portal** en CSS sin dependencias: botón, campo, tarjeta de línea, línea de paradas (SVG), estado en vivo, aviso vacío, aviso de error.
4. **Accesibilidad base:** `:focus-visible` con anillo `--senal` de 3 px, `prefers-reduced-motion`, objetivos táctiles ≥ 48 px en portal y ≥ 72 px en cabina, sin `!important` salvo para sobrescribir Odoo.
5. **`docs/diseno/DISENO.md` reescrito**: idea de la línea, voz, paleta con contrastes **medidos**, tipografía, movimiento y la lista de "no hacer" (emojis como íconos, mayúsculas sostenidas, imágenes IA, datos de ejemplo, *glassmorphism*, pulsos decorativos).
6. **Calculadora de contraste** como prueba (`qa/` o Jest) que falla si un par de tokens baja del umbral.

### Fase 28. Portal público — `feature/portal-pasajero-v2`

Commits sugeridos: estructura → portada → lista de líneas → ruta y "mi parada" → quejas → gracias → idiomas → rendimiento.

1. **Portada `/`**: encabezado simple (marca, Líneas, Escribir a transporte, idioma). Debajo, directamente, el buscador de parada y las líneas con su línea dibujada y su estado real. Al final, un bloque corto de qué es el servicio y para quién, con texto aprobado por la universidad.
2. **Ruta `/rutas/<código>`**: en móvil, mapa arriba (40 % de la pantalla) y línea de paradas abajo; en escritorio, lado a lado. Tocar una parada la marca como "mi parada" (con `aria-pressed`) y la recuerda. Cada bus aparece **sobre la línea** en el tramo entre su última parada alcanzada y la siguiente.
   - Backend: ampliar `buses.json` con `last_stop_index` y `next_stop_index` (de `current_stop_id` y `bus.stop.arrival`), sin exponer nada más (mantiene la regla de la fase 10). Pruebas en `test_portal.py`.
3. **Estados**: cargando (esqueleto de la línea, no un *spinner*), sin buses, datos viejos (> 60 s: "Los datos tienen 2 min; puede que el bus haya avanzado"), error de red, límite de peticiones.
4. **Quejas `/quejas`**: una sola columna, cinco tipos como opciones grandes, ruta y bus opcionales, texto con contador, contacto opcional explicado en una línea. Aviso de privacidad visible, no escondido. Sin "3 pasos" artificiales.
5. **Gracias**: folio grande y copiable, qué pasa ahora (sin plazos que nadie haya comprometido), enlace a volver a su ruta.
6. **Idiomas**: todo texto a `portal_i18n.py` (es, en, borrador de kichwa); prueba que recorre las plantillas y falla si encuentra texto visible fuera del diccionario.
7. **Rendimiento**: presupuesto de **< 300 KB** en la primera carga de la portada sin mapa y **< 600 KB** con el mapa (sin contar teselas). Leaflet solo en la página de ruta. CSS crítico mínimo, imágenes en WebP/AVIF con `srcset` cuando las haya.
8. **Mapa**: marcador de bus propio (SVG con rumbo y nombre, no depende de Font Awesome), paradas con número, "mi parada" resaltada en `--senal`.

Criterios de aceptación:
- Lighthouse móvil: Rendimiento ≥ 90, Accesibilidad 100, Buenas prácticas ≥ 95.
- axe sin errores en `/`, `/rutas`, `/rutas/<código>`, `/quejas`, `/quejas/gracias`.
- Navegable solo con teclado y con TalkBack.
- Probado a 360, 390, 768 y 1280 px.
- Prueba con 5 personas (fase 31): 4 de 5 encuentran dónde está el bus respecto de su parada en menos de 30 s.

### Fase 29. Panel de operación — `feature/panel-operacion`

1. **Cola de atención** en el mapa (panel derecho que reemplaza la lista de flota cuando hay algo pendiente): SOS, incidentes, alertas abiertas, quejas nuevas, ordenados por gravedad y hora. Acción "Atendido" que guarda quién y cuándo.
   - Backend: `/bus_tracking/live` devuelve incidentes abiertos de las últimas horas; campos `acknowledged_by` y `acknowledged_at` en `bus.incident`; endpoint para marcar como atendido. Pruebas.
2. **SOS**: banda superior roja con el bus, la hora y la ubicación; sonido corto (con permiso) y notificación del navegador; el marcador parpadea hasta que se atiende. La tableta recibe el acuse en `/driver/state`.
3. **Filtros** con contador: En ruta · Detenidos · Sin señal · Con alerta (A2).
4. **Rendimiento del mapa** (A4): animar solo mientras haya interpolación pendiente; detener con `document.hidden`; interpolación lineal sobre el intervalo real entre posiciones.
5. **Responsive** (A5): cajón como hoja inferior en < 1200 px; tarjeta del bus compacta.
6. **Textos** con `_t` y `es.po` (A3); "hace 5 min" en lugar de "Hace 340s" (A6).
7. **Menús** (A7): raíz "Buses"; "Operación" (Mapa en vivo, Incidentes, Quejas), "Flota" (Buses, Rutas, Recorridos, Turnos, Choferes), "Reportes", "Configuración". Quejas e incidentes con kanban por estado.
8. **Login** (A8): saludo según la hora de Ecuador, foto propia o ninguna, enlaces de Odoo ocultos en producción.
9. **Tarjeta del bus**: chofer, línea, línea de paradas en horizontal, velocidad, última posición "hace X s", alertas, "Ver recorrido de 4 h".

Criterio de aceptación: con un SOS simulado, una persona que no lo espera lo nota en menos de 10 s con el panel abierto en otra pestaña (notificación) o en la misma (banda). Pruebas Odoo del acuse y del endpoint en vivo. CPU en reposo del mapa con 20 buses < 5 % en un portátil de oficina (medido con el perfilador del navegador).

### Fase 30. Tableta del chofer — `feature/tablet-cabina-v2`

1. **Un solo tema** con modo día (fondo claro, texto `#0E1418`, para sol directo) y modo noche (fondo `#0B0F14`, texto `#F2F5F4`), automático por hora con cambio manual en una esquina. `_layout` con el fondo del tema activo (T10).
2. **Pantalla de turno** en horizontal:
   - Franja superior: línea de la ruta con la parada actual y la siguiente; próxima parada a 56–64 px; "faltan N paradas".
   - Izquierda (≈ 40 %): bus y línea, estado del GPS real (T5), hora sin segundos, una alerta activa a la vez en lenguaje claro ("Vas a 58 km/h. El límite es 50.").
   - Derecha (≈ 60 %): mapa.
   - Abajo: **Avisar un problema** · **SOS (mantener)** · **Terminar turno**, todos ≥ 72 px de alto y con al menos 16 px entre ellos.
3. **Bloqueo en marcha** (T11): con velocidad > 10 km/h durante más de 5 s, los botones salvo SOS se atenúan y muestran "Detén el bus para usar la pantalla". Prueba unitaria del umbral.
4. **Hoja de incidentes**: cuatro tipos grandes con ícono y palabra, nota opcional por voz o teclado, enviar; si no hay red, "Guardado. Se enviará cuando haya señal" y contador visible de pendientes.
5. **SOS con acuse**: estados "Enviando…", "Enviado. Esperando a la central", "La central lo vio · 10:42" desde `/driver/state`.
6. **Textos** con `t()` en es/en/qu (T7); prueba que falla si hay texto visible fuera del diccionario.
7. **Accesibilidad**: escala mínima de 20 px (T8), etiquetas de accesibilidad en todo control, sin emojis (T12), íconos SVG (`react-native-svg`), respeta el tamaño de fuente del sistema hasta 1,3×.
8. **Login y selección**: escanear credencial primero; usuario y clave como alternativa; dirección del servidor escondida tras una pulsación larga en el logo (solo para soporte). Selección de bus y ruta en una sola pantalla con la confirmación integrada, sin diálogo extra.

Criterios de aceptación: `tsc`, `expo lint` y Jest en verde; prueba en tableta real (fase 22 sigue abierta) de pie a 1 m, al sol y de noche: la próxima parada se lee en menos de 1 s; ningún texto de la cabina por debajo de 20 px (prueba automática sobre los estilos).

### Fase 31. Validación con personas — `chore/validacion-ux`

1. **Guion de tareas** por persona (en `docs/calidad/`):
   - Pasajera: "Estás en la parada X. ¿Cuánto le falta al bus de la línea Y?"; "Deja una queja porque el bus no paró".
   - Administrador: "Hay un problema con un bus. Encuéntralo y márcalo como atendido"; "Mueve la queja Q-00012 a resuelta".
   - Chofer: "Inicia tu turno en el bus 04, línea Troncal"; "Avisa que hay tráfico"; "Termina el turno".
2. **Cinco personas por perfil**; medir éxito, tiempo y errores; anotar frases textuales.
3. **Automático**: Lighthouse y axe en CI para el portal; prueba de contraste de tokens; prueba de textos sin traducir.
4. **Registro**: hallazgos en `docs/calidad/05-registro-de-defectos.md` y una entrada en `BITACORA.md`.

## 6. Orden recomendado

1. **Fase 26** completa. Es corta y quita lo que hoy le resta credibilidad al proyecto en la defensa.
2. **Fase 27**, porque las tres siguientes dependen de los tokens y la guía.
3. **Fases 28, 29 y 30** en paralelo si hay más de una persona; si no, 30 → 29 → 28: la tableta tiene riesgos de seguridad, el panel tiene el SOS y el portal ya funciona.
4. **Fase 31** al cerrar cada una de las anteriores, no solo al final.

## 7. Lo que debe aportar la universidad

- Teléfono, correo y redes oficiales del servicio de transporte (o la decisión de no mostrarlos).
- Logo, colores y aprobación del nombre "Buses UTA" (ver `PERSONALIZACION.md`).
- Fotos propias o autorización para tomarlas, con consentimiento de quienes aparezcan.
- Texto institucional del bloque "qué es el servicio" y, si existe, el horario oficial y la frecuencia por línea.
- Cuál es el plazo real de respuesta a una queja, si se quiere mostrar uno.

## 8. Fuera de alcance

- Cálculo real de intervalo entre buses (*headway*) y ETA con modelo de tráfico. Se puede estudiar cuando haya semanas de datos reales.
- App nativa para pasajeros: la web cubre el caso.
- Rediseño de las vistas estándar de Odoo más allá de menús, kanban de quejas e incidentes y el tema.
