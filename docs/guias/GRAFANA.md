# Grafana: los tableros dentro de Odoo

Grafana es el segundo tablero del proyecto (el primero está hecho dentro de Odoo, menú **Buses › Indicators › Odoo dashboard**). Se ve dentro de Odoo, en **Buses › Indicators › Grafana**,
con seis tableros: Resumen, Líneas, Puntualidad, Recorridos, Incidencias y Calidad del sistema. Es opcional: sin Grafana, el tablero de Odoo cubre todos los indicadores.

La evidencia y la interpretación de lo que muestra están en `docs/calidad/15-tablero-grafana.md`.

## 1. Cómo está armado

```
Base de Odoo (vistas kpi_*) ◄── rol grafana_reader (solo lectura) ── Grafana ◄── Caddy (grafana.<dominio>) ◄── iframe en Odoo
                                                                         ▲
                                         Odoo firma un token por usuario (rol Viewer) ┘
```

- **Los datos** salen de nueve vistas SQL de solo lectura, que crea el módulo (`models/bus_kpi_views.py`): `kpi_routes`, `kpi_route_stops`, `kpi_trips`, `kpi_trip_stops`, `kpi_alerts`,
  `kpi_positions`, `kpi_positions_daily`, `kpi_response` y `kpi_software`. No llevan chofer, usuario, placa ni texto escrito por una persona.
- **El rol `grafana_reader`** solo puede leer esas vistas (`addons/bus_tracking/data/grafana-role.sql`): sin acceso a las tablas de Odoo, sin escritura, con `statement_timeout` de 10 s y 5 conexiones.
- **Los tableros son código**: `scripts/gen_grafana_dashboards.py` los genera y quedan en `bi/grafana/dashboards/*.json`; Grafana los carga solos desde `bi/grafana/provisioning/` y no se pueden editar
  desde la pantalla. Para cambiar un tablero se cambia el generador y se vuelve a ejecutar.
- **El acceso** es solo desde Odoo. Quien tiene sesión en Odoo y pertenece al grupo de usuarios de buses recibe un token firmado (HS256) con rol fijo **Viewer**, sin nombre ni correo
  (`odoo-<id>`). Los choferes (usuarios de portal) no lo reciben. El secreto nunca sale del servidor. Grafana no tiene registro, ni acceso anónimo, ni tableros públicos, ni Explore.

> **Por qué el token dura 8 horas y no 5 minutos.** Se verificó con Grafana 11.6: con el inicio de sesión por JWT, Grafana no crea una cookie de sesión, sino que el navegador reenvía el token con
> **cada consulta** (también las de la actualización automática cada 30 s). Un token de 5 minutos dejaría el tablero sin datos pasado ese tiempo. Por eso dura una jornada (480 minutos por defecto,
> ajustable de 5 a 1440 en Ajustes) y la pantalla de Odoo pide uno nuevo antes de que venza (al 90 % de su vida). Lo que limita el daño de un token filtrado es el rol: es Viewer y la base solo deja
> leer las vistas `kpi_*`, que no tienen datos personales.

## 2. Desarrollo (local)

```bash
# 1. Las vistas las crea el módulo: instalarlo o actualizarlo (con Odoo parado si se actualiza).
# 2. El rol de solo lectura (una vez, y tras recrear la base):
GRAFANA_DB_PASSWORD=grafana-dev ODOO_DB=buses scripts/grafana-role.sh
# 3. Grafana (perfil "bi"; http://localhost:3000):
docker compose --profile bi up -d grafana
# 4. En Odoo, Ajustes › Buses › Grafana dashboards:
#      Grafana address = http://localhost:3000     Shared secret = dev-grafana-jwt-secret-change-me
python qa/grafana_smoke.py          # 19 comprobaciones: debe terminar con «19 of 19 checks passed»
```

Los valores de desarrollo (`grafana-dev`, `dev-grafana-jwt-secret-change-me`, administrador `admin`/`admin`) son solo para el equipo local. En producción los genera `scripts/init-prod.sh`.

## 3. Producción (Azure)

1. **DNS**: un registro para `GRAFANA_DOMAIN`, que **debe ser un subdominio del dominio de Odoo** (por ejemplo, `grafana.buses.uta.edu.ec` si Odoo está en `buses.uta.edu.ec`); así las cookies siguen
   siendo del mismo sitio dentro del iframe.
2. **`.env.prod`**: `COMPOSE_PROFILES=bi`, `GRAFANA_DOMAIN`, y las tres claves `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_DB_PASSWORD` y `GRAFANA_JWT_SECRET`
   (`scripts/init-prod.sh` las rellena al azar la primera vez; con una base externa que pide TLS, `GRAFANA_DB_SSLMODE=require`).
3. **Despliegue**: `scripts/init-prod.sh` actualiza el módulo (para crear las vistas), crea el rol de solo lectura, guarda la dirección y el secreto en Odoo y levanta Grafana.
   En un servidor ya instalado: actualizar el módulo, ejecutar `scripts/grafana-role.sh` y `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d grafana`.
   Con una **base externa** (Supabase) no hay `db` local: se ejecuta `grafana-role.sh` con `PSQL="psql postgres://<superusuario>@<host>/postgres"`.
4. **Caddy** publica `grafana.<dominio>` con HTTPS y la cabecera `frame-ancestors https://<dominio de Odoo>`, de modo que solo Odoo puede incrustarlo.
5. **Memoria**: Grafana tiene un límite de 512 MB; cabe en la VM actual.
6. **Comprobación**: `GRAFANA_URL=https://grafana.<dominio> GRAFANA_ADMIN_PASSWORD=… GRAFANA_JWT_SECRET=… python qa/grafana_smoke.py --frame-ancestor https://<dominio de Odoo>`.

## 4. Operación

| Quiero… | Hago… |
|---|---|
| Rotar el secreto | Cambiar `GRAFANA_JWT_SECRET` en `.env.prod` y el «Grafana shared secret» de Ajustes; reiniciar `grafana`. Los tokens anteriores dejan de valer. |
| Rotar la clave del rol | Cambiar `GRAFANA_DB_PASSWORD`, ejecutar `scripts/grafana-role.sh` y reiniciar `grafana`. |
| Cambiar cuánto dura la sesión | Ajustes › Grafana access lasts (minutes). |
| Cambiar un tablero | Editar `scripts/gen_grafana_dashboards.py`, ejecutarlo y confirmar los JSON; Grafana los recarga en 30 s. |
| Ver qué consulta hace un panel | En Grafana (con el administrador), menú del panel › Inspect › Query; o leer `rawSql` en el JSON. |
| Dejar de usar Grafana | Quitar `COMPOSE_PROFILES=bi` y vaciar la dirección en Ajustes: el menú muestra «Grafana is not set up yet». |

## 5. Si algo falla

| Síntoma | Causa probable |
|---|---|
| La pantalla dice «Grafana is not set up yet» | Falta la dirección o el secreto en Ajustes (el secreto necesita 16 caracteres como mínimo). |
| Los tableros salen vacíos o con «Sin datos» | El rol no existe o no tiene permisos: ejecutar `scripts/grafana-role.sh`; el módulo debe estar actualizado para que existan las vistas. |
| El recuadro queda en blanco | `frame-ancestors` no coincide con el dominio de Odoo, o `GRAFANA_DOMAIN` no es un subdominio del de Odoo. |
| Aparece la pantalla de inicio de sesión de Grafana | El secreto de Odoo y el `GRAFANA_JWT_SECRET` de Grafana son distintos, o el reloj del servidor está desfasado. |
| «db query error: permission denied» | El panel lee algo que no es una vista `kpi_*`; es la defensa funcionando. Cambiar la consulta. |

## 6. Lo que quedó fuera

- **Reglas de alerta de Grafana** (aviso al equipo cuando la puntualidad cae): era opcional en el plan y no se hizo; las alertas del sistema ya las generan las reglas de Odoo.
- **Minigráficos en las tarjetas del resumen**: en su lugar hay una tabla «Este periodo contra el anterior» y dos series diarias, porque Grafana calcula el minigráfico con la misma consulta que el valor
  y no permite que el valor sea el total del periodo y la línea sea por día.
- **Pareto con línea acumulada**: Grafana no mezcla barras y línea en un gráfico de barras; el Pareto se presenta como tabla ordenada con barra de porcentaje acumulado y el anillo por tipo.
- Los cuatro indicadores de software (S1 a S4) **no cambian con la línea ni el bus elegidos**: miden el sistema, no una línea.
