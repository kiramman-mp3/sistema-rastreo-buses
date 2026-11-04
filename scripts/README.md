# Scripts de Operación, Mantenimiento y Desarrollo

Colección de herramientas automatizadas para la administración del stack, despliegue en producción, respaldo de bases de datos y generación de datos para desarrollo local.

---

## Catálogo de Scripts

| Script | Entorno | Propósito | Uso básico |
|---|---|---|---|
| [`backup.sh`](backup.sh) | Producción / Dev | Genera un volcado SQL comprimido de las bases de Odoo y Traccar. | `./scripts/backup.sh` |
| [`restore.sh`](restore.sh) | Producción / Dev | Restaura un respaldo específico en la base de datos de PostgreSQL. | `./scripts/restore.sh backups/<archivo>.sql.gz` |
| [`init-prod.sh`](init-prod.sh) | Producción | Aprovisionamiento inicial del stack en servidor Linux (Azure VM). | `sudo ./scripts/init-prod.sh` |
| [`reset-prod.sh`](reset-prod.sh) | Producción | Reinicio seguro de producción (requiere confirmación y crea backup). | `sudo ./scripts/reset-prod.sh` |
| [`bootstrap-traccar.sh`](bootstrap-traccar.sh) | Producción / Dev | Configura usuario admin y parámetros API de Traccar de forma automatizada. | `./scripts/bootstrap-traccar.sh` |
| [`dev_seed.py`](dev_seed.py) | Desarrollo local | Puebla la base de datos con rutas de Ambato, paradas, buses y choferes. | `docker compose exec -T odoo odoo shell < dev_seed.py` |
| [`download-apk.ps1`](download-apk.ps1) | Host local (Win) | Sondea el estado del build de Android en EAS y descarga el APK a `dist-mobile/`. | `powershell -File scripts/download-apk.ps1` |

---

## Detalles de Ejecución

### 1. Respaldos automáticos (`backup.sh` y `restore.sh`)
* Los respaldos se guardan en el directorio `backups/` con fecha y hora (`buses_YYYY-MM-DD_HHMM.sql.gz`).
* Se recomienda programar `backup.sh` en el crontab del servidor de producción:
  ```bash
  0 2 * * * cd /home/azureuser/buses && ./scripts/backup.sh > /dev/null 2>&1
  ```

### 2. Semillas de datos locales (`dev_seed.py`)
Crea 4 líneas realistas de Ambato (Ingahurco – Huachi, Ficoa – Mercado Mayorista, Circuito Universitario y Querochaca) con coordenadas geográficas verídicas, paradas con radio de 30 metros y 2 conductores de prueba (`chofer1` y `chofer2`).

### 3. Descarga de binarios móviles (`download-apk.ps1`)
Permite dejar un proceso en segundo plano que consulta la API de Expo Application Services (EAS) cada 45 segundos hasta que el runner asignado finalice el APK, descargándolo automáticamente sin intervención manual.
