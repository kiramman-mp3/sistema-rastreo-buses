"""The privacy page of the public site, written from what the system really does and with the retention
periods that are set in Settings (not invented numbers).

Plain functions, no database: the controller passes the values in. Spanish and English; Kichwa reads Spanish
like the rest of the portal until a speaker has reviewed a translation.

This text describes the system. The university still has to review it with whoever is in charge of personal
data protection before it counts as its official policy; if it has one, put its address in
Settings > Privacy policy link and the site will point there (docs/PRIVACIDAD.md).
"""

BACKUP_DAYS = 14  # scripts/backup.sh keeps copies this long by default (BACKUP_KEEP_DAYS)


def _kept(lang, days, what):
    """'<what> are kept N days' or, with no limit set, that nobody erases them by themselves."""
    if lang == 'en':
        if days and days > 0:
            return '%s are kept for %d days.' % (what, days)
        return '%s are not erased automatically: an administrator erases them.' % what
    if days and days > 0:
        return '%s se conservan %d días.' % (what, days)
    return '%s no se borran solas: las borra un administrador.' % what


def _contact_line(lang, contact, brand):
    email = (contact or {}).get('email') or ''
    phone = (contact or {}).get('phone') or ''
    if lang == 'en':
        if email or phone:
            return 'To use any of these rights write or call: %s.' % ', '.join(x for x in (email, phone) if x)
        return 'To use any of these rights ask the transport office of %s.' % brand
    if email or phone:
        return ('Para ejercer cualquiera de estos derechos escribe o llama a: %s.'
                % ', '.join(x for x in (email, phone) if x))
    return 'Para ejercer cualquiera de estos derechos acude a la oficina de transporte de %s.' % brand


def privacy_sections(lang, brand, contact=None, position_days=0, complaint_days=0):
    """The page as a list of sections: {'title': str, 'paragraphs': [str], 'bullets': [str]}."""
    if lang == 'en':
        return _english(brand, contact, position_days, complaint_days)
    return _spanish(brand, contact, position_days, complaint_days)


def _spanish(brand, contact, position_days, complaint_days):
    return [
        {'title': 'Quién trata estos datos', 'paragraphs': [
            '%s, mediante su sistema de rastreo de buses. Esta página dice qué datos se tratan, para qué, '
            'cuánto tiempo se guardan y cómo ejercer tus derechos.' % brand], 'bullets': []},
        {'title': 'Si solo miras el mapa', 'paragraphs': [
            'No pedimos nombre, correo ni teléfono para ver dónde van los buses. El mapa público muestra la '
            'posición de cada bus y su línea: no muestra quién conduce ni la placa.'], 'bullets': [
            'Si guardas "mi parada", queda solo en tu navegador; no llega al servidor.',
            'Si eliges un idioma, se guarda una cookie de preferencia (bus_lang) por un año.',
            'El servidor crea una cookie técnica de sesión (session_id, 7 días) que el sitio necesita para funcionar; '
            'no la usamos para identificarte.',
            'No usamos cookies de publicidad ni de seguimiento.']},
        {'title': 'Si envías un reporte', 'paragraphs': [
            'Guardamos lo que escribes (texto, línea, bus y tipo de problema) para atenderlo y mejorar el servicio. '
            'Dejar correo o teléfono es opcional y sirve solo para responderte.'], 'bullets': [
            ('El correo y el teléfono se borran %d días después de resolver el reporte.' % complaint_days
             if complaint_days and complaint_days > 0 else
             'El correo y el teléfono no se borran solos: los borra un administrador.'),
            'El texto del reporte y su estado no se borran automáticamente. No escribas datos personales de otras '
            'personas en él.']},
        {'title': 'Si eres chofer', 'paragraphs': [
            'La app de la tableta trata los datos necesarios para operar el servicio '
            'y para tu seguridad:'], 'bullets': [
            'Tu usuario y tu nombre. La contraseña se guarda protegida, nunca en claro; '
            'la credencial QR sirve solo para iniciar sesión.',
            'La posición del bus, la hora y la velocidad, solo mientras tu turno está abierto. Se envía a la '
            'oficina y se ve en el mapa del personal. Al terminar el turno el envío se detiene.',
            'Los avisos de problema y el SOS que pulses, con la hora y la posición, '
            'para que la oficina pueda atenderte.',
            'Las sesiones de la app (30 días) se guardan como huella, no en claro.',
            'La cámara se usa solo para leer el código QR: no se guarda ninguna imagen.',
            _kept('es', position_days, 'Las posiciones'),
            'Los registros de turnos y los avisos no se borran automáticamente.']},
        {'title': 'Quién puede ver los datos', 'paragraphs': [], 'bullets': [
            'El personal autorizado del servicio de transporte, con su propio usuario. '
            'Los pasajeros no ven datos de choferes.',
            'Los proveedores que hacen posible el servicio: el servidor donde se instala el sistema y, para dibujar '
            'el mapa, el proveedor de teselas del mapa (por defecto CARTO con datos de OpenStreetMap): '
            'tu navegador o la app le piden '
            'las imágenes del mapa y por eso conoce tu dirección IP y la zona que miras.',
            'Las notificaciones del personal pasan por el servicio de notificaciones de su navegador.']},
        {'title': 'Copias de seguridad', 'paragraphs': [
            'El sistema hace copias de seguridad. Un dato borrado puede seguir en las copias hasta %d días '
            '(por defecto; lo configura el administrador del servidor).' % BACKUP_DAYS], 'bullets': []},
        {'title': 'Tus derechos', 'paragraphs': [
            'Puedes pedir saber qué datos tuyos tenemos, corregirlos, que los borremos, o oponerte a su uso. '
            'Si algo no se puede borrar de inmediato (por ejemplo, está en una copia de seguridad), te lo diremos.',
            _contact_line('es', contact, brand)], 'bullets': []},
    ]


def _english(brand, contact, position_days, complaint_days):
    return [
        {'title': 'Who handles this data', 'paragraphs': [
            '%s, through its bus tracking system. This page says which data is handled, what for, how long it is '
            'kept and how to use your rights.' % brand], 'bullets': []},
        {'title': 'If you only look at the map', 'paragraphs': [
            'We do not ask for a name, email or phone to see where the buses are. The public map shows the position '
            'of each bus and its line: it does not show who drives or the plate.'], 'bullets': [
            'If you save "my stop" it stays in your browser only; it never reaches the server.',
            'If you choose a language, a preference cookie (bus_lang) is kept for one year.',
            'The server creates a technical session cookie (session_id, 7 days) that the site needs to work; '
            'we do not use it to identify you.',
            'We use no advertising or tracking cookies.']},
        {'title': 'If you send a report', 'paragraphs': [
            'We keep what you write (text, line, bus and kind of problem) to handle it and improve the service. '
            'Leaving an email or phone is optional and only used to answer you.'], 'bullets': [
            ('The email and phone are erased %d days after the report is resolved.' % complaint_days
             if complaint_days and complaint_days > 0 else
             'The email and phone are not erased by themselves: an administrator erases them.'),
            'The text of the report and its status are not erased automatically. Do not write other people\'s '
            'personal data in it.']},
        {'title': 'If you are a driver', 'paragraphs': [
            'The tablet app handles the data needed to run the service and for your safety:'], 'bullets': [
            'Your username and name. The password is stored protected, never in clear; '
            'the QR badge only serves to sign in.',
            'The bus position, time and speed, only while your shift is open. It goes to the office and shows on '
            'the staff map. When the shift ends, sending stops.',
            'The problem reports and the SOS you press, with time and position, so the office can help you.',
            'App sessions (30 days) are stored as a fingerprint, not in clear.',
            'The camera is only used to read the QR code: no image is stored.',
            _kept('en', position_days, 'Positions'),
            'Shift records and reports are not erased automatically.']},
        {'title': 'Who can see the data', 'paragraphs': [], 'bullets': [
            'Authorised staff of the transport service, with their own user. Passengers cannot see driver data.',
            'The providers that make the service possible: the server where the system is installed and, to draw '
            'the map, the map tile provider (CARTO with OpenStreetMap data by default): '
            'your browser or the app asks it for the '
            'map images, so it learns your IP address and the area you look at.',
            'Staff notifications go through the notification service of their browser.']},
        {'title': 'Backups', 'paragraphs': [
            'The system makes backups. Erased data may stay in the backups for up to %d days '
            '(by default; the server administrator sets it).' % BACKUP_DAYS], 'bullets': []},
        {'title': 'Your rights', 'paragraphs': [
            'You can ask what data of yours we have, have it corrected or erased, or object to its use. '
            'If something cannot be erased at once (for example, it is in a backup) we will tell you.',
            _contact_line('en', contact, brand)], 'bullets': []},
    ]
