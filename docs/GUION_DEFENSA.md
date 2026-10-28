# Guion de defensa: sistema de rastreo de buses de la UTA

Duración objetivo: **15 minutos de exposición y 5 de preguntas**. Cada sección dice cuánto dura, qué decir y qué mostrar. El texto en cursiva es lo que se dice en voz alta; el resto son notas para quien expone. Todas las cifras salen de `docs/calidad/` (ejecución del 28-oct-2026); si se vuelve a ejecutar `qa/ejecutar_todo.sh`, hay que actualizarlas.

Reparto sugerido si exponen dos personas: quien desarrolló presenta las secciones 1 a 5 y 9; quien hizo de QA presenta las secciones 6 a 8.

---

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

*"El celular del chofer, con la app Traccar Client, manda su posición a Traccar. Traccar la reenvía por webhook a Odoo, donde está nuestro módulo `bus_tracking`. Como respaldo, un cron consulta a Traccar cada minuto, por si el webhook falla."*

```
Celular (Traccar Client) --> Traccar --webhook--> Odoo (bus_tracking) --> mapa, alertas, portal
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
| **Azure con máquina virtual Linux** | Decisión del cliente. Traccar recibe conexiones de dispositivos que no encajan en servicios de aplicación web. **Aún no desplegado.** |
| **Español, inglés y kichwa** | Decisión del cliente. Odoo 16 no trae kichwa; se hizo en el portal con un diccionario propio, marcado como borrador hasta que lo revise una persona hablante. |

*"Todas estas decisiones se tomaron con el cliente en la fase 0 y están en `docs/PLAN.md`."*

---

## 5. Cómo se trabajó: proceso y trazabilidad (1 min)

*"Seguimos un flujo Git con `main`, `develop` y ramas `feature/*`, `fix/*`, `refactor/*` y `chore/*`. Los commits son pequeños y siguen Conventional Commits, así que cualquiera se puede revertir."*

- Cada sesión de trabajo queda en `docs/BITACORA.md`, y el avance por fases en `docs/PLAN.md`.
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
| Pruebas automatizadas de Odoo | 150 | 0 fallos |
| Suite en vivo (12 funcionales, 22 de error, 7 de rendimiento, 1 de usabilidad) | 42 | 3 fallos |
| Auditoría aleatoria con semilla fija | 1.000 peticiones | 57 fallos (5,7 %) |
| Cobertura de código (sentencias y ramas) | 1.144 sentencias | **93,8 %** |

**Rendimiento** (servidor de un solo proceso):

- Uso normal: **0,037 s** en promedio por petición.
- Con 20 hilos simultáneos: p95 de 1,6 s y **39 peticiones por segundo**. Para 100 buses reportando cada 10 segundos se necesitan 10, es decir casi cuatro veces el margen.
- **Integridad concurrente:** 20 envíos idénticos a la vez guardan 1; 60 de 60 envíos de un mismo bus se guardan.

**Cuadro de mando:** de 12 metas, 8 se cumplen. Las 4 que no se cumplen son: respuestas 5xx (27), posiciones con datos imposibles (33), defectos cerrados (70 % contra la meta de 90 %) y cobertura de rutas HTTP (84,2 % contra 100 %: faltan `/bus_tracking/track`, `/bus_tracking/stop/load` y `/bus_tracking/stop/save`). Las tres primeras vienen de los defectos de la siguiente sección.

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

*"La evaluación encontró 10 defectos. 7 están cerrados y 3 siguen abiertos, y los tres tienen el mismo origen: el webhook no valida bien el contenido de la posición."*

| Defecto | Qué pasa | Estado |
|---|---|---|
| DEF-008 | Se guardan posiciones con latitud o longitud imposibles (p. ej. 95°) | Abierto |
| DEF-009 | Una latitud que no es número devuelve HTTP 500 | Abierto |
| DEF-010 | Una hora GPS inválida devuelve HTTP 500 | Abierto |

- **Causa raíz (cinco porqués):** se supuso que quien envía siempre manda datos correctos, porque todas las pruebas usaban datos válidos y una sola persona escribía el código y sus pruebas.
- **Arreglo ya diseñado:** validar rango y tipo en `_apply_position`, capturar el error de formato en `parse_traccar_dt` y responder 400, añadir un `@api.constrains` de rango, y portar las pruebas E7, E8 y E9 a la suite de Odoo. Un solo cambio cierra los tres.
- **Impacto medido:** 27 respuestas 5xx y 33 posiciones imposibles guardadas entre la suite y la auditoría. Fuera de eso, las consultas SQL de integridad dieron 0 en duplicados, alertas inconsistentes y recorridos incoherentes.

**Limitaciones que hay que decir en voz alta:**

- El GPS se **simuló con peticiones HTTP**; no se ha hecho un turno completo con un celular real.
- El push se probó en cifrado, firma y endpoints, pero no entregado a un navegador real.
- No se ejecutó análisis estático (SonarQube, flake8, pylint-odoo) ni hay integración continua.
- No se desplegó en Azure ni se probó con dominio público.
- El kichwa es un borrador sin revisión de una persona hablante.
- No hay QA independiente: quien desarrolla también probó.

**Decisión del informe:** *"Es apto para un piloto controlado con personal de la universidad. La producción abierta espera a cerrar esos tres defectos y a probar un turno completo con celular y Traccar reales."*

---

## 9. Cierre (1 min)

*"Para resumir: el sistema resuelve el problema que pidió el cliente: el pasajero ve los buses y reporta quejas sin login, y la administración recibe alertas. Está medido, no solo afirmado: 150 pruebas sin fallos, 93,8 % de cobertura y 0,037 segundos de respuesta media. Y está documentado con honestidad: sabemos qué falla, por qué falla y cómo se arregla."*

**Próximos pasos, en orden:**

1. Cerrar DEF-008 a DEF-010 y portar sus pruebas.
2. Probar un turno completo con celular y Traccar reales.
3. Repetir la prueba de carga con varios procesos y el volumen de 30 días.
4. Análisis estático e integración continua.
5. Desplegar en Azure y revisar el kichwa con una persona hablante.

*"Gracias. Quedamos atentos a sus preguntas."*

---

## Preguntas difíciles y respuestas

**1. ¿Por qué lo dan por bueno si hay defectos abiertos?**
No lo damos por bueno para producción abierta; lo damos por apto para un piloto controlado. Los defectos están registrados con causa raíz y arreglo, y nuestra propia política (regla 4) dice que bloquean las funciones nuevas hasta cerrarse.

**2. ¿Por qué no los corrigieron antes de la defensa?**
La evaluación de calidad era precisamente para encontrarlos y documentarlos con evidencia. Corregirlos y volver a ejecutar toda la tubería (`qa/ejecutar_todo.sh`) es el siguiente paso. *(Si ya los corrigieron antes de la defensa, cambiar esta respuesta y las cifras.)*

**3. ¿Cómo saben que el sistema funciona si nunca lo probaron con un celular real?**
Se probó el camino completo con un GPS simulado que usa el mismo protocolo (OsmAnd, puerto 5055) que usa la app. Eso valida Traccar, el webhook, Odoo y el mapa. No valida batería, segundo plano ni pantalla apagada, y por eso es el criterio pendiente de la fase 9.

**4. ¿Por qué el celular del chofer y no un GPS dedicado?**
Fue decisión del cliente por costo. El plan registra las advertencias: Android debe dejar la app sin restricción de batería, iPhone es menos fiable en segundo plano, hace falta un soporte con carga, un plan de datos y el consentimiento escrito del chofer.

**5. ¿Qué pasa con los datos personales de choferes y pasajeros?**
Privacidad por diseño: el pasajero solo ve nombre, posición, rumbo y estado del bus; el contacto de una queja es opcional, solo lo ven los administradores y se borra a los 90 días de resuelta; el identificador del GPS solo lo ven los administradores. Falta el consentimiento escrito de los choferes y la revisión legal del aviso (la hace la universidad).

**6. ¿Soportará 100 buses?**
Se necesitan 10 peticiones por segundo y se midieron 39 con un solo proceso y 20 hilos, sin errores. Falta repetirlo con varios procesos y con el volumen de 30 días (unos 10,8 millones de posiciones, cerca de 3 GB). El volumen del plan es una estimación, no una medida.

**7. ¿Por qué Odoo para algo que parece una app de mapas?**
Porque trae usuarios, permisos, panel, tareas programadas y traducciones. Eso dejó el tiempo para lo que aporta valor: ingesta, alertas, portal y quejas.

**8. ¿Qué es la cobertura de 93,8 % y por qué confiar en ella?**
Es el porcentaje de sentencias y ramas del código que ejecutan las pruebas, medido con coverage.py. No garantiza que no haya errores, y lo demuestra DEF-008 a DEF-010: estaban en código cubierto, porque faltaban datos inválidos en las pruebas. Por eso añadimos la auditoría aleatoria.

**9. ¿El CMMI nivel 2 está certificado?**
No. Es una autoevaluación contra las 22 áreas de proceso, no una evaluación SCAMPI. Dijimos "nivel 2 en consolidación": 4 de 6 áreas se cumplen y 2 son parciales.

**10. ¿Qué hizo Claude Code y qué hicieron ustedes?**
Claude Code ayudó a escribir y probar el código y la documentación; las decisiones del alcance, las del cliente y la aprobación son humanas. Está dicho en el RACI: no aprueba despliegues ni sustituye a un QA independiente. *(Ajusten esta respuesta a cómo lo quieran presentar.)*

**11. ¿Por qué recortaron funciones?**
Por pedido del cliente se priorizó lo que se pudiera defender y probar. Quedó fuera lo que dependía de datos o decisiones que aún no hay: roster oficial, trazados por calle, correo y puntualidad.

**12. ¿Cómo evitan que alguien falsifique posiciones?**
El webhook exige un secreto en cabecera y lo compara en tiempo constante; en producción el proxy lo bloquea desde fuera y el tráfico del celular va por HTTPS. El punto débil es que el identificador del dispositivo es la única credencial del GPS; está en la lista de mejoras.

**13. ¿Y si cae el webhook o Traccar?**
Un cron consulta `/api/positions` cada minuto como respaldo, y hay una prueba que comprueba que sobrevive a errores de Traccar. Además `/bus_tracking/health` responde 503 si no llegan posiciones. Falta conectar un servicio externo que avise.

**14. ¿Se puede recuperar tras un desastre?**
Hay respaldos de Odoo, Traccar y el filestore con checksums y retención, y se probó la restauración en una base paralela y una restauración completa. Falta copiar los respaldos fuera del servidor.

**15. ¿Cuánto costaría tenerlo en Azure?**
No hay un cálculo en el proyecto. El plan recomienda una máquina virtual de 2 vCPU y 4 a 8 GB, suficiente para 100 buses o menos, pero no se probó contra una suscripción real. No dar una cifra sin calcularla antes.

---

## Cifras para memorizar

| Dato | Valor |
|---|---|
| Servicios de bus / líneas públicas | 11 / 4 (Troncal, Izamba, Pelileo, Píllaro) |
| Pruebas de Odoo | 150, 0 fallos |
| Suite en vivo | 42 casos, 3 fallos |
| Auditoría aleatoria | 1.000 peticiones, 57 fallos (5,7 %) |
| Fallos totales | 60 de 1.192 (5,03 %), todos del webhook |
| Cobertura | 93,8 % |
| Tiempo medio | 0,037 s |
| Capacidad medida / necesaria | 39 req/s / 10 req/s |
| Defectos | 10 registrados, 7 cerrados, 3 abiertos |
| Metas del cuadro de mando | 8 de 12 cumplidas |
| Política | 7 reglas |
| Lluvia de ideas | 94 ideas |
| ISO 25010 | 7 cumple, 19 parcial, 5 no evaluado |
| ISO 12207 | 13 cumple, 14 parcial, 3 no aplica |
| CMMI | Nivel 2 en consolidación |
| Decisión | Apto para piloto controlado |

## Qué no decir

- No decir "está certificado" ni "cumple la ISO": es una autoevaluación.
- No decir "probado con celular real": se probó con un GPS simulado.
- No decir "listo para producción": está listo para un piloto controlado.
- No dar cifras de costo de Azure ni de usuarios que no estén medidas.
- No presentar el kichwa como definitivo: es un borrador sin revisión.
- No decir que la lluvia de ideas fue una sesión real: es una reconstrucción a partir del plan y la bitácora (así consta en `docs/calidad/06-lluvia-de-ideas.md`).
