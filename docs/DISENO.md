# Diseño de la landing, el login y el tema

Nota: el nombre que se ve en las páginas es configurable (por defecto "Buses UTA"); este documento se escribió cuando el nombre provisional era "Ruta Viva". El logo y las fotos deben reemplazarse por los de la universidad: ver `docs/PERSONALIZACION.md`.

## Idea

Un paradero tiene una forma reconocible: la línea de la ruta con sus paradas. Esa línea es el único gesto memorable de la landing: al cargar, un bus recorre la línea y va encendiendo las paradas por las que pasa. Todo lo demás es sobrio.

## Paleta

| Nombre | Valor | Uso |
|---|---|---|
| Papel | `#F1F3F2` | Fondo general |
| Tinta | `#172025` | Texto, marcos, barra del backend |
| Ruta | `#1E5560` | Línea de ruta, botones primarios del backend |
| Rojo bus | `#C23327` | Botón principal y el bus dibujado |
| Señal | `#FFC62B` | Paradas encendidas, sombra de la foto, línea bajo la barra |
| Lluvia | `#DCE3E3` | Superficies suaves |

Contrastes calculados: texto blanco sobre rojo bus ~5.5:1, texto gris (`#526368`) sobre papel ~5.6:1; ambos superan 4.5:1.

## Tipografía

- **Bricolage Grotesque** (variable, pesos 200 a 800) para títulos: tiene carácter humano sin perder legibilidad.
- **Atkinson Hyperlegible** (400 y 700) para el cuerpo: diseñada por el Braille Institute para ser muy legible. Líneas de hasta 58 caracteres.

## Decisiones frente a los defaults

- Sin tarjetas iguales con sombra: los tres públicos se cuentan con filas alternadas de foto y texto.
- Sin etiquetas en mayúsculas, sin flechas en los botones, sin numeración decorativa. La única numeración es la lista de cómo llega un bus a la pantalla, porque ahí sí hay una secuencia real; se dibuja con paradas en vez de números.
- Sin tono crema ni terracota: el papel es gris verdoso frío.
- Movimiento: una sola animación de carga. Respeta `prefers-reduced-motion`.
- Foco visible con anillo amarillo; la foto del hero tiene texto alternativo.

## Estructura

```
/ e /inicio   landing: encabezado, hero + ruta animada, quien espera, quien conduce,
              quien coordina (banda tinta), cómo llega un bus, cierre amarillo, pie
/web/login    panel de foto + formulario
/web          backend con la paleta nueva
```

## Archivos

- `static/src/css/brand.css`: variables de color y @font-face (compartido).
- `static/src/landing/landing.css`: estilos de la landing.
- `static/src/css/login.css`: login (cargado en `web.assets_frontend`).
- `static/src/scss/primary_variables.scss`, `static/src/css/backend.css`: tema del backend.
- `views/landing_templates.xml`, `views/login_templates.xml`, `controllers/landing.py`.

## Créditos de activos

| Activo | Fuente y licencia | Dónde se usa |
|---|---|---|
| Foto `hero-paradero.jpg`: mujer esperando en un paradero (Unsplash, `photo-1646174805377-ed0baac4c54e`) | [Unsplash](https://unsplash.com/photos/a-woman-in-a-red-shirt-is-standing-at-a-bus-stop-pY_SgNn4rus), licencia Unsplash | Hero |
| Foto `lluvia-paradero.jpg`: personas bajo un paradero con lluvia (`photo-1696545720052-b2c622c058b5`) | Unsplash, licencia Unsplash | Sección "quien espera" |
| Foto `conductor.jpg`: conductor en la ventana del bus (`photo-1631798262744-5c15818c2e92`) | Unsplash, licencia Unsplash | "Quien conduce" y login |
| Bricolage Grotesque | Fontsource, licencia OFL | Títulos |
| Atkinson Hyperlegible | Fontsource, licencia OFL | Cuerpo |
| Íconos del bus y de la marca | Dibujados para este proyecto (SVG en las plantillas) | Marca, ruta animada |

Los nombres de las personas fotografiadas y de quienes tomaron las fotos no se registraron; la licencia de Unsplash no exige atribución, pero es buena práctica agregarla. Pendiente: buscar los nombres de los fotógrafos en las páginas de cada foto.
