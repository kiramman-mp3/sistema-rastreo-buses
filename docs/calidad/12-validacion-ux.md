# 12. Validación de la experiencia (fase 31)

Cierre de las fases 26 a 30 de `docs/PLAN-UX.md`. Este documento separa lo que **se midió** (automático, repetible) de lo que **todavía no se hizo** (pruebas con personas), y deja el protocolo para hacerlo.

Fecha: 2026-11-02. Entorno: Docker local (Odoo 16 en el puerto 8070, base `buses` cargada con `scripts/dev_seed.py`), Chromium de Playwright, app de tableta en modo web (Expo).

## 1. Lo que se midió

| Verificación | Herramienta | Resultado |
|---|---|---|
| Pruebas del módulo Odoo | `odoo --test-enable --test-tags /bus_tracking` en base limpia | Ver §4 (corrida final) |
| Pruebas de la app de tableta | Jest | 56 de 56 |
| Tipos y linter de la tableta | `tsc --noEmit`, `expo lint --no-cache` | Sin errores |
| Contraste de los tokens | `python qa/contraste.py` | 20 de 20 pares cumplen; texto de cuerpo ≥ 7:1 en portal y tableta |
| Accesibilidad automática del portal | `python qa/accesibilidad.py` (axe-core 4.10, reglas WCAG 2.1 A y AA) | 0 problemas en 7 páginas × 2 tamaños (390 y 1440 px) |
| Revisión de diseño de la portada | `inspect.mjs` de la skill de diseño, a 1440, 768 y 390 px | 0 fallos, 1 advertencia (ver §2) |
| Capturas de las tres interfaces | `qa/capturas_ui.py`, `qa/capturas_tablet.py` | Evidencias en `evidencias/ux/` |

### Antes y después

| Interfaz | Antes | Después |
|---|---|---|
| Portada, móvil | `evidencias/ux/antes-portal-inicio-movil.jpg` | `evidencias/ux/despues-portal-inicio-movil.jpg` |
| Ruta, móvil | `evidencias/ux/antes-portal-ruta-movil.jpg` (minutos inventados por parada) | `evidencias/ux/despues-portal-ruta-movil.jpg`, `despues-portal-mi-parada-movil.jpg` |
| Mapa del panel | `evidencias/ux/antes-panel-mapa.jpg` (sin incidentes ni SOS) | `evidencias/ux/despues-panel-mapa.jpg`, `despues-panel-mapa-laptop.jpg` |
| Tableta | (no había forma de verla fuera de un dispositivo) | `despues-tableta-turno-dia.jpg`, `-noche`, `-en-marcha`, `-incidente`, `-seleccion`, `-login` |

### Comprobaciones de comportamiento hechas con el navegador

- **Mi parada:** en `/rutas/L1`, al tocar *Mercado Central* con el Bus 04 detenido en *Parque Cevallos*, la página dice "Bus 04 está a 1 parada de tu parada"; al recargar, la parada sigue elegida; con *Campus Huachi* (ya pasada por ambos buses) dice "Ningún bus con señal va hacia tu parada ahora".
- **SOS:** un SOS creado en un turno aparece como banda roja en el mapa del panel, encabeza la cola de *Atención* y el bus parpadea; al marcarlo como atendido, la tableta muestra quién lo vio y a qué hora (`/driver/state`, cubierto por prueba).
- **Bloqueo en marcha:** con una muestra de GPS a 42 km/h de más de 5 s, la tableta atenúa *Avisar un problema* y *Terminar turno* y solo deja el SOS; a 0 km/h se desbloquea (cubierto por `motion.test.ts`).
- **Idioma:** `/rutas?lang=en` cambia todo el texto visible; el `<html lang>` y el idioma marcado en el selector corresponden al elegido (cubierto por prueba).

## 2. Advertencia que se acepta

- **Sin video en la portada.** No existe un clip honesto de los buses de la UTA con licencia libre, y usar uno genérico iría contra la regla de no presentar como propio lo que no lo es. Cuando la universidad grabe uno, entra.

La primera corrida dio además 2 fallos (un título de 3 líneas en móvil y una tira de fotos cortada en el borde) y 3 advertencias (párrafo largo, sección con la mitad vacía, fila con desplazamiento lateral); se corrigieron y la segunda corrida quedó en 0 fallos y esta sola advertencia.

## 3. Lo que no se pudo hacer aquí

- **Pruebas con personas.** No se hicieron. El protocolo está en §5 y debe ejecutarse antes de dar el diseño por validado.
- **Tableta física.** La cabina se revisó en modo web a 1280 × 800. Falta: lectura a 1 m al sol y de noche, guantes o dedos húmedos, vibración real, TalkBack.
- **Panel con teclado y lector de pantalla.** axe no se corrió sobre el panel de Odoo (mediría también el código de Odoo) y tampoco se recorrió a mano con teclado: queda pendiente. Los botones solo con ícono del mapa tienen `aria-label`.
- **Lighthouse.** No se corrió; el presupuesto de peso se midió a mano: fotos WebP de 23 a 182 KB, cargadas en diferido.

## 4. Corrida final de pruebas

Se completa en la entrada de `docs/BITACORA.md` del 2026-11-02 con los números de la última corrida sobre `develop`.

## 5. Protocolo de pruebas con personas

Cinco personas por perfil. Sesiones individuales de 20 minutos, en el dispositivo real de cada perfil. Quien modera no ayuda; solo repite la tarea si se la piden.

### Pasajeros (teléfono propio, datos móviles)

| # | Tarea | Éxito si… | Medir |
|---|---|---|---|
| P1 | "Estás en el Mall de los Andes. ¿Cuánto le falta al bus de la línea Huachi – Ingahurco?" | Dice cuántas paradas le faltan, leyendo la página | Tiempo hasta responder (meta < 30 s), toques |
| P2 | "Mañana vuelves a la misma parada. Ábrela otra vez." | La parada aparece elegida sola | Si la nota |
| P3 | "El bus no paró en tu parada. Avísalo." | Envía el formulario y entiende el número de caso | Tiempo, errores, si deja contacto |
| P4 | "¿En qué idioma está la página? Cámbiala a inglés y vuelve." | Cambia y regresa | Tiempo |

### Personal de transporte (computador de oficina)

| # | Tarea | Éxito si… | Medir |
|---|---|---|---|
| A1 | Con el mapa abierto en otra pestaña, se dispara un SOS sin aviso. | Lo nota y lo marca como atendido | Tiempo hasta notarlo (meta < 10 s con notificaciones activadas) |
| A2 | "¿Qué buses no tienen señal ahora?" | Usa el filtro *Sin señal* | Tiempo |
| A3 | "Pasa el mensaje Q-0000X a *En revisión* y asígnatelo." | Lo hace desde el kanban | Errores |

### Choferes (tableta montada, bus detenido)

| # | Tarea | Éxito si… | Medir |
|---|---|---|---|
| C1 | "Inicia tu turno en el Bus 04, línea Huachi – Ingahurco." | Llega a la cabina | Tiempo, dudas |
| C2 | De pie a 1 m: "¿Cuál es la próxima parada?" (mirada de 1 s) | La dice | Acierto |
| C3 | "Avisa que hay tráfico." | Envía el aviso | Tiempo |
| C4 | "Si fuera una emergencia, ¿qué harías?" | Mantiene presionado el SOS sin ayuda | Acierto, tiempo |
| C5 | "Termina el turno." | Lo termina con la confirmación | Errores |

### Registro

Por cada sesión: perfil, dispositivo, éxito o fracaso por tarea, tiempo, frases textuales de la persona y problemas observados. Cada problema que se repita en dos o más personas entra al registro de defectos (`05-registro-de-defectos.md`) con severidad S1 a S4 (definidas en `docs/PLAN-UX.md`).
