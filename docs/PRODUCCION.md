# Puesta en producción

Guía para instalar y operar el sistema en un servidor. Todo lo de esta página está en `docker-compose.prod.yml`, `proxy/Caddyfile` y `scripts/`.

## Requisitos

- Un servidor Linux con Docker y Docker Compose v2.
- Dos nombres DNS que apunten al servidor, por ejemplo `buses.tuempresa.cl` (Odoo) y `gps.tuempresa.cl` (a donde los celulares de los choferes envían su posición).
- Puertos abiertos hacia internet: solo 80 y 443. Los celulares también entran por HTTPS (443).
- Postgres, Odoo, la API de Traccar y su puerto de dispositivos no se publican: solo el proxy los alcanza. El panel de Traccar no se expone.

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

Es seguro repetirla: no sobrescribe `.env.prod`, la configuración ni las bases existentes.

Después, a mano:

1. Entra a `https://<DOMAIN>` como `admin` con la contraseña que mostró el script y cámbiala.
2. Crea las rutas y sus paradas, y un bus por cada celular de chofer.
3. En cada bus pulsa **Register GPS in Traccar**. Aparece la sección *Driver's phone* con el identificador y el QR; sigue `docs/GUIA-CHOFER.md` en el celular.

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

`GET https://<DOMAIN>/bus_tracking/health` responde `{"status": "ok"}` con código 200, o `{"status": "stale"}` con 503 cuando ningún bus ha reportado en los últimos minutos configurados en `Settings > Report as down after (minutes)` (10 por defecto; 0 desactiva el control). Si no hay ningún bus con Traccar vinculado, responde 200.

Apunta un servicio de monitoreo de disponibilidad (el que prefieras) a esa URL y que avise por correo o mensaje cuando falle. Ojo: si tus buses no circulan de noche, el endpoint devolverá 503 en ese horario; sube el plazo o pausa el monitor.

## Actualizar

1. `./scripts/backup.sh`
2. Trae el código nuevo y revisa el `docs/BITACORA.md`.
3. `docker compose --env-file .env.prod -f docker-compose.prod.yml pull db traccar proxy` y luego `docker compose --env-file .env.prod -f docker-compose.prod.yml build --pull odoo` (la imagen de Odoo se construye con `docker/odoo/Dockerfile` para incluir el componente de push)
4. `docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm odoo odoo -d <ODOO_DB> -u bus_tracking --stop-after-init`
5. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d`

Antes de la primera puesta en marcha real, fija las versiones de `ODOO_IMAGE`, `POSTGRES_IMAGE` y `TRACCAR_IMAGE` en `.env.prod` (por defecto Traccar usa `latest`), para que una actualización nunca ocurra por sorpresa.

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
- Un GPS físico.
- Carga con muchos buses.

## Limitaciones conocidas

- El identificador del dispositivo es la única credencial del protocolo OsmAnd: quien lo conozca puede enviar posiciones falsas de ese bus. Es aleatorio y solo lo ven los administradores; si se filtra, hay que registrar el bus de nuevo (hoy no hay un botón para rotarlo).
- Solo se admite el protocolo OsmAnd (la app Traccar Client). Los GPS físicos con otros protocolos exigirían abrir su puerto en el servidor y en la red de Azure, y esos no van cifrados.
- El usuario de base de datos de Odoo es superusuario de Postgres (el patrón de la imagen oficial).
- No hay límite de intentos de login, ni autenticación en dos pasos, ni bloqueo de IPs (por ejemplo con fail2ban).
- Los respaldos no se copian fuera del servidor automáticamente.
