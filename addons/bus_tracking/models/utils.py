import math
import re
import unicodedata
from datetime import timezone

from dateutil import parser

KNOTS_TO_KMH = 1.852
MOVING_ABOVE_KMH = 2.0

# Defaults for the Universidad Tecnica de Ambato deployment (all editable in Settings).
DEFAULT_BRAND = 'Buses UTA'
DEFAULT_MAP_CENTER = (-1.2417, -78.6167)    # Ambato, Tungurahua, Ecuador (approximate city centre)
LOCAL_TIMEZONE = 'America/Guayaquil'        # UTC-5, no daylight saving


# Map tiles: CARTO Voyager (OpenStreetMap data). A third-party service with its own terms and key;
# change it in Settings > Map tiles. Leaflet fills in {s}, {z}, {x}, {y} and {r}.
DEFAULT_TILE_URL = ('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
                    '?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb')


def tile_url(env):
    value = (env['ir.config_parameter'].sudo().get_param('bus_tracking.tile_url') or '').strip()
    return value if value.startswith('https://') and '{z}' in value else DEFAULT_TILE_URL


def int_param(env, key, default):
    """A whole-number system parameter. A typo in Settings > Technical falls back to the
    default instead of breaking the cron or the page that reads it."""
    value = env['ir.config_parameter'].sudo().get_param(key)
    if value in (False, None, ''):
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def brand_name(env):
    value = env['ir.config_parameter'].sudo().get_param('bus_tracking.brand_name')
    return (value or '').strip() or DEFAULT_BRAND


def map_center(env):
    """Latitude and longitude from the 'lat,lon' setting; the default when it is empty or malformed."""
    value = env['ir.config_parameter'].sudo().get_param('bus_tracking.map_center') or ''
    try:
        lat, lon = (float(part) for part in value.split(','))
    except ValueError:
        return DEFAULT_MAP_CENTER
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else DEFAULT_MAP_CENTER


PHONE_CHARS = re.compile(r'^[0-9+()\-\s]{6,30}$')
EMAIL_SHAPE = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$')


def public_contact(env):
    """Phone and email the university wants passengers to see. Empty means: show no contact at all.
    Nothing is invented: a value only appears when someone typed it in Settings."""
    icp = env['ir.config_parameter'].sudo()
    phone = (icp.get_param('bus_tracking.contact_phone') or '').strip()
    email = (icp.get_param('bus_tracking.contact_email') or '').strip()
    return {
        'phone': phone if PHONE_CHARS.match(phone) else '',
        'phone_href': re.sub(r'[^0-9+]', '', phone) if PHONE_CHARS.match(phone) else '',
        'email': email if EMAIL_SHAPE.match(email) else '',
    }


# The driver app speaks Spanish, English and Kichwa; Odoo names its languages differently
# (es_EC, en_US, qu_EC...). Kichwa is a language this module adds to Odoo (data/languages.xml); where it is
# not installed the driver reads Spanish.
APP_LANGUAGES = {
    'es': ('es_EC', 'es_419', 'es_ES'),
    'qu': ('qu_EC', 'es_EC', 'es_419', 'es_ES'),
    'en': ('en_US', 'en_GB'),
}


def pick_odoo_lang(requested, installed, fallback=None):
    """The installed Odoo language that matches the language the app asked for, else `fallback`.

    `requested` comes from the request body: anything that is not one of the app languages is ignored.
    """
    if not isinstance(requested, str) or requested not in APP_LANGUAGES:
        return fallback
    for code in APP_LANGUAGES[requested]:
        if code in installed:
            return code
    base = 'en' if requested == 'en' else 'es'
    for code in sorted(installed):
        if code.split('_')[0] == base:
            return code
    return fallback


def fold(text):
    """Lowercase without accents, so "Pillaro" finds "Píllaro"."""
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower().strip()


def safe_http_url(value):
    value = (value or '').strip()
    return value if value.lower().startswith(('http://', 'https://')) and ' ' not in value else ''


EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def parse_traccar_dt(value):
    """Traccar ISO-8601 string -> naive UTC datetime (Odoo format)."""
    if not value or not isinstance(value, str):
        return False
    try:
        dt = parser.isoparse(value)
    except (ValueError, TypeError, OverflowError):
        return False
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def clock_to_float(text):
    """'6:16' -> 6.2667 (hours)."""
    hours, mins = str(text).strip().split(':')
    return int(hours) + int(mins) / 60.0


def float_to_clock(value):
    """6.2667 -> '06:16'."""
    total = int(round(value * 60))
    return '%02d:%02d' % divmod(total, 60)


def local_now(env):
    """Current local time (Ecuador) as an aware datetime."""
    import pytz
    from datetime import datetime
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE))
