# Guía para el chofer: tu celular como GPS del bus

Esta guía es para quien maneja. Tu celular enviará la posición del bus mientras dure tu turno, y nada más. No hace falta que hagas nada mientras manejas.

## Qué necesitas

- Un celular Android o iPhone con datos móviles.
- La aplicación gratuita **Traccar Client** (Google Play o App Store).
- Dos datos que te entrega el administrador: la **dirección del servidor** y el **identificador del dispositivo** de tu bus. Trata el identificador como una contraseña: no lo compartas ni lo publiques.

## Configurar la aplicación (una sola vez)

1. Abre Traccar Client.
2. En **Device identifier** escribe el identificador de tu bus.
3. En **Server URL** escribe la dirección completa que te dieron, empezando con `https://`.
4. Abre los ajustes y deja estos valores (son los recomendados por el proyecto):

| Ajuste | Valor |
|---|---|
| Location accuracy | Highest |
| Interval | 10 (segundos) |
| Angle | 30 |
| Distance | 0 |
| Stationary heartbeat | unos 60 segundos |
| Offline buffering | Activado |
| Wake lock (solo Android) | Activado |

Si tu celular se queda sin batería muy rápido, el administrador puede pedirte esta alternativa más suave: precisión **High** y distancia de **50** metros.

Si el administrador te da un código QR, puedes escanearlo con la cámara del celular para llenar la dirección y el identificador. Ese método no está documentado oficialmente por la aplicación y puede no funcionar en tu teléfono; si no abre la aplicación, escribe los datos a mano como arriba.

## Que no se detenga en segundo plano

Sin esto el celular puede dormir la aplicación y el bus desaparece del mapa.

- **Android:** en los ajustes del teléfono busca la aplicación Traccar Client, entra a Batería y elige **Sin restricciones**. Cada marca (Samsung, Xiaomi, Huawei, etc.) esconde estas opciones en lugares distintos; la guía [dontkillmyapp.com](https://dontkillmyapp.com) explica cómo hacerlo en cada una.
- **iPhone:** concede el permiso de ubicación **Siempre**. El seguimiento en segundo plano en iPhone es menos fiable que en Android; avisa al administrador si el bus deja de aparecer.
- Deja el celular **cargando** en el bus y con los datos móviles activados.

## Cada día

1. Al **iniciar tu turno**, abre la aplicación y activa **Service status**.
2. Comprueba que aparezca como activo.
3. Al **terminar tu turno**, desactívalo. Fuera de tu turno el celular no debe seguir enviando tu ubicación.

## Qué ve el sistema de ti

- La posición, el rumbo y la hora del bus mientras el servicio está activo.
- No ve tus mensajes, llamadas, fotos ni contactos, y no sigue tu celular cuando lo desactivas.
- Los pasajeros solo ven en un mapa el nombre del bus y por dónde va; no ven tu nombre ni la patente.

Tu empresa debe pedirte que aceptes este seguimiento por escrito antes de empezar.

## Si algo falla

| Problema | Qué hacer |
|---|---|
| El bus no aparece en el mapa | Revisa que el servicio esté activo, que tengas datos móviles, que la dirección empiece con `https://` y que el identificador esté bien escrito. |
| Aparece y desaparece | Quita la restricción de batería a la aplicación y deja el celular cargando. |
| La aplicación pide permisos | Acepta la ubicación (en iPhone, **Siempre**) y las notificaciones: Android las usa para mantener el servicio vivo. |
| Cambiaste de celular | Avisa al administrador; el identificador puede usarse en el nuevo teléfono, pero solo debe estar activo en uno. |

Los ajustes de esta guía provienen de la [documentación oficial de Traccar Client](https://www.traccar.org/client-configuration/). No se han probado todavía en un celular real con este sistema.
