# Privacidad y datos personales

Qué datos trata el sistema, por qué, cuánto tiempo y cómo atender a quien pida ver o borrar los suyos. La página pública es `/privacidad` (se arma sola con los plazos de *Ajustes*, en `models/privacy_text.py`).

> **Esto describe lo que el sistema hace hoy. No es asesoría legal.** Antes de darlo por la política oficial, la universidad debe revisarlo con quien lleve la protección de datos personales (en Ecuador, la Ley Orgánica de Protección de Datos Personales). Si ya tiene una política, escribe su dirección en *Ajustes > Enlace a la política de privacidad*: el pie del sitio y el formulario de quejas apuntarán allí, y `/privacidad` seguirá disponible.

## Inventario

| Dato | De quién | Para qué | Dónde | Cuánto tiempo | Quién lo ve |
|---|---|---|---|---|---|
| Posición, hora y velocidad del bus | Choferes (indirecto: es del bus) | Mapa en vivo, alertas, historial | `bus.position`, Traccar | `bus_tracking.retention_days` (Ajustes: *Conservar posiciones (días)*, 30 por defecto; **0 = no se borra**) | Personal autorizado; el pasajero ve solo posición y línea, sin chofer ni placa |
| Turnos (inicio, fin, bus, ruta, chofer) | Choferes | Operación, auditoría | `bus.shift` | **No se borran solos** | Personal |
| Incidentes y SOS (tipo, nota, hora, posición, quién lo atendió) | Choferes | Atender emergencias | `bus.incident` | **No se borran solos** | Personal |
| Usuario, nombre, contraseña (con hash) | Choferes | Entrar a la app | `res.users` | Mientras exista el usuario | Administradores |
| Sesiones de la app | Choferes | Mantener la sesión | `bus.driver.token` (solo la huella) | 30 días; cron de purga | Nadie (solo huella) |
| Credencial QR (365 días) | Choferes | Iniciar sesión | `res.users` (solo administradores) | Hasta que se revoque | Administradores |
| Reporte (texto, línea, bus, tipo) | Pasajeros | Atender y mejorar el servicio | `bus.complaint` | **El texto no se borra solo** | Personal |
| Correo y teléfono del reporte (opcionales) | Pasajeros | Responder | `bus.complaint` | `bus_tracking.complaint_retention_days` días después de resolver (90 por defecto); cron diario | Personal |
| "Mi parada" | Pasajeros | Comodidad | Navegador (`localStorage`) | Hasta que se borre el navegador | Solo la persona |
| Idioma elegido | Pasajeros | Comodidad | Cookie `bus_lang` | 1 año | Solo la persona |
| Sesión técnica | Cualquier visita | Funcionamiento de Odoo | Cookie `session_id` | 7 días | — |
| Suscripción a notificaciones | Personal | Avisos de alertas | `bus.push.subscription` | Hasta que se desactive | Sistema |
| Imágenes de la cámara | Choferes | Solo leer el QR | **No se guardan** | — | — |

Terceros: el servidor donde se instala el sistema; el proveedor de teselas del mapa (por defecto CARTO con datos de OpenStreetMap, configurable en *Ajustes > Teselas del mapa*), que ve la IP y la zona que mira cada navegador o app; y el servicio de notificaciones del navegador del personal.

## Copias de seguridad

`scripts/backup.sh` conserva copias `BACKUP_KEEP_DAYS` días (14 por defecto). Un dato borrado puede seguir en las copias hasta entonces; la página pública lo dice.

## Atender un pedido de derechos

Responde por el contacto público de *Ajustes*. Para **pasajeros** (solo existen en `bus.complaint`):

1. Localiza el reporte por su folio (`Q-00001`) o por el correo o teléfono.
2. **Acceso:** copia lo que hay en la ficha.
3. **Borrado del contacto:** vacía *Correo* y *Teléfono* en la ficha (el cron lo hace solo a los N días). Si piden borrar el reporte entero, bórralo.

Para **choferes**:

1. **Acceso:** *Flota > Choferes* (datos de la cuenta) y *Turnos* e *Incidentes* filtrados por su nombre. Las posiciones son del bus, no de la persona: se obtienen por los turnos.
2. **Baja:** *Archivar* al usuario y *Revocar credencial*. El historial de turnos e incidentes se conserva por seguridad operativa; si hay que anonimizarlo, hazlo con una decisión escrita de la universidad.
3. Responde dentro del plazo que fije la normativa aplicable y deja constancia.

## Lo que el sistema hace para no tratar de más

- Las posiciones solo se guardan con un turno abierto (Odoo descarta las de un bus sin turno).
- El pasajero no ve choferes, placas ni velocidades.
- La tableta avisa al chofer, al ingresar y antes de iniciar turno, de que la oficina ve la posición mientras el turno esté abierto.
- Las contraseñas y las sesiones se guardan con hash, nunca en claro.

## Pendiente para la universidad

- Revisión legal del texto y decisión de la política oficial (y su enlace en *Ajustes*).
- Decidir plazos para turnos e incidentes (hoy no se borran solos) y poner `retention_days` en un valor distinto de 0 si no se quiere guardar para siempre.
- Informar a los choferes por escrito (contrato o reglamento interno) del rastreo durante el turno; el aviso en la app no sustituye eso.
- Registro de actividades de tratamiento y, si corresponde, delegado de protección de datos.
