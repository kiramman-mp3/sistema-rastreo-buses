# Guion de defensa: sistema de rastreo de buses de la UTA

Duración objetivo: **15 minutos de exposición y 5 de preguntas**. Cada sección dice cuánto dura, qué decir y qué mostrar. El texto en cursiva es lo que se dice en voz alta; el resto son notas para quien expone. Todas las cifras salen de `docs/calidad/` (ejecución del 28-oct-2026); si se vuelve a ejecutar `qa/ejecutar_todo.sh`, hay que actualizarlas.

Reparto sugerido si exponen dos personas: quien desarrolló presenta las secciones 1 a 5 y 9; quien hizo de QA presenta las secciones 6 a 8.

---

# PARTE A. Defensa del proyecto final (rúbrica de Gestión de Calidad)

Esta parte sigue la sección 8 del PDF «Presentación y defensa»: se demuestra el sistema **con la posición de un celular que usa Traccar Client**, se verifica el registro del vehículo, la asignación de una ruta, la consulta de posiciones,
el historial de recorridos y el cálculo de los indicadores, se muestra **un caso de cumplimiento y uno de incumplimiento** explicando las reglas, y se presentan el diseño, la calidad y las mejoras. La parte B (más abajo) es el guion general
del proyecto; esta parte es la que se ensaya para la rúbrica. Duración sugerida: **15 min de demostración y exposición, 5 de preguntas.**

## A.1. Antes de empezar (preparación, 10 min antes)

| Qué | Cómo |
|---|---|
| Servidor arriba y celular con datos móviles | `https://<dominio>` abre; el celular **sin Wi-Fi**; Traccar Client configurado (`docs/guias/DEMO-TRACCAR-CLIENT.md`) |
| El bus de la demostración | Buses › Flota › Vehículos de la flota › el bus: dispositivo GPS registrado; botón **Iniciar reporte de demostración** pulsado (dura 8 h) |
| Un recorrido programado para la hora de la defensa | Buses › Flota › Horarios: horario de la línea con ese bus; o Buses › Operación › Recorridos programados |
| Los 12 recorridos simulados | Buses › Configuración › Simular recorridos › «Crear el conjunto de demostración (12 recorridos)» (si hace falta); se identifican como simulados |
| Pantallas abiertas en pestañas | Mapa en vivo · Operación › Recorridos programados · Reportes › Tablero · Reportes › Descargar reporte (PDF) · `docs/calidad/16-sonarqube.md` |

## A.2. Orden de la demostración (≈ 9 min)

1. **Registro del vehículo (1 min).** Buses › Flota › Vehículos de la flota › el bus: placa, capacidad, ruta, dispositivo Traccar y el botón **Abrir en Fleet**: *«cada bus tiene su vehículo en Odoo Fleet, con la placa, el chofer y los asientos sincronizados»*.
2. **Asignación de una ruta (1 min).** Buses › Flota › Horarios: horario de la línea y botón **Asignar un bus** (por fecha y hora); un bus no puede tener dos recorridos a la misma hora.
3. **Consulta de posiciones (1 min).** Mapa en vivo con el celular moviéndose por datos móviles; en el celular, Traccar Client con la dirección `https://gps.<dominio>` y 5 s de intervalo.
4. **Caso de CUMPLIMIENTO (2 min).** El recorrido del celular o, si no hay tiempo físico, el recorrido simulado «L1 Puntual» (Recorridos programados): paradas **a tiempo**, retraso 0, distancia recorrida ≈ estimada, sin alertas. Se abre el recorrido y se leen las paradas con hora planificada y real.
5. **Caso de INCUMPLIMIENTO (2 min).** El recorrido simulado «L2 Con retraso» (4 paradas tarde, 12 min al final, alerta de llegada tarde) y «L3 Se detuvo antes de la última parada» (parada omitida, recorrido incompleto), con sus alertas.
6. **Historial e indicadores (2 min).** Reportes › Tablero: los 12 indicadores, comparación con el periodo anterior, pestañas Líneas, Puntualidad, Recorridos, Incidencias y Multas; pestaña **Fórmulas** para mostrar la consulta SQL de una cifra. Cerrar con Reportes › Descargar reporte: el mismo periodo en PDF.

> Si el celular falla el día de la defensa, los recorridos simulados (identificados como tales) cubren los dos casos y la cadena real queda demostrada con las capturas de la lista de evidencias de `DEMO-TRACCAR-CLIENT.md` §5.

## A.3. Las reglas que deciden el resultado (para explicar)

*«Cada parada de un recorrido tiene una hora planificada. Si el bus llega más de **5 minutos** después, la llegada es **tarde** y se genera la alerta; si llega más de 5 minutos antes, es **adelantada**. Si el recorrido termina y nunca estuvo en una parada, esa parada queda **omitida** y el recorrido **incompleto**.
Si pasan **10 minutos** de la hora de salida y el bus no ha empezado, hay una alerta de **salida tarde**. Si la duración real difiere de la planificada en más de **25 %**, se marca. La desviación se mide contra el trazado de la ruta. Todo eso son ajustes que el gestor puede cambiar.»*
Fuente: `docs/calidad/02-estandares-y-reglas.md` §1.1 (reglas R17 a R24) y las pruebas de caja negra en `tests/test_trip_rules.py` y `tests/test_boundaries.py`.

## A.4. Las 11 preguntas del PDF y dónde se responden

| Pregunta | Pantalla o consulta | Qué decir |
|---|---|---|
| ¿Dónde se encuentra actualmente el vehículo? | Mapa en vivo de Odoo y portal del pasajero | La última posición válida y su hora; el bus conectado se ve en verde |
| ¿Qué ruta está realizando? | Recorrido programado (Operación › Recorridos programados) y cabecera del turno en la tableta | El horario asigna ruta y bus por fecha y hora |
| ¿Qué paradas ha visitado? | Líneas del recorrido abierto (hora planificada y real por parada); tira de paradas de la tableta | Cada parada tiene estado: a tiempo, tarde, adelantada u omitida |
| ¿Está cumpliendo los horarios establecidos? | Puntualidad (T2) y paradas del recorrido | Porcentaje de llegadas dentro de la tolerancia |
| ¿Cuánto tiempo de retraso ha acumulado? | «Retraso al final» del recorrido y retraso promedio (T3) | El retraso que el recorrido fue acumulando hasta su última parada |
| ¿Se ha desviado de su ruta? | Alerta de desvío (Notificaciones › Desvíos de ruta) y desviación media (T5); el recorrido guarda la desviación media y máxima y el % de posiciones dentro del corredor | Distancia de las posiciones al trazado; más de 150 m es salirse |
| ¿Cuántos recorridos ha realizado? | Pestaña Recorridos del tablero y «Recorridos por día» | Hechos e incompletos por día y por línea |
| ¿Qué porcentaje de recorridos se ha cumplido correctamente? | Cumplimiento de ruta (T1) | Recorridos que llegaron a todas las paradas entre los cerrados |
| ¿Cuáles son las incidencias más frecuentes? | Pestaña Incidencias del tablero (Pareto) y el reporte en PDF | Pocos tipos explican la mayoría; en los datos de prueba, sin señal y llegada tarde |
| ¿Qué tan confiable es el sistema implementado? | Pestaña Calidad del sistema: S1 a S4 y `docs/calidad/17-rendimiento-por-volumen.md` | Integridad de posiciones, exactitud de la sincronización, tiempo de respuesta (p95 menor que 2 s hasta 1 000 000 de posiciones) y detección correcta (12 de 12) |
| ¿Qué mejoras se realizaron para incrementar la calidad? | `docs/calidad/18-mejora-continua-pdca.md` y `16-sonarqube.md` | 16 bugs y 12 vulnerabilidades de SonarQube a 0; 93 defectos registrados y 92 cerrados con su prueba (el abierto, DEF-079, es un aviso de Android 17); 639 + 197 pruebas |

## A.5. Calidad, diseño y mejoras (≈ 4 min)

- **Diseño** (`docs/arquitectura/ARQUITECTURA-Y-DATOS.md`): Traccar reenvía a Odoo; Odoo evalúa recorridos y reglas y calcula indicadores con SQL; un tablero y un reporte en PDF. *«El indicador es una consulta que se puede ejecutar: no hay números escritos a mano.»*
- **Pruebas** (`docs/calidad/03-plan-y-casos-de-prueba.md`, `19-matriz-de-trazabilidad.md`): caja negra y blanca, integración Traccar–Odoo con la auditoría de sincronización, rendimiento por volumen.
- **Calidad** (`docs/calidad/16-sonarqube.md`): Quality Gate aprobado, 0 bugs, 0 vulnerabilidades abiertas, cobertura 78,4 % en SonarQube (5-nov) y 94,3 % de Python con `coverage.py` (23-nov); **límites**: el JavaScript del módulo no tiene pruebas unitarias y Community no analiza inyecciones ni dependencias.
- **Mejora continua** (`18-mejora-continua-pdca.md`): Ishikawa, Pareto y cinco ciclos PDCA con comparación antes y después.

## A.6. Ensayo

Un ensayo completo consta de: **(1)** la preparación de A.1; **(2)** la demostración de A.2 con un caso de cumplimiento y uno de incumplimiento; **(3)** responder las 11 preguntas de A.4 sin mirar la tabla; **(4)** abrir la pestaña Fórmulas y explicar de dónde sale una cifra.
Registrar en `docs/academico/BITACORA.md` la fecha del ensayo, lo que falló y lo que se corrigió. **Pendiente: el ensayo con celular real.**

## A.7. Preguntas difíciles de esta parte

| Pregunta | Respuesta |
|---|---|
| ¿Por qué no Power BI? | El PDF ofrece dos alternativas y se eligió la A: el tablero dentro de Odoo, con la consulta de cada cifra a la vista. Grafana se usó como complemento y se retiró el 17-nov-2026 para no mantener dos tableros con las mismas cifras; lo reemplazó el reporte en PDF |
| ¿Los datos son reales? | Los recorridos de prueba son **simulados e identificados** (`simulated`), lo que el PDF permite; las posiciones de la demostración física son reales. Nunca se mezclan en silencio: el tablero tiene filtro «Real / Simulated / Both» |
| ¿Cómo sé que una cifra no es estática? | Pestaña Fórmulas: la consulta de cada indicador; agregar un recorrido o una alerta y volver a consultar |
| ¿Qué pasa si Traccar pierde una posición? | La auditoría diaria la detecta (S2 baja) y la consulta periódica de Odoo recupera la última; hay una prueba de integración de eso |
| ¿Qué no está bien todavía? | El JavaScript del módulo sin pruebas unitarias (0 % medido), kichwa sin revisión de una persona hablante, concurrencia sin medir, y la evidencia física con Traccar Client se completa con el celular |

---

# PARTE B. Guion general del proyecto

## 0. Apertura (30 s)

*"Buenos días. Les presentamos el sistema de rastreo de buses de la Universidad Técnica de Ambato: una aplicación que muestra en un mapa, en vivo, dónde está cada bus, avisa cuando algo anda mal y deja que el pasajero levante una queja. Vamos a explicar por qué se hizo, cómo funciona, qué calidad tiene medida con datos reales y qué nos falta todavía."*

Orden de la charla: problema, solución, arquitectura, proceso, calidad, estándares, límites, cierre.

---

## 1. El problema y por qué se hizo (1 min 30 s)

*"La universidad tiene 11 servicios de bus que salen hacia Izamba, Pelileo, Píllaro y la ruta troncal. Hoy el pasajero no sabe dónde está su bus y la administración no sabe si un bus excedió la velocidad, se detuvo mucho tiempo fuera de un paradero o se desvió de su ruta."*

*"El cliente, la universidad, pidió tres cosas: que el pasajero vea los buses de una ruta sin tener que crear cuenta, que pueda reportar un problema, y que el personal administrativo reciba avisos cuando algo falle."*

Puntos que justifican el proyecto:

- **Para el pasajero:** menos espera a ciegas, un canal para quejarse.
- **Para la administración:** control de velocidad, de señal, de paradas largas y de desvíos, con evidencia guardada.
- **Para la universidad:** usa software libre (Odoo y Traccar), sin pagar licencias, y los celulares de los choferes hacen de GPS, sin comprar equipos.

> Conviene añadir aquí una anécdota real de espera o de queja de pasajeros, si la tienen. Los documentos del proyecto no la registran, así que no se inventa.

---

## 2. Qué hace el sistema y demostración (2 min)

*"Les mostramos las tres caras del sistema."*

**Demostración en vivo (preparar antes, tener Docker arriba y un GPS simulado):**

1. **Portal del pasajero** (`/`, luego `/rutas`, luego una ruta): sin login, mapa con paradas y buses. Mostrar el selector de idioma (español, inglés y kichwa en borrador). *"El pasajero solo ve nombre del bus, posición, rumbo y estado. Nunca la placa, el chofer, la velocidad exacta ni el historial: es privacidad por diseño."*
2. **Queja** (`/quejas`): enviar una queja de prueba y mostrar el folio `Q-00001`. *"Tiene protección contra abuso: campo trampa, tiempo mínimo, límite por IP y borrado del contacto a los 90 días de resuelta."*
3. **Panel del administrador:** Mapa en vivo, Buses (con el QR para configurar el celular del chofer), Recorridos automáticos, Reportes (velocidad, sin señal, paradas largas, desvíos, llegadas) y Quejas.
4. **Simular un GPS:** `curl "http://localhost:5055/?id=<identificador>&lat=-1.2491&lon=-78.6168&speed=10"` y mostrar que el bus se mueve en el mapa. *"El celular real manda lo mismo que este comando."*

Plan B si falla la demostración: capturas de pantalla preparadas y el informe `docs/calidad/Informe_calidad_rastreo_buses.pdf`.

---

## 3. Cómo funciona (1 min 30 s)

*"La tableta instalada en el bus, con la app oficial Buses UTA desarrollada para los choferes, manda su posición en protocolo OsmAnd a Traccar. Traccar la reenvía por webhook a Odoo, donde está nuestro módulo `bus_tracking`. Como respaldo, un cron consulta a Traccar cada minuto, por si el webhook falla."*

```
Tableta Chofer (App Buses UTA) --> Traccar --webhook--> Odoo (bus_tracking) --> mapa, alertas, portal
                                ^                        |
                                +---- cron cada 1 min ---+
```

Puntos a destacar:

- **Webhook protegido** con un secreto en una cabecera (no en la URL, porque el servidor registra las URL: era el defecto DEF-003, ya cerrado).
- **Sin duplicados:** una posición es única por bus y hora GPS. Probado con 20 envíos iguales a la vez: se guarda 1.
- **Alertas** con umbrales configurables: exceso de velocidad (50 km/h urbano), bus sin señal, parada larga y desvío de ruta. Llegan por push a los administradores suscritos.
- **Producción:** Caddy con HTTPS, secretos aleatorios, respaldos con restauración probada, y `/bus_tracking/health` para monitoreo.

---

## 4. Decisiones y por qué esas tecnologías (1 min 30 s)

| Decisión | Por qué |
|---|---|
| **Odoo 16** | Ya trae usuarios, permisos, vistas, tareas programadas y traducción; no hubo que construir un panel desde cero. |
| **Traccar** | Servidor de GPS de código abierto que ya entiende decenas de protocolos y de dispositivos. |
| **Celular del chofer como GPS** | Decisión del cliente: cero costo de hardware. A cambio hay que cuidar batería, plan de datos y consentimiento del chofer. |
| **Portal sin login** | Decisión del cliente: el pasajero solo mira y se queja; menos fricción y menos datos personales. |
| **Docker Compose** | Instalación repetible (`docker compose up`); probada desde cero. |
| **Azure con máquina virtual Linux** | Decisión original del cliente: Traccar recibe conexiones de dispositivos que no encajan en servicios de aplicación web. **No se usó:** el 21-nov-2026 la demostración se desplegó en un homelab con Docker Compose detrás de un túnel de Cloudflare, con despliegue continuo desde `main` (`docs/guias/DESPLIEGUE-HOMELAB.md`). |
| **Español, inglés y kichwa** | Decisión del cliente. Odoo 16 no trae kichwa; se hizo en el portal con un diccionario propio, marcado como borrador hasta que lo revise una persona hablante. |

*"Todas estas decisiones se tomaron con el cliente en la fase 0 y están en `docs/arquitectura/PLAN.md`."*

---

## 5. Cómo se trabajó: proceso y trazabilidad (1 min)

*"Seguimos un flujo Git con `main`, `develop` y ramas `feature/*`, `fix/*`, `refactor/*` y `chore/*`. Los commits son pequeños y siguen Conventional Commits, así que cualquiera se puede revertir."*

- Cada sesión de trabajo queda en `docs/academico/BITACORA.md`, y el avance por fases en `docs/arquitectura/PLAN.md`.
- **Decidimos recortar el alcance** el 27-oct para quedarnos con lo que se pueda defender: se eliminaron el roster oficial, los trazados por calle, el correo y los viajes con puntualidad. *"Preferimos pocas funciones bien probadas a muchas a medias."*
- Un ejemplo de que el proceso funciona: al simplificar, una prueba atrapó un error real (un bus sin ruta rompía el cálculo de desvío, DEF-006) y quedó una prueba que lo protege.

---

## 6. Qué calidad tiene: la política y las pruebas (3 min)

*"Para decir que algo tiene calidad hay que medirlo. Definimos una política de siete reglas y la verificamos con tres tipos de prueba."*

**Las siete reglas** (`docs/calidad/01-politica-y-alcance.md`):

1. Criterio de despliegue: nada pasa a `main` sin pruebas al 100 %.
2. Validación en el modelo o el controlador, nunca solo en la vista.
3. Integridad de las transacciones.
4. Los defectos hallados bloquean las funciones nuevas.
5. Todo defecto corregido deja una prueba de regresión.
6. Privacidad por diseño.
7. Trazabilidad (Git y bitácora).

**Las pruebas:**

| Qué | Cantidad | Resultado |
|---|---|---|
| Pruebas automatizadas de Odoo | 639 | 0 fallos |
| Pruebas de la app de tableta (Jest) | 197 | 0 fallos |
| Suite en vivo (14 funcionales, 25 de error, 7 de rendimiento, 1 de usabilidad) | 47 | 0 fallos |
| Auditoría aleatoria con semilla fija | 1.000 peticiones | 0 fallos |
| Cobertura de Python (sentencias y ramas) | 4.285 sentencias | **94,3 %** |
| Cobertura de la tableta (sentencias) | 916 sentencias | 89,2 % |

Cifras de la corrida del 23-nov-2026 (`qa/ejecutar_todo.py`). La evaluación del 28-oct había dado 3 fallos en la suite y 57 en la auditoría, todos del webhook, ya corregidos.

**Rendimiento** (servidor de un solo proceso):

- Uso normal: **0,030 s** en promedio por petición.
- Con 20 hilos simultáneos: p95 de 1,7 s y **47,8 peticiones por segundo**. Para 100 buses reportando cada 10 segundos se necesitan 10: casi cinco veces el margen.
- **Integridad concurrente:** 20 envíos idénticos a la vez guardan 1; 60 de 60 envíos de un mismo bus se guardan.
- **Volumen:** el tablero responde en 704 ms con 50 000 recorridos (`17-rendimiento-por-volumen.md`).

**Cuadro de mando:** se cumplen las 12 metas (`04-resultados-y-metricas.md`). El 28-oct se cumplían 8: las que fallaban (respuestas 5xx, posiciones imposibles, defectos cerrados y rutas HTTP sin probar) se cerraron con los defectos DEF-008 a DEF-010 y con pruebas nuevas.

*"Además hicimos análisis de causa: tres diagramas de Pareto y dos de Ishikawa con los cinco porqués, y una lluvia de ideas de 94 ideas categorizadas."*

---

## 7. Qué estándares cumple (1 min 30 s)

*"Nos autoevaluamos contra cuatro estándares. Es una autoevaluación del equipo, no una certificación, y lo decimos así en el documento."*

| Estándar | Resultado |
|---|---|
| **ISO/IEC 25010** (calidad del producto) | De 31 subcaracterísticas: 7 cumple, 19 parcial, 5 no evaluado. Fuerte en instalabilidad, modularidad, modificabilidad, capacidad de ser probado, recuperación y protección ante errores del usuario. |
| **ISO/IEC/IEEE 12207** (ciclo de vida) | De 30 procesos: 13 cumple, 14 parcial, 3 no aplica. |
| **CMMI v1.3** | **Nivel 2 en consolidación:** 4 de las 6 áreas del nivel 2 se cumplen (planificación, seguimiento, medición y configuración); REQM y PPQA son parciales. |
| **ISO/IEC/IEEE 29119-3** (documentación de pruebas) | Los nueve documentos de la norma tienen su equivalente en `docs/calidad/`. |

*"Nos quedamos en 'parcial' en muchas casillas porque no tenemos usuarios reales ni un celular real probado. Preferimos decirlo antes de que nos lo pregunten."*

---

## 8. Defectos abiertos y limitaciones (1 min 30 s)

*"Hay 93 defectos registrados, cada uno con su causa raíz y la prueba que lo protege. 92 están cerrados. El abierto, DEF-079, es un aviso de Android 17 en una librería de Expo que no detiene el GPS."*

| Defectos | De dónde salieron | Estado |
|---|---|---|
| DEF-008 a DEF-010 | Evaluación del 28-oct: posiciones imposibles y HTTP 500 en el webhook | Cerrados |
| DEF-011 a DEF-026 | Primera auditoría (2-nov): credencial QR, choferes con acceso al panel, GPS de un bus sin turno | Cerrados |
| DEF-051 a DEF-062 | Segunda auditoría (17-nov): XSS en el portal, colas de la tableta, permisos de choferes | Cerrados |
| DEF-091 y DEF-092 | Revisión de seguridad (23-nov): un chofer podía llamar por RPC al cliente de Traccar y a los indicadores; los choferes de demostración tenían su usuario como contraseña | Cerrados (13 pruebas nuevas; 8 fallaban antes) |
| DEF-079 | Aviso de Android 17 en `expo-task-manager` | **Abierto** (no afecta el envío del GPS) |

- **Causa raíz que se repite:** reglas que se cumplían sólo en un lado: el botón oculto en la vista pero el método abierto. La primera auditoría lo encontró en la credencial QR y la revisión del 23-nov en los métodos que Odoo deja llamar por RPC. Ahora cada regla se comprueba en el servidor y tiene una prueba que llama como un chofer.
- **Mejora continua:** cinco ciclos PDCA con antes y después (`18-mejora-continua-pdca.md`).

**Limitaciones que hay que decir en voz alta:**

- No se ha hecho una jornada real con tabletas (fase 46): el GPS se probó con un celular, con el emulador y simulado por HTTP.
- El JavaScript del módulo (mapa y tablero) no tiene pruebas unitarias.
- SonarQube se corrió a mano el 5-nov; el CI corre flake8, ESLint, `tsc`, Jest, gitleaks y la suite de Odoo.
- La demostración está desplegada con dominio público (`buses.madebyjohan.xyz`) en un homelab, no en un servidor de producción: no hay respaldo automático ni copia fuera del equipo.
- El kichwa es un borrador sin revisión de una persona hablante.
- No hay QA independiente: quien desarrolla también probó.

**Decisión del informe:** *"No está listo para producción general: falta la jornada real con tabletas. Sí está listo como demostración pública y para un piloto controlado con personal de la universidad."*

---

## 9. Cierre (1 min)

*"Para resumir: el sistema resuelve el problema que pidió el cliente: el pasajero ve los buses y reporta quejas sin login, la administración recibe alertas y evalúa cada recorrido con reglas explícitas, y 12 indicadores salen de consultas que se pueden comprobar. Está medido, no solo afirmado: 639 pruebas de Odoo y 197 de la tableta sin fallos, 1.000 peticiones aleatorias sin un error, 94,3 % de cobertura de Python y 0,03 segundos de respuesta media. Y está documentado con honestidad: sabemos qué falla, por qué falla y cómo se arregla."*

**Próximos pasos, en orden:**

1. Jornada real con tabletas (fase 46), con corte de red y SOS sin señal.
2. Respaldo automático con copia fuera del equipo en el homelab.
3. Pruebas unitarias del JavaScript del módulo.
4. Volver a correr SonarQube con el código actual.
5. Revisar el kichwa con una persona hablante.

*"Gracias. Quedamos atentos a sus preguntas."*

---

## Preguntas difíciles y respuestas

**1. ¿Por qué lo dan por bueno si hay un defecto abierto?**
No lo damos por bueno para producción abierta; lo damos por apto para un piloto controlado. El abierto (DEF-079) es un aviso de Android 17 en una librería de terceros que no detiene el GPS; está registrado con su causa y su plan.

**2. ¿Cómo saben que una corrección no rompió otra cosa?**
Cada corrección deja una prueba de regresión (regla 5) y la suite completa corre en el CI. Después de la última corrección (DEF-091) se volvió a ejecutar toda la tubería (`qa/ejecutar_todo.py`) y se regeneraron los documentos de resultados desde las evidencias.

**3. ¿Cómo saben que el sistema funciona si nunca lo probaron con un celular real?**
Se probó el camino completo con un GPS simulado que usa el mismo protocolo (OsmAnd, puerto 5055) que usa la app. Eso valida Traccar, el webhook, Odoo y el mapa. No valida batería, segundo plano ni pantalla apagada, y por eso es el criterio pendiente de la fase 9.

**4. ¿Por qué el celular del chofer y no un GPS dedicado?**
Fue decisión del cliente por costo. El plan registra las advertencias: Android debe dejar la app sin restricción de batería, iPhone es menos fiable en segundo plano, hace falta un soporte con carga, un plan de datos y el consentimiento escrito del chofer.

**5. ¿Qué pasa con los datos personales de choferes y pasajeros?**
Privacidad por diseño: el pasajero solo ve nombre, posición, rumbo y estado del bus; el contacto de una queja es opcional, solo lo ven los administradores y se borra a los 90 días de resuelta; el identificador del GPS solo lo ven los administradores. Falta el consentimiento escrito de los choferes y la revisión legal del aviso (la hace la universidad).

**6. ¿Soportará 100 buses?**
Se necesitan 10 peticiones por segundo y se midieron 47,8 con un solo proceso y 20 hilos, sin errores. Falta repetirlo con varios procesos y con el volumen de 30 días (unos 10,8 millones de posiciones, cerca de 3 GB). El volumen del plan es una estimación, no una medida.

**7. ¿Por qué Odoo para algo que parece una app de mapas?**
Porque trae usuarios, permisos, panel, tareas programadas y traducciones. Eso dejó el tiempo para lo que aporta valor: ingesta, alertas, portal y quejas.

**8. ¿Qué es la cobertura de 94,3 % y por qué confiar en ella?**
Es el porcentaje de sentencias y ramas del código que ejecutan las pruebas, medido con coverage.py. No garantiza que no haya errores, y lo demuestra DEF-008 a DEF-010: estaban en código cubierto, porque faltaban datos inválidos en las pruebas. Por eso añadimos la auditoría aleatoria.

**9. ¿El CMMI nivel 2 está certificado?**
No. Es una autoevaluación contra las 22 áreas de proceso, no una evaluación SCAMPI. Dijimos "nivel 2 en consolidación": 4 de 6 áreas se cumplen y 2 son parciales.

**10. ¿Qué hizo Claude Code y qué hicieron ustedes?**
Claude Code ayudó a escribir y probar el código y la documentación; las decisiones del alcance, las del cliente y la aprobación son humanas. Está dicho en el RACI: no aprueba despliegues ni sustituye a un QA independiente. *(Ajusten esta respuesta a cómo lo quieran presentar.)*

**11. ¿Por qué recortaron funciones?**
Por pedido del cliente se priorizó lo que se pudiera defender y probar. Quedó fuera lo que dependía de datos o decisiones que aún no hay: roster oficial, trazados por calle, correo y puntualidad.

**12. ¿Cómo evitan que alguien falsifique posiciones?**
El webhook exige un secreto en cabecera y lo compara en tiempo constante; en producción el proxy lo bloquea desde fuera y el tráfico del celular va por HTTPS. El punto débil es que el identificador del dispositivo es la única credencial del GPS: solo lo ven los gestores, y desde DEF-091 un chofer ya no puede leerlo por RPC. Está en la lista de mejoras.

**13. ¿Y si cae el webhook o Traccar?**
Un cron consulta `/api/positions` cada minuto como respaldo, y hay una prueba que comprueba que sobrevive a errores de Traccar. Además `/bus_tracking/health` responde 503 si no llegan posiciones. Falta conectar un servicio externo que avise.

**14. ¿Se puede recuperar tras un desastre?**
Hay respaldos de Odoo, Traccar y el filestore con checksums y retención, y se probó la restauración en una base paralela y una restauración completa. Falta copiar los respaldos fuera del servidor, y en el homelab de la demostración aún no hay respaldo automático.

**15. ¿Cuánto costaría tenerlo en Azure?**
No hay un cálculo en el proyecto. El plan recomienda una máquina virtual de 2 vCPU y 4 a 8 GB, suficiente para 100 buses o menos, pero no se probó contra una suscripción real. No dar una cifra sin calcularla antes.

---

## Cifras para memorizar

| Dato | Valor |
|---|---|
| Servicios de bus / líneas públicas | 11 / 4 (Troncal, Izamba, Pelileo, Píllaro) |
| Pruebas de Odoo / tableta | 639 / 197, 0 fallos (23-nov) |
| Suite en vivo | 47 casos, 0 fallos (28-oct: 42 casos, 3 fallos) |
| Auditoría aleatoria | 1.000 peticiones, 0 fallos (28-oct: 57) |
| Fallos totales | 0 de 1.686 en la corrida del 23-nov (28-oct: 60 de 1.192, todos del webhook) |
| Cobertura | Python 94,3 %; tableta 89,2 %; SonarQube 78,4 % (5-nov) |
| Tiempo medio | 0,030 s |
| Capacidad medida / necesaria | 47,8 req/s / 10 req/s |
| Indicadores | 12 (8 de transporte y 4 de calidad) |
| Defectos | 93 registrados, 92 cerrados, 1 abierto (DEF-079) |
| Metas del cuadro de mando | 12 de 12 cumplidas (28-oct: 8 de 12) |
| Política | 7 reglas |
| Lluvia de ideas | 94 ideas |
| ISO 25010 | 7 cumple, 19 parcial, 5 no evaluado |
| ISO 12207 | 13 cumple, 14 parcial, 3 no aplica |
| CMMI | Nivel 2 en consolidación |
| Decisión | Demostración pública y piloto controlado; no producción general |

## Qué no decir

- No decir "está certificado" ni "cumple la ISO": es una autoevaluación.
- No decir "probado con celular real": se probó con un GPS simulado.
- No decir "listo para producción": está listo para un piloto controlado.
- No dar cifras de costo de Azure ni de usuarios que no estén medidas.
- No presentar el kichwa como definitivo: es un borrador sin revisión.
- No decir que la lluvia de ideas fue una sesión real: es una reconstrucción a partir del plan y la bitácora (así consta en `docs/calidad/06-lluvia-de-ideas.md`).
