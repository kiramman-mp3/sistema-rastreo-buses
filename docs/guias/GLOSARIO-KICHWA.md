# Glosario del kichwa de Buses UTA

El portal de pasajeros, la página de privacidad y la tableta del chofer están en kichwa unificado del Ecuador.
La traducción la hizo una IA, sin revisión de una persona hablante: las mismas palabras se repiten en los
tres sitios para que se entiendan, pero conviene que una persona de la comunidad las revise antes de un
uso oficial. Los textos están en `addons/bus_tracking/models/portal_i18n.py`,
`addons/bus_tracking/models/privacy_text.py` y `apps/conductor-tablet/src/i18n/index.ts`.

| Español | Kichwa | Español | Kichwa |
|---|---|---|---|
| ruta, línea | ñan | parada | sayana |
| chofer | pushak | turno | llankay pacha |
| ahora | kunan | iniciar | kallarichiy |
| terminar | tukuchiy | entrar | yaykuy |
| salir | llukshiy | enviar | kachay |
| reportar, avisar | willay | problema | llaki |
| actualizar | musuyachiy | sin señal | mana rikurin |
| en movimiento | purishka | detenido | sayashka |
| contraseña | pakashka shimi | privacidad | pakashka willaykuna |
| otro | shuk | siguiente | katik |

Se dejaron como en español las palabras que ya se dicen así: bus, GPS, QR, SOS, correo, telefono, servidor,
accidente, tráfico, cámara.

## Qué queda en español

- Los avisos que escribe el servidor (por ejemplo «Hasta 60 km/h», en las alertas) salen en el idioma de
  Odoo del chofer: Odoo no tiene kichwa, así que la tableta los muestra en español.
- El panel de Odoo (personal de la oficina) está en inglés y español.
