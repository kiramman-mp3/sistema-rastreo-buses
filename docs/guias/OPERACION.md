# Operación diaria

Lo que hay que hacer, y quién, para que el sistema funcione cuando hay buses y choferes reales. La instalación y las actualizaciones están en `docs/guias/PRODUCCION.md`; los datos personales, en `docs/diseno/PRIVACIDAD.md`.

Lo marcado como **propuesta** es un valor razonable para empezar: la universidad debe confirmarlo.

## 1. Qué versión corre

```bash
curl -s https://<DOMAIN>/bus_tracking/health
# {"status": "ok", "version": "16.0.1.3.0"}
```

`status` es `ok` (200) o `stale` (503, ningún bus ha reportado en el plazo de *Ajustes*); `version` es la del módulo instalado. Anótala en cada despliegue (sección 5). Con `-u bus_tracking` la versión sube sola si el módulo la cambió.

## 2. Quién vigila el SOS

Un SOS solo sirve si alguien lo ve. El sistema lo deja en la cola **Atención** del mapa del personal, avisa por notificación a los dispositivos suscritos y, cuando alguien lo marca como visto, la tableta del chofer muestra quién y a qué hora.

- **Responsable de turno** (propuesta): una persona nombrada por cada franja en que haya buses en ruta, con la cola de Atención abierta o las notificaciones activas en su celular.
- **Notificaciones**: cada responsable abre *Configuración > Notificaciones en este dispositivo* y las activa en su celular y en su PC. Mínimo dos dispositivos distintos, para que un celular sin batería no deje el SOS sin ver.
- **Qué hacer**: abrir el SOS, **marcarlo como visto** (el chofer lo ve en su pantalla) y llamar al chofer. Si no contesta, llamar a la central y avisar a la autoridad que corresponda.
- **Tiempo de respuesta** (propuesta): visto en menos de 5 minutos. Revisa una vez al mes cuántos SOS hubo y cuánto tardaron (la ficha guarda hora de envío y de acuse).
- **Fuera de servicio**: si nadie vigila (noche, feriado), dilo a los choferes: el SOS queda guardado pero nadie lo atiende hasta que alguien entre.

## 3. Monitoreo

**Disponibilidad.** Apunta un monitor externo (el que prefieras) a `https://<DOMAIN>/bus_tracking/health`:

- Cada 5 minutos, y que avise tras **2 fallos seguidos** (un 503 aislado puede ser un bus en un túnel).
- **Pausa el monitor fuera del horario de servicio.** Sin buses reportando, `health` responde 503 de noche y el monitor avisaría todas las noches. Alternativa: sube *Informar caída tras (minutos)* en Ajustes, o ponlo en 0 para desactivar el control.
- Avisa por correo o mensaje a más de una persona.

**Errores de las tabletas.** Una falla de la propia app llega al registro de Odoo (si hay señal) como una línea `Tablet error`, con chofer, bus, versión de la app, pantalla y mensaje:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --since 24h odoo | grep "Tablet error"
```

Revísalo cada día mientras la app sea nueva, y siempre que un chofer diga que "se cerró sola". Si el mismo error se repite en varios choferes, es un defecto de la app. En la tableta, *Estado del GPS* muestra la última falla de la app de los últimos 7 días.

**Lo que el monitor no ve.** Un bus que no envía no apaga `health` si otro sí envía; en el mapa del personal aparece como alerta de "sin señal".

## 4. Respaldos

- **Diario:** `scripts/backup.sh` por cron (ver `PRODUCCION.md`). Revisa `backups/backup.log` cada semana: una línea de error es un respaldo que no existe.
- **Copia fuera del servidor:** los respaldos viven en el mismo servidor; sin una copia externa, perder el servidor es perder todo. Programa la copia de `backups/` a otro lugar y comprueba cada mes que llegó.
- **Ensayo mensual de restauración** (hazlo y anótalo, un respaldo sin ensayo no se sabe si sirve):

  ```bash
  ./scripts/restore.sh backups/<fecha> --target-db buses_check
  ```

  Abre la base restaurada, mira que tenga buses y turnos recientes y bórrala. Anota la fecha y el resultado en la bitácora.

## 5. Versiones y reversión

Cada versión desplegada lleva una etiqueta de Git (`v<mayor>.<menor>`; `-preview` mientras no haya pasado una jornada real). Así se sabe qué corre y a qué volver.

**Publicar**

1. CI en verde en `develop` (incluye las pruebas de Odoo y el análisis de secretos).
2. `./scripts/backup.sh`.
3. Fusiona `develop` en `main` con `--no-ff` y etiqueta: `git tag -a v0.9-preview -m "..."` y `git push origin main --tags`.
4. Despliega siguiendo *Actualizar* de `PRODUCCION.md`.
5. Comprueba `/bus_tracking/health`: la `version` es la esperada.
6. Anota en la bitácora la etiqueta, la fecha y quién lo hizo.

**Volver atrás.** Odoo no baja la versión de un módulo: si el despliegue ejecutó una migración, la reversión es **restaurar el respaldo del paso 2** y volver a la etiqueta anterior.

```bash
git checkout v<anterior>
./scripts/restore.sh backups/<fecha-antes-del-despliegue> --yes
docker compose --env-file .env.prod -f docker-compose.prod.yml build odoo
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

Las posiciones que llegaron después del respaldo se pierden: decide con la universidad si compensa. Si el despliegue no migró nada, basta con volver a la etiqueta y reiniciar.

## 6. Secretos y claves

- Los secretos reales viven en `.env.prod` y `config/odoo.prod.conf` (no se versionan, tampoco se respaldan: guárdalos aparte).
- **Análisis de secretos en el CI** (`gitleaks`, `.gitleaks.toml`): lee el árbol y falla si encuentra una clave o contraseña escrita. Si falla: **cambia el secreto** (ver *Cambiar secretos* en `PRODUCCION.md`; borrarlo del historial no basta), quítalo del código y vuelve a probar.
- **La única clave permitida** es la de las teselas del mapa (CARTO): viaja en la dirección de cada tesela, así que cualquier navegador la ve; no es un secreto. Si la universidad tiene una clave propia, se pone en *Ajustes > Teselas del mapa*.
- Si un secreto salió en un repositorio público, hay que **rotarlo aunque se reescriba el historial**: la copia pública ya pudo haberse leído.

## 7. Mantenimiento

Una vez al mes (30 minutos):

| Qué | Cómo |
|---|---|
| Dependencias de la app | `cd apps/conductor-tablet && npm audit --omit=dev`, `npx expo-doctor` y `npx expo install --check`. Los avisos de `glob`, `minimatch` y `@expo/*` vienen de las herramientas de compilación de Expo y no viajan en la app; no se arreglan bajando Expo. |
| Imágenes de Docker | Fija y actualiza `ODOO_IMAGE`, `POSTGRES_IMAGE` y `TRACCAR_IMAGE` en `.env.prod`; prueba en desarrollo antes. |
| Versión de Odoo | El sistema usa Odoo 16 (y Python 3.9 de su imagen). Según el ciclo de soporte de Odoo, esa versión ya no recibe correcciones oficiales: confirma el estado actual y decide por escrito migrar o aceptar el riesgo. |
| Datos personales | Revisa los plazos de *Ajustes* contra `docs/diseno/PRIVACIDAD.md`. |
| Respaldo | Ensayo de restauración (sección 4). |

## 8. Pruebas en el equipo de desarrollo

La suite de Odoo se corre como el CI: con `docker run` y una base nueva, no con `docker compose run`. Con `compose run`, `TestHttp` falló de forma intermitente (`Session expired` tras `authenticate('admin')`, o el inicio sin redirección): 2 de 4 corridas sobre nuestra rama y 2 de 4 sobre `develop` sin ningún cambio nuestro. Con el comando del CI pasó 5 de 5.

Se probó qué diferencia lo causa, con el comando del CI y una sola variable cada vez: `--proxy-mode` (6 de 6 pasan) y montar el volumen de datos compartido con el Odoo de desarrollo (6 de 6 pasan). **Ninguna de las dos es la causa.** Quedan sin probar el resto del `odoo.conf` del compose y el montaje de `addons` con escritura. Mientras no se sepa, el veredicto de las pruebas es el del CI, y una falla aislada de `TestHttp` en `compose run` se repite con el comando del CI antes de darla por real. Comando exacto en `.github/workflows/ci.yml`, trabajo `odoo-tests`.
