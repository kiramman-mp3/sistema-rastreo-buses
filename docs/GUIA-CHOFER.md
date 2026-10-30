# Guía para el chofer: tableta del bus

Esta guía es para quien maneja. En el bus hay una tableta con la app **Buses UTA**. Con ella inicias sesión, eliges el bus y la ruta, y el GPS se envía solo mientras tu turno está abierto. No uses Traccar Client en el celular para este sistema.

## Qué necesitas

- Tableta Android **con GPS** (muchas tabletas solo Wi-Fi no tienen chip GNSS). Si la tableta no tiene GPS, usa un celular Android del chofer con la misma app.
- Datos móviles o Wi-Fi del bus.
- Usuario y contraseña de Odoo que te da el administrador (grupo *Driver*). No es el identificador de Traccar: ese dato no se escribe a mano.
- La app instalada como APK (no hace falta Play Store). Expo Go no sirve: el GPS de fondo necesita el APK de desarrollo o de producción.

## Instalar (el administrador lo hace una vez)

1. Instala el APK de `eas build --profile production --platform android` (o el de *development* para pruebas).
2. En el login se puede escribir la URL de Odoo o **Leer código QR** (Ajustes o ficha del bus en Odoo). El APK de producción ya trae `https://busesuta2340.eastus2.cloudapp.azure.com`.
3. En Ajustes de Android: ubicación precisa; batería de **Buses UTA** sin restricciones; pantalla encendida mientras carga. Guía por marca: [dontkillmyapp.com](https://dontkillmyapp.com).
4. Si el modelo lo permite, fija la app (modo aplicación fija / *screen pinning*) para que no se salga al escritorio.
5. Deja la tableta **cargando** en el bus.

## Cada día

1. Abre **Buses UTA** e inicia sesión con tu usuario.
2. Elige el bus (los ocupados salen deshabilitados) y la ruta. Concede ubicación *todo el tiempo* y la exclusión de ahorro de batería si Android la pide.
3. Comprueba **Estado del GPS**: permisos concedidos y que haya un último envío tras unos segundos.
4. Mientras manejas: las paradas avanzan solas; las alertas salen en el panel; un incidente se reporta con tipo y nota. Si no hay red, el incidente espera y se envía al volver.
5. Al terminar, pulsa **Terminar turno** y confirma. Ahí se corta el GPS. **Cerrar sesión** también detiene el GPS en esa tableta.

Si cierras la app sin terminar el turno, el servicio en primer plano sigue enviando posición hasta que alguien termine el turno o un gestor revoque la tableta.

## Qué ve el sistema de ti

- Posición, rumbo y hora del bus **solo con turno abierto**.
- Tu nombre en el mapa en vivo del personal (el pasajero no ve tu nombre ni la placa).
- Incidentes que reportes.

No ve mensajes, fotos ni contactos. Tu empresa debe pedirte que aceptes este seguimiento por escrito.

## Si algo falla

| Problema | Qué hacer |
|---|---|
| No entra | Usuario o clave; el administrador restablece la clave en Odoo. |
| El bus no aparece en el mapa | Estado del GPS, datos móviles, que el bus tenga GPS registrado en Odoo, y que el turno esté abierto. |
| Aparece y desaparece | Quita el ahorro de batería a la app y deja la tableta cargando. |
| La tableta no tiene GPS | Cámbiala o usa un celular Android con la misma app. |
| Cambiaste de tableta | Entra con tu usuario. Un gestor puede *Cerrar sesión de la tableta* si la anterior sigue con sesión. |

## Actualizar la app

El administrador construye un APK nuevo (`eas build --profile production --platform android`) y lo instala encima en cada tableta. No hay tienda. Confirma la versión en Ajustes de Android → Aplicaciones → Buses UTA.
