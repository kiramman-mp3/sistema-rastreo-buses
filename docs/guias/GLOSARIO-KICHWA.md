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

## El panel de Odoo (la oficina)

Odoo no trae kichwa. El módulo agrega el idioma `qu_EC` (`data/languages.xml`) y su catálogo
`addons/bus_tracking/i18n/qu.po` con los 417 textos del módulo. Cada persona lo elige en
**Preferencias > Idioma**. La tableta también lo pide, y por eso los avisos del servidor («Hasta 60 km/h»,
etc.) salen en kichwa.

Límites:

- Solo están traducidos los textos de este módulo (menús, formularios, reportes, avisos). Lo que trae Odoo
  de fábrica (Ajustes generales, Aplicaciones, Usuarios...) no tiene kichwa y se ve en inglés.
- La página de ingreso del personal (`/web/login`) usa el idioma del navegador de cada persona; no hay selector.
- Para regenerar los catálogos tras cambiar textos: exportar con `odoo --i18n-export` y completar `es.po` y
  `qu.po` (ninguna entrada puede quedar vacía: una prueba lo comprueba).
