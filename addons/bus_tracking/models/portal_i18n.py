"""Strings of the public passenger portal.

Kept in plain dictionaries so a language is added by adding a key. Kichwa is
deliberately absent until a native speaker has reviewed a translation.
"""

DEFAULT_LANG = 'es'

STRINGS = {
    'es': {
        'lang_name': 'Español',
        'title_routes': 'Buses en vivo',
        'pick_route': 'Elige tu ruta',
        'pick_route_help': 'Mira por dónde van los buses de tu ruta en este momento.',
        'no_routes': 'Todavía no hay rutas disponibles.',
        'buses_in_service': '{n} en servicio',
        'no_service': 'Sin buses con señal',
        'all_routes': 'Todas las rutas',
        'stops': 'Paradas',
        'buses_now': 'Buses de esta ruta',
        'no_buses': 'Ahora no hay buses con señal en esta ruta.',
        'status_moving': 'en movimiento',
        'status_stopped': 'detenido',
        'status_offline': 'sin señal',
        'updated': 'Actualizado hace {s} s',
        'update_error': 'No pudimos actualizar. Reintentando…',
        'report': 'Reportar un problema',
        'staff_login': 'Ingresar',
        'footer': 'La posición de los buses se actualiza cada pocos segundos.',
        'map_label': 'Mapa con los buses de la ruta',
        'report_title': 'Reportar un problema',
        'report_intro': 'Cuéntanos qué pasó. Lo revisa una persona del equipo.',
        'field_route': 'Ruta',
        'field_route_none': 'No sé o no aplica',
        'field_bus': 'Bus',
        'field_bus_none': 'No sé cuál',
        'field_kind': 'Qué pasó',
        'kind_delay': 'Demora o bus que no pasó',
        'kind_behavior': 'Trato del conductor o del personal',
        'kind_safety': 'Seguridad o forma de manejar',
        'kind_cleanliness': 'Limpieza o estado del bus',
        'kind_other': 'Otro',
        'field_description': 'Descripción',
        'field_description_help': 'Entre 10 y 2000 caracteres. Si puedes, di el lugar y la hora.',
        'field_email': 'Correo (opcional)',
        'field_phone': 'Teléfono (opcional)',
        'contact_help': 'Puedes enviar el reporte sin dejar datos. Si no los dejas, no podremos responderte.',
        'privacy': 'Usaremos estos datos solo para atender tu reporte. Si dejas correo o teléfono, se borran {days} días después de resolverlo.',
        'submit': 'Enviar reporte',
        'err_title': 'Revisa estos datos',
        'err_description': 'Escribe entre 10 y 2000 caracteres.',
        'err_email': 'Ese correo no parece válido.',
        'err_phone': 'Ese teléfono no parece válido.',
        'err_rate': 'Enviaste varios reportes seguidos. Intenta de nuevo más tarde.',
        'err_expired': 'La página estuvo abierta mucho tiempo. Revisa tus datos y envía de nuevo.',
        'thanks_title': 'Recibimos tu reporte',
        'thanks_text': 'Gracias por avisarnos. Una persona del equipo lo revisará.',
        'thanks_folio': 'Tu folio es',
        'thanks_no_contact': 'Como no dejaste datos de contacto, no podremos responderte.',
        'back_to_routes': 'Volver a las rutas',
        'privacy_more': 'Política de privacidad',
    },
    'en': {
        'lang_name': 'English',
        'title_routes': 'Live buses',
        'pick_route': 'Pick your route',
        'pick_route_help': 'See where the buses on your route are right now.',
        'no_routes': 'There are no routes available yet.',
        'buses_in_service': '{n} in service',
        'no_service': 'No buses reporting',
        'all_routes': 'All routes',
        'stops': 'Stops',
        'buses_now': 'Buses on this route',
        'no_buses': 'No buses are reporting on this route right now.',
        'status_moving': 'moving',
        'status_stopped': 'stopped',
        'status_offline': 'no signal',
        'updated': 'Updated {s} s ago',
        'update_error': "We couldn't update. Retrying…",
        'report': 'Report a problem',
        'staff_login': 'Sign in',
        'footer': 'Bus positions refresh every few seconds.',
        'map_label': 'Map with the buses of the route',
        'report_title': 'Report a problem',
        'report_intro': 'Tell us what happened. A person on the team will read it.',
        'field_route': 'Route',
        'field_route_none': "I don't know or not applicable",
        'field_bus': 'Bus',
        'field_bus_none': "I don't know which",
        'field_kind': 'What happened',
        'kind_delay': 'Delay or missed bus',
        'kind_behavior': 'Driver or staff behavior',
        'kind_safety': 'Safety or driving',
        'kind_cleanliness': 'Cleanliness or condition of the bus',
        'kind_other': 'Other',
        'field_description': 'Description',
        'field_description_help': 'Between 10 and 2000 characters. If you can, say where and when.',
        'field_email': 'Email (optional)',
        'field_phone': 'Phone (optional)',
        'contact_help': "You can send the report without leaving any details. If you don't, we won't be able to reply.",
        'privacy': 'We only use this information to handle your report. If you leave an email or phone, it is erased {days} days after the report is resolved.',
        'submit': 'Send report',
        'err_title': 'Please check these fields',
        'err_description': 'Write between 10 and 2000 characters.',
        'err_email': "That email doesn't look valid.",
        'err_phone': "That phone number doesn't look valid.",
        'err_rate': 'You sent several reports in a row. Please try again later.',
        'err_expired': 'The page was open for a long time. Check your details and send again.',
        'thanks_title': 'We got your report',
        'thanks_text': 'Thank you for letting us know. A person on the team will read it.',
        'thanks_folio': 'Your reference is',
        'thanks_no_contact': "Since you left no contact details, we won't be able to reply.",
        'back_to_routes': 'Back to the routes',
        'privacy_more': 'Privacy policy',
    },
}
STRINGS['es'].update(path_pick='Ver un recorrido', path_all='Todos los recorridos', path_reset='Restablecer')
STRINGS['en'].update(path_pick='Show one trip route', path_all='All routes', path_reset='Reset')

# Kichwa (Ecuador). DRAFT written without a native speaker: it must be reviewed before it is published.
# Whatever is missing falls back to Spanish. See docs/PLAN.md, phase 13.
KICHWA_DRAFT = {
    'lang_name': 'Kichwa (borrador)',
    'title_routes': 'Bus kunaka kunan',
    'pick_route': 'Ñanta akllay',
    'pick_route_help': 'Ñanpi bus kuna ima ladopi richun kunan rikuy.',
    'no_routes': 'Ñan kuna mana tiyanchu.',
    'all_routes': 'Tukuy ñankuna',
    'stops': 'Sayana kuna',
    'buses_now': 'Kay ñanpi bus kuna',
    'no_buses': 'Kunan kay ñanpi mana bus rikurinchu.',
    'status_moving': 'purishka',
    'status_stopped': 'sayashka',
    'status_offline': 'mana rikurin',
    'updated': 'Hawa {s} s kutin rikuchishka',
    'update_error': 'Mana kutin rikuchi ushashkachu. Kutin ruranchik…',
    'report': 'Llakita willay',
    'staff_login': 'Yaykuy',
    'back_to_routes': 'Ñankunaman kutiy',
    'path_reset': 'Kutin churay',
}
STRINGS['qu'] = {**STRINGS['es'], **KICHWA_DRAFT}


def pick_lang(accept_languages, requested=None, remembered=None):
    """Explicit request, then remembered choice, then the browser, then Spanish."""
    for candidate in (requested, remembered):
        if candidate in STRINGS:
            return candidate
    # Kichwa is never picked from the browser: it is a draft until a speaker has reviewed it.
    best = accept_languages.best_match(['es', 'en']) if accept_languages else None
    return best or DEFAULT_LANG
