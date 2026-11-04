# Guía para el chofer: tableta del bus

Esta guía es para quien maneja. En el bus hay una tableta con la app **Buses UTA**. Con ella inicias sesión, eliges el bus y la ruta, y el GPS se envía solo mientras tu turno está abierto. El sistema opera exclusivamente con esta app oficial.

## Qué necesitas

- Dispositivo con GPS: Tableta o celular Android **con GPS** (muchas tabletas solo Wi-Fi no tienen chip GNSS), o iPhone con chip GNSS (modelos celulares). Si la tableta no tiene GPS, usa un teléfono celular con la misma app: la pantalla se adapta al dispositivo y funciona de pie o acostado.
- Datos móviles o Wi-Fi del bus.
- Tu **Credencial QR de Chofer** asignada por el administrador en Odoo (menú *Choferes*), o tu usuario y contraseña de chofer. Esa cuenta sólo sirve en la tableta: no abre el panel de Odoo. No es el identificador de Traccar: ese dato no se escribe a mano.
- La app instalada nativamente (APK en Android o build nativo en iOS). Expo Go no sirve: el GPS de fondo necesita la compilación nativa.

## Instalar (el administrador lo hace una vez)

1. Instala el APK de `eas build --profile production --platform android` (o build nativo de iOS para pruebas en iPhone).
2. El APK de producción ya trae configurado `https://busesuta2340.eastus2.cloudapp.azure.com`. Para iniciar sesión, el chofer simplemente pulsa **Escanear credencial QR** y apunta a su carnet de conductor.
3. En Ajustes del sistema:
   - **Android**: ubicación precisa (*Todo el tiempo*); batería de **Buses UTA** sin restricciones; pantalla encendida mientras carga. Guía por marca: [dontkillmyapp.com](https://dontkillmyapp.com).
   - **iOS (iPhone)**: Ajustes → Buses UTA → Ubicación: seleccionar **Siempre** y marcar **Ubicación exacta**. Habilitar **Actualización en segundo plano**. Durante el turno activo se muestra el indicador azul de ubicación en la barra de estado.
4. Si el modelo lo permite, fija la app (modo aplicación fija / *screen pinning*) para que no se salga al escritorio.
5. Deja la tableta **cargando** en el bus.

## Cada día

1. Abre **Buses UTA** y pulsa **Escanear credencial QR** para entrar en 1 segundo con tu carnet de chofer (o ingresa manualmente con usuario y clave).
2. Elige el bus (los que están en uso salen atenuados) y la línea, y pulsa **Iniciar turno**. Concede ubicación *todo el tiempo* y la exclusión de ahorro de batería si Android la pide.
3. Arriba a la derecha está el estado del GPS, en palabras: **GPS enviando**, **Sin red: N puntos guardados** (se envían solos al volver la señal), **Esperando señal del GPS** o **GPS sin permiso**. Tócalo para ver el detalle.
4. Mientras manejas, la pantalla muestra en grande la **próxima parada**, cuánto falta y la franja con las paradas siguientes. Las paradas avanzan solas: no hay que confirmar nada. Al llegar a la última parada empieza la vuelta y la franja se recorre al revés; cada vuelta empieza de cero.
5. **En marcha la pantalla se bloquea** (más de 10 km/h por 5 segundos): solo responde el **SOS**. Para avisar un problema o terminar el turno, detén el bus.
6. **Avisar un problema**: eliges tráfico, avería, accidente u otro, y una nota si quieres. Si no hay red (o el servidor falla), el aviso se guarda y sale solo, con la hora en que lo pulsaste.
7. **SOS**: mantén presionado un segundo y medio (así un bache no lo dispara). Sin red dice "SOS guardado"; en cuanto llega a la oficina cambia a "SOS enviado. Esperando a la central." y, cuando alguien lo ve, muestra quién y a qué hora. Un SOS sin atender no desaparece del mapa de la oficina.
8. El botón **Día / Noche** cambia los colores (el modo día se lee mejor al sol). Si lo dejas presionado, vuelve al cambio automático por la hora.
9. Al terminar, pulsa **Terminar turno** y confirma. Ahí se corta el GPS, **aunque no haya señal**: la app avisa a la oficina apenas vuelva la red (y si nunca vuelve, Odoo cierra el turno solo a las 14 horas). Antes de apagarse, el GPS intenta enviar los puntos guardados. **Cerrar sesión** también detiene el GPS en esa tableta.
10. Si usas letra grande en Android, la pantalla del turno se desplaza hacia abajo: los avisos importantes siempre están arriba y los botones **Avisar un problema**, **SOS** y **Terminar turno** quedan al final. La pantalla se puede girar: vale de pie o acostada, en celular o tableta.
11. Si abres la app sin señal, tu sesión sigue abierta y el GPS sigue guardando; la app vuelve a intentar sola.

Si cierras la app sin terminar el turno, el servicio en primer plano sigue enviando posición hasta que termines el turno. Si la oficina cierra tu turno o revoca la tableta, la app apaga el GPS en cuanto se entera (en unos segundos con señal) y vuelve a *Elegir bus*; Odoo, además, descarta cualquier posición de un bus sin turno abierto.

## Qué ve el sistema de ti

- Posición, rumbo y hora del bus **solo con turno abierto**.
- Tu nombre en el mapa en vivo del personal (el pasajero no ve tu nombre ni la placa).
- Incidentes que reportes.

No ve mensajes, fotos ni contactos. Tu empresa debe pedirte que aceptes este seguimiento por escrito.

## Si algo falla

| Problema | Qué hacer |
|---|---|
| No entra | Usuario o clave; el administrador restablece la clave en Odoo. "Demasiados intentos": espera un minuto. "El servidor tuvo un problema": avisa al administrador. |
| No puedo iniciar turno: "Falta la dirección del GPS" | El administrador debe llenar *Dirección del GPS para los teléfonos* en los Ajustes de Odoo. |
| El bus sale como "Sin GPS" | Ese bus no está registrado en Traccar: el administrador pulsa *Register GPS in Traccar* en su ficha. |
| El código QR pide confirmar otro servidor | No continúes salvo que el administrador te lo haya pedido: un QR falso podría llevarse tu clave. |
| El bus no aparece en el mapa | Estado del GPS, datos móviles, que el bus tenga GPS registrado en Odoo, y que el turno esté abierto. |
| Aparece y desaparece | Quita el ahorro de batería a la app y deja la tableta cargando. |
| La tableta no tiene GPS | Cámbiala o usa un celular Android con la misma app. |
| Cambiaste de tableta | Entra con tu usuario o tu credencial. Un gestor puede *Cerrar sesión de la tableta* si la anterior sigue con sesión: esa tableta se apaga y cierra el turno, pero tu credencial QR sigue valiendo. |
| GPS "Esperando señal" mucho rato | Abre el estado del GPS: la fila *Último error* dice por qué no se envía (sin red, Traccar rechaza el identificador, el servidor no responde). |
| En iPhone no envía ubicación estando detenido | Verifica que el permiso de ubicación esté en "Siempre" y "Actualización en 2.° plano" activada. La app cuenta con un latido periódico cada 10 s para mantener la posición activa incluso si Apple CoreLocation entra en reposo por falta de movimiento. |
| Perdiste la credencial QR | Pide al administrador que la revoque y genere otra en *Choferes*: la anterior deja de servir al instante. |

## Actualizar la app

El administrador construye un APK nuevo (`eas build --profile production --platform android`) y lo instala encima en cada tableta. No hay tienda. Confirma la versión en Ajustes de Android → Aplicaciones → Buses UTA.
