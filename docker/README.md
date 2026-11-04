# Entorno de Contenedores Docker

Definición de imágenes personalizadas para los servicios del sistema de rastreo de buses.

---

## Servicios Personalizados

### `docker/odoo/Dockerfile`
Extiende la imagen oficial `odoo:16.0` incorporando librerías Python requeridas por el módulo `bus_tracking`:
* **`phonenumbers`**: Normalización y validación de números celulares para choferes y denuncias de pasajeros.
* **`qrcode[pil]`**: Generación vectorial y rasterizada de credenciales QR para el carnet digital de choferes.
* **`requests`**: Cliente REST para la comunicación periódica con la API de Traccar.
* **`python-dateutil`** y **`pytz`**: Manejo estricto de zonas horarias locales (`America/Guayaquil`) e interpolación de marcas de tiempo UTC.

Para compilar la imagen localmente:
```bash
docker build -t rastreo-odoo:16.0 docker/odoo/
```
