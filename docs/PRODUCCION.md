# Puesta en producción

Guía para instalar y operar el sistema en un servidor. Todo lo de esta página está en `docker-compose.prod.yml`, `proxy/Caddyfile` y `scripts/`.

## Requisitos

- Un servidor Linux con Docker y Docker Compose v2.
- Dos nombres DNS que apunten al servidor, por ejemplo `buses.tuempresa.cl` (Odoo) y `gps.tuempresa.cl` (a donde la tableta envía la posición OsmAnd).
- Puertos abiertos hacia internet: solo 80 y 443. Los celulares también entran por HTTPS (443).
- Postgres, Odoo, la API de Traccar y su puerto de dispositivos no se publican: solo el proxy los alcanza. El panel de Traccar no se expone.

### Base de datos: local o Supabase

- **Local (recomendado para empezar)**: deja `DB_HOST` vacío o en `db` en `.env.prod`. Postgres corre en el contenedor `db`, `init-prod.sh` crea las bases y `backup.sh`, `restore.sh` y `reset-prod.sh` funcionan tal cual.
- **Externa (Supabase u otra)**: pon `DB_HOST`, `DB_USER`, `TRACCAR_DATABASE_URL` y `TRACCAR_DB_USER` del proveedor (el ejemplo trae marcadores `TU_PROYECTO`). Las bases y los usuarios se crean en la consola del proveedor, los respaldos los hace el proveedor y `reset-prod.sh` se niega a correr.

## Instalación

```bash
cp .env.prod.example .env.prod      # o deja que el script lo cree
./scripts/init-prod.sh              # 1.ª ejecución: crea .env.prod con secretos aleatorios y se detiene
# edita DOMAIN, GPS_DOMAIN y ACME_EMAIL en .env.prod
./scripts/init-prod.sh              # 2.ª ejecución: levanta todo
```

La segunda ejecución:

1. Genera `config/odoo.prod.conf` con la contraseña maestra de Odoo guardada como hash, y la muestra una sola vez en pantalla. Guárdala en un gestor de contraseñas.
2. Crea la base de datos `traccar` y su usuario en Postgres.
3. Crea la base de Odoo con el módulo instalado y el idioma de `ODOO_LANG`, fija una contraseña aleatoria para el usuario `admin` (se muestra una sola vez) y carga el secreto del webhook y la URL de Traccar.
4. Levanta todos los servicios.
5. Crea el administrador de Traccar (contraseña aleatoria guardada en Odoo), cierra el registro abierto de Traccar y guarda en Odoo la **dirección del GPS** (`https://<GPS_DOMAIN>`). Sin esa dirección ningún chofer puede iniciar turno.

Es seguro repetirla: no sobrescribe `.env.prod`, la configuración ni las bases existentes.

Después, a mano:

1. Entra a `https://<DOMAIN>` como `admin` con la contraseña que mostró el script y cámbiala.
2. Crea las rutas y sus paradas, y un bus por cada tableta (o celular de respaldo).
3. En cada bus pulsa **Register GPS in Traccar**. El identificador OsmAnd lo recibe la app al **iniciar el turno**, no se teclea en la tableta. Sigue `docs/GUIA-CHOFER.md`.

No hace falta tocar el panel de Traccar: el script crea su cuenta de administrador (contraseña aleatoria guardada en Odoo), cierra el registro abierto, y Odoo crea los dispositivos por su API.

## Qué cambia respecto al entorno de desarrollo

| Tema | Producción |
|---|---|
| HTTPS | Caddy obtiene y renueva los certificados solo. Cabeceras HSTS, `nosniff`, `SAMEORIGIN` y `Referrer-Policy`. |
| Secretos | Aleatorios, en `.env.prod` (no se versiona). Contraseña maestra de Odoo guardada como hash. |
| Webhook | Traccar lo llama por la red interna de Docker con el secreto en la cabecera `X-Webhook-Secret`, para que no quede en los logs. El proxy devuelve 404 si alguien lo pide desde internet. |
| Base de datos de Odoo | `list_db = False`, `dbfilter` fijo, y `/web/database/*` bloqueado en el proxy. |
| Traccar | Usa Postgres (no la base H2 de pruebas), con un usuario propio. El panel solo se ve por el proxy. |
| Odoo | 2 workers, límites de memoria y de tiempo, código montado en solo lectura. |
| Logs | Rotación de 10 MB x 5 archivos por servicio. |
| Salud | Healthchecks en Postgres, Odoo y Traccar; `restart: unless-stopped`. |

## Respaldos

```bash
./scripts/backup.sh
```

Genera `backups/<fecha>/` con `odoo.dump`, `traccar.dump`, `filestore.tgz` y `SHA256SUMS`, y borra los respaldos con más de `BACKUP_KEEP_DAYS` días (14 por defecto). **No incluye** `.env.prod` ni `config/odoo.prod.conf`: guarda esos secretos aparte.

Programación diaria con cron (ajusta la ruta):

```
0 3 * * * cd /opt/rastreo-buses && ./scripts/backup.sh >> backups/backup.log 2>&1
```

**Los respaldos viven en el mismo servidor.** Si el servidor se pierde, se pierden con él. Copia `backups/` a otro lugar (otro servidor, almacenamiento en la nube) con la herramienta que ya uses; el proyecto no incluye ese paso.

### Comprobar que un respaldo sirve

```bash
./scripts/restore.sh backups/<fecha> --target-db buses_check
```

Restaura solo la base de Odoo con otro nombre, sin tocar producción. Revísala y bórrala cuando termines. Conviene hacerlo una vez al mes.

### Restaurar en producción

```bash
./scripts/restore.sh backups/<fecha> --yes
```

Es destructivo: detiene Odoo y Traccar, reemplaza las bases `odoo` y `traccar` y el filestore por los del respaldo, y vuelve a levantar todo. Sin `--yes` solo muestra qué haría.

## Notificaciones

Las alertas llegan por push (notificaciones web), que funcionan solo sobre HTTPS y necesitan que el servidor pueda salir a internet hacia los servicios push. Cada administrador abre *Configuración > Notificaciones en este dispositivo* y las activa en cada navegador o celular. No se usa correo.

## Monitoreo

`GET https://<DOMAIN>/bus_tracking/health` responde `{"status": "ok", "version": "<versión del módulo>"}` con código 200, o `{"status": "stale", "version": "..."}` con 503 cuando ningún bus ha reportado en los últimos minutos configurados en `Settings > Report as down after (minutes)` (10 por defecto; 0 desactiva el control). Si no hay ningún bus con Traccar vinculado, responde 200.

Apunta un servicio de monitoreo de disponibilidad (el que prefieras) a esa URL y que avise por correo o mensaje cuando falle. La operación diaria (quién vigila el SOS, el monitor, los errores de las tabletas, el ensayo de restauración, las etiquetas de versión y la reversión) está en `docs/OPERACION.md`; los datos personales y sus plazos, en `docs/PRIVACIDAD.md`. Ojo: si tus buses no circulan de noche, el endpoint devolverá 503 en ese horario; sube el plazo o pausa el monitor.

## Actualizar

1. `./scripts/backup.sh`
2. Trae el código nuevo y revisa el `docs/BITACORA.md`.
3. `docker compose --env-file .env.prod -f docker-compose.prod.yml pull db traccar proxy` y luego `docker compose --env-file .env.prod -f docker-compose.prod.yml build --pull odoo` (la imagen de Odoo se construye con `docker/odoo/Dockerfile` para incluir el componente de push)
4. `docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm odoo odoo -d <ODOO_DB> -u bus_tracking --stop-after-init`
5. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d`

Antes de la primera puesta en marcha real, fija las versiones de `ODOO_IMAGE` y `POSTGRES_IMAGE` en `.env.prod`. Traccar ya viene fijado en `traccar/traccar:6.16.0` (la versión con la que se verificó el reenvío); prueba una nueva en desarrollo antes de cambiar `TRACCAR_IMAGE`.

La versión 16.0.1.2.0 del módulo convierte a los choferes existentes en usuarios de portal y la 16.0.1.3.0 rellena la hora de los incidentes viejos; las dos corren solas en el paso 4.

## Empezar de cero

`scripts/reset-prod.sh` borra la base de Odoo, sus archivos y la base de Traccar, y vuelve a correr `init-prod.sh`. **Se pierde todo**: buses, rutas, turnos, posiciones y quejas. Antes de borrar pide escribir el nombre de la base (o `CONFIRM=<base>` sin terminal) y hace un respaldo con `backup.sh`. No lleva contraseñas escritas: las nuevas se generan y se muestran una vez. Sólo funciona con la base local.

`scripts/bootstrap-traccar.sh` sirve si Traccar se reinstaló aparte y Odoo perdió sus credenciales: crea otro administrador con contraseña aleatoria y la guarda en Odoo.

## Cambiar secretos

Si un secreto se filtra (por ejemplo, quedó en un commit), cámbialo; borrarlo del historial no basta.

| Secreto | Cómo se cambia |
|---|---|
| Contraseña del `admin` de Odoo | En Odoo: *Ajustes > Usuarios > Administrator > Cambiar contraseña*. Revisa en *Ajustes > Técnico > Registros* los accesos recientes. |
| Contraseña maestra de Odoo | Genera otro hash como lo hace `init-prod.sh` y reemplaza `admin_passwd` en `config/odoo.prod.conf`; reinicia Odoo. |
| `WEBHOOK_SECRET` | Cámbialo en `.env.prod` y en *Ajustes > Webhook secret* de Odoo al mismo valor; `docker compose ... up -d traccar odoo`. |
| `DB_PASSWORD` / `TRACCAR_DB_PASSWORD` | `ALTER ROLE ... PASSWORD` en Postgres, luego el mismo valor en `.env.prod`, y `up -d`. |
| Administrador de Traccar | `bootstrap-traccar.sh` no lo cambia si ya existe: cámbialo en el panel de Traccar por el proxy y guárdalo en los Ajustes de Odoo. |
| Credencial QR de un chofer | *Choferes > chofer > Revocar credencial* y *Generar credencial QR*. |

## Choferes: usuarios, tokens y tabletas

Cada chofer es un **usuario de portal** de Odoo (`base.group_portal` + `group_bus_driver`), creado desde *Flota > Choferes*: entra a la API de la tableta, pero no al panel de Odoo, ni ve contactos o usuarios. La contraseña la restablece un gestor en Odoo.

La tableta no usa API keys de Odoo. Tras `/bus_tracking/driver/login` guarda un token (en Odoo sólo su huella; `bus.driver.token`, 30 días, cron de purga) en el almacén seguro de Android. Un 401 en la app borra el token local.

La **credencial QR** (365 días) sólo sirve para pedir una sesión en `/bus_tracking/driver/login_badge`; no abre la API por sí sola y una sesión no puede renovarse por ese camino. Sólo los administradores la generan, la revocan o ven su enlace. La app sólo acepta servidores `https://` (o de la red local en desarrollo) y pide confirmar si un QR cambia el servidor.

El identificador OsmAnd (`traccar_unique_id`) **solo** viaja en `POST /bus_tracking/driver/shift/start`, con turno activo. `/me` no lo incluye. `bus_tracking.gps_url` debe ser `https://<GPS_DOMAIN>` (el mismo host que Caddy reenvía a Traccar `:5055`).

Si se pierde una tableta o hay que echar a alguien del turno: en Turnos, acción **Cerrar sesión de la tableta**. Revoca las sesiones (no la credencial QR) y cierra el turno; la app apaga el GPS en la siguiente consulta y Odoo descarta cualquier posición de ese bus mientras no haya otro turno. Si se perdió también la credencial, revócala en *Choferes*.

APK (sin Play Store):

```bash
cd apps/conductor-tablet
# La URL de Odoo se congela al construir:
# EXPO_PUBLIC_ODOO_URL=https://<DOMAIN> eas build --profile production --platform android
eas build --profile production --platform android
```

Instala el APK a mano en cada tableta. Para actualizar, otro build y se instala encima. El perfil `development` es el que admite GPS de fondo en pruebas; Expo Go no.

Checklist de la tableta: GPS real, ubicación todo el tiempo, sin ahorro de batería para la app, cargador, pantalla encendida, modo aplicación fija si el aparato lo tiene. Guía del chofer: `docs/GUIA-CHOFER.md`.

## Lo que se probó y lo que no

Probado en una máquina local con Docker, con los dominios `localhost` y `gps.localhost`:

- Instalación completa con `init-prod.sh` desde cero.
- HTTPS con el certificado interno de Caddy, cabeceras de seguridad, y 404 en `/bus_tracking/traccar/webhook` y `/web/database/*` desde el proxy.
- Traccar sobre Postgres, y el reenvío de posiciones a Odoo con el secreto en la cabecera (el log de Odoo no muestra el secreto).
- Creación automática de la cuenta de Traccar (el alta anónima posterior da HTTP 400), registro de un dispositivo desde Odoo, y posiciones por GET y por POST de formulario a través de `https://gps.localhost`. El puerto 5055 no está publicado en el servidor.
- Respaldo, verificación de checksums, restauración en una base paralela, y restauración destructiva completa (el bus, el usuario de Traccar y el contenido de un adjunto volvieron).
- Healthchecks en verde y el endpoint de salud (200 y 503).

**No se probó:**

- Certificados reales de Let's Encrypt: requiere un dominio público. Con `localhost` Caddy usa su autoridad interna.
- Un servidor Linux real: las pruebas se hicieron en Windows con Docker Desktop y Git Bash.
- Un GPS físico ni una jornada completa con chofer real (fase 22, criterio de campo).
- Carga con muchos buses.
- `eas build` de producción (hace falta cuenta Expo y firmar el APK).

## Limitaciones conocidas

- El identificador del dispositivo es la única credencial del protocolo OsmAnd: quien lo conozca puede enviar posiciones falsas de ese bus. Es aleatorio y solo lo ven los administradores; si se filtra, hay que registrar el bus de nuevo (hoy no hay un botón para rotarlo).
- Solo se admite el protocolo OsmAnd (la app de tableta). Los GPS físicos con otros protocolos exigirían abrir su puerto en el servidor y en la red de Azure, y esos no van cifrados.
- El login de choferes (`/bus_tracking/driver/login`) sí tiene límite de intentos; el login del panel de Odoo no.
- El usuario de base de datos de Odoo es superusuario de Postgres (el patrón de la imagen oficial).
- No hay límite de intentos de login, ni autenticación en dos pasos, ni bloqueo de IPs (por ejemplo con fail2ban).
- Los respaldos no se copian fuera del servidor automáticamente.
