# Demostración con Traccar Client desde un celular

Para la defensa del proyecto: mostrar el sistema con **un celular real que envía su posición con Traccar Client, por datos móviles, hasta el servidor público**, y verla aparecer en Odoo. Es una demostración;
**el cliente de operación sigue siendo la app de tableta** (Buses UTA), que inicia turno y recibe la dirección y el identificador sola (`docs/guias/GUIA-CHOFER.md`).

## 1. Qué hay que preparar

| Qué | Cómo |
|---|---|
| Un bus con su GPS registrado | Buses › Fleet › Buses › el bus › **Register GPS in Traccar**. Odoo crea el dispositivo con un identificador aleatorio (campo «Traccar Unique ID»; solo lo ven los gestores). |
| La dirección pública del GPS | En producción: `https://gps.<dominio>` (el `GPS_DOMAIN` de `.env.prod`). Caddy la recibe con HTTPS y la pasa a Traccar (puerto 5055, protocolo OsmAnd). |
| Un celular con **Traccar Client** | Android o iOS, de la tienda oficial (editor: Traccar Ltd). |
| Una ruta con paradas y, si se quiere mostrar puntualidad, un horario y un recorrido programado | Buses › Fleet › Routes y Schedules. |

## 2. Configurar Traccar Client

| Ajuste de la app | Valor |
|---|---|
| **Device identifier** | El «Traccar Unique ID» del bus (se copia del formulario del bus en Odoo). |
| **Server URL** | `https://gps.<dominio>` (sin puerto: HTTPS por el 443). |
| **Frequency** | `5` segundos. |
| **Location accuracy** | Alta (*High*). |
| **Distance / Angle** | `0` (que no filtre por distancia ni por giro). |
| Servicio | Activado (*Service status* en verde); conceder el permiso de ubicación «siempre» y desactivar el ahorro de batería para la app. |

## 3. Abrir el bus a la demostración

Sin un turno de chofer, Odoo **descarta** las posiciones de un bus (para que una tableta olvidada no lo siga dibujando). Para la demostración:

1. Abrir el bus en Odoo y pulsar **Start demo report** (solo gestores; el bus necesita su dispositivo GPS).
2. El bus muestra un aviso amarillo «Demo report: … until <hora>». **Solo ese bus** acepta posiciones sin turno, **por 8 horas**, y después vuelve a exigir turno solo. **Stop demo report** lo cierra antes.

> Esto reemplaza al ajuste global «Accept positions without a shift», que abre **todos** los buses y no caduca: queda solo para pruebas con `curl` en desarrollo.

## 4. Comprobar que llega

1. En el celular, Traccar Client en *Service status: started* y el icono de envío activo.
2. En el panel de Traccar (`https://traccar.<dominio>`): el dispositivo aparece **online** y con la última posición.
3. En Odoo: el bus pasa a **Connected** (formulario o lista), y en el **Live Map** se ve moverse.
4. Si el bus tiene un recorrido programado para esa hora (Buses › Operations › Scheduled trips), al pasar por las paradas se registran las llegadas con su retraso, y las reglas generan las alertas.

## 5. Guion y evidencias para la defensa

Orden sugerido (5 minutos): **(1)** el celular con Wi-Fi apagado y datos móviles; **(2)** abrir Traccar Client y mostrar la dirección `https://gps.<dominio>` y el intervalo de 5 s; **(3)** caminar o ir en auto
un tramo; **(4)** en una laptop, el mapa en vivo de Odoo con el bus moviéndose; **(5)** el recorrido terminado en Scheduled trips con sus paradas y retrasos; **(6)** el tablero con los indicadores.

| # | Evidencia | Cómo se obtiene | Estado |
|---|---|---|---|
| 1 | Captura de Traccar Client con la dirección `https://gps.<dominio>` y el identificador | Captura de pantalla del celular | Pendiente (requiere celular) |
| 2 | Captura del celular con **Wi-Fi apagado y datos móviles** | Barra de estado visible | Pendiente (requiere celular) |
| 3 | La posición apareciendo en el **mapa en vivo de Odoo** | Captura de pantalla de la laptop | Pendiente |
| 4 | El dispositivo **online** en el panel de Traccar | Captura | Pendiente |
| 5 | El **recorrido** en Scheduled trips con paradas, retrasos y estado | Captura del recorrido programado | Pendiente |
| 6 | Las llegadas a las paradas registradas, con fecha y hora, en Buses › Reports › Stop arrivals | Captura de la lista | Pendiente |
| 7 | Una prueba de que, **sin la marca**, el sistema descarta la posición | Prueba automática `TestDemoReport` (hecha); opcional, mostrarlo en vivo | Hecha |

Las evidencias 1 a 6 se completan el día de la prueba con el celular; se guardan en `docs/calidad/evidencias/traccar-client/` y se enlazan desde `docs/calidad/13-recorridos-de-prueba.md`.
Los 12 recorridos simulados (`docs/calidad/13-recorridos-de-prueba.md`) cubren los escenarios que no se pueden reproducir físicamente; la demostración física cubre la cadena real de punta a punta.

## 6. Por qué Azure con Caddy y no Cloudflare Tunnel

El proyecto pide que el servidor sea alcanzable desde Internet por los celulares sin exponer la red de la institución. Cloudflare Tunnel y la VM de Azure con Caddy resuelven lo mismo; se eligió la segunda:

| | Cloudflare Tunnel | Azure VM + Caddy (el proyecto) |
|---|---|---|
| Para qué sirve | Publicar un servidor que está **detrás de un NAT o un firewall** (una laptop o un servidor en el campus) sin abrir puertos | Servidor con **IP pública propia** |
| Cifrado | HTTPS en el borde de Cloudflare | HTTPS con certificados de Let's Encrypt que Caddy obtiene y renueva solo |
| Qué se expone | Solo lo que el túnel publica | Solo 80 y 443; Traccar (5055, 8082) y Odoo no se publican: Caddy los alcanza por la red interna de Docker; el administrador de bases de datos y el webhook se bloquean en el proxy |
| Dependencias | Cuenta y dominio en Cloudflare, el agente `cloudflared` | Un registro DNS por nombre; sin terceros en el camino de los datos |
| Datos | Pasan por la red de Cloudflare | Van del celular a la VM de la institución |
| Costo | Gratis en el plan básico | Ya existe la VM; sin costo adicional |

Equivalencia: en ambos casos el celular habla **HTTPS con un nombre público** y el servidor no queda abierto a la red de la institución. Con la VM de Azure ya con IP pública, el túnel no aporta nada más y añade un tercero.
Si el despliegue se moviera a un servidor dentro del campus, Cloudflare Tunnel sería la opción: bastaría apuntar `gps.<dominio>` al túnel; Traccar Client y Odoo no cambian.
Cómo se despliega y se endurece: `docs/guias/PRODUCCION.md`.

## 7. Si algo falla

| Síntoma | Causa probable |
|---|---|
| Traccar Client dice «Send failed» | La dirección está mal (sin `https://`, con puerto, o el DNS de `gps.<dominio>` aún no resuelve), o el celular no tiene datos. |
| El dispositivo aparece en Traccar pero el bus no se conecta en Odoo | Falta **Start demo report** (o expiró): sin turno ni marca, Odoo descarta la posición. |
| Traccar no muestra el dispositivo | El identificador del celular no es el «Traccar Unique ID» del bus (se distingue entre mayúsculas y minúsculas). |
| Las posiciones llegan pero no hay recorrido | No hay un recorrido programado para esa hora, o la ruta no tiene las paradas; ver `docs/calidad/02-estandares-y-reglas.md`, sección 1.1. |
| El celular deja de enviar con la pantalla apagada | Ahorro de batería: concederle el permiso de ubicación «siempre» y excluir la app del ahorro. |
