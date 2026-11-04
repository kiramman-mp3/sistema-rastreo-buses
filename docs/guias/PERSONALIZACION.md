# Personalización para la Universidad Técnica de Ambato

El sistema está pensado para los buses de la Universidad Técnica de Ambato (UTA), en Ambato, Ecuador. Esta guía dice qué ya viene ajustado, qué se cambia desde `Configuración > Ajustes` y qué debe aportar la universidad.

## Ya ajustado para Ambato

| Tema | Valor por defecto |
|---|---|
| Zona horaria | `America/Guayaquil` (UTC-5, sin horario de verano). La fija el script de instalación para el administrador y la compañía; los reportes de actividad cortan los días en hora de Ecuador. |
| Idioma del panel | Español de Ecuador (`es_EC`), que usa el catálogo `i18n/es.po`. Inglés es el idioma base: todos los textos fuente están en inglés, el módulo mantiene `en_US` activo y cada usuario elige su idioma en Preferencias. |
| Centro del mapa | -1.2417, -78.6167 (centro aproximado de Ambato). Se usa cuando una ruta no tiene paradas ni buses. |
| Nombre mostrado | **Buses UTA** (provisional). |
| Límite de velocidad | 50 km/h (velocidad urbana). Verifica con la normativa de tránsito vigente y con las rutas reales, porque una ruta por una vía perimetral puede admitir más. |
| Idiomas del portal de pasajeros | Español (por defecto, aunque el navegador esté en otro idioma), inglés y kichwa. El visitante elige uno una vez y se recuerda. Glosario y límites del kichwa: `GLOSARIO-KICHWA.md`. |
| Idioma de la tableta | Español, inglés y kichwa. La primera vez usa el idioma del dispositivo (inglés o español); después, el que elige el chofer. |
| Frecuencia de las posiciones | La tableta envía el GPS cada 5 s; el mapa en vivo de Odoo se actualiza cada 4 s y el mapa público cada 5 s. |

## Se cambia desde Ajustes (sin programar)

`Bus Tracking > Configuration > Settings`:

- **Name shown to passengers**: aparece en las páginas públicas, en la pantalla de ingreso y en los títulos.
- **Map center (latitude, longitude)**: por ejemplo `-1.2417,-78.6167`.
- **Privacy policy link**: si se llena, el formulario de quejas muestra el enlace a la política de privacidad de la universidad.
- **Speed limit**, **No-signal alert after**, **Long-stop alert after**: umbrales de las alertas.
- **Erase complaint contact data after (days)**: 90 por defecto.
- **GPS address for the phones**: la dirección HTTPS a la que envían los celulares de los choferes.

En cada ruta, la casilla **Visible to passengers** decide si aparece en el portal público.

## Lo que debe aportar la universidad

El nombre, el logo y los colores institucionales son de la universidad. Este proyecto no incluye ninguno de ellos: usa un ícono genérico de bus y una paleta propia. Antes de publicar, conviene que quien administre la imagen institucional apruebe el nombre y entregue el logo y el manual de marca.

- **Logo**: el ícono de la marca está en `addons/bus_tracking/views/landing_templates.xml`, en la plantilla `brand_mark` (un SVG que se reutiliza en la landing, el portal y el ingreso). Se reemplaza por el SVG de la universidad.
- **Colores**: las variables `--bus-*` en `addons/bus_tracking/static/src/css/brand.css`, y las del panel en `static/src/scss/primary_variables.scss`.
- **Fotos**: las tres fotos actuales (`static/img/hero-paradero.jpg`, `lluvia-paradero.jpg`, `conductor.jpg`) son de Unsplash y **no son de Ambato**: la de la portada muestra un paradero de otra ciudad con un letrero en portugués. Se reemplazan por fotos propias de los buses y paradas de la universidad, con el mismo nombre de archivo (o cambiando la ruta en las plantillas). Quien aparezca en una foto debe haber dado su autorización.
- **Textos**: la landing está en `views/landing_templates.xml`; el portal y el formulario, en `controllers/portal_i18n.py` (español e inglés).
- **Política de privacidad**: el aviso del formulario es genérico. Antes de publicarlo, el área legal o el delegado de protección de datos de la universidad debe revisarlo frente a la Ley Orgánica de Protección de Datos Personales de Ecuador (yo no soy fuente legal). El enlace de **Privacy policy link** permite apuntar a la política oficial.

## Cosas a revisar con los datos reales de la universidad

- **Rutas y paradas**: se crean a mano en *Administración de Buses > Rutas*. La ruta se dibuja como línea recta entre paradas.
- **Horarios de servicio**: los buses probablemente no circulan de noche ni fines de semana. La alerta de "sin señal" solo vigila buses que reportaron en las últimas 6 horas, pero el control de salud `/bus_tracking/health` falla fuera de servicio; ajusta `Report as down after` o pausa ese monitor en esos horarios.
- **Frecuencia y celulares**: ver `docs/guias/GUIA-CHOFER.md` y la recomendación del plan.
- **Correo institucional**: el servidor de correo saliente de la universidad se configura en la fase 12.
