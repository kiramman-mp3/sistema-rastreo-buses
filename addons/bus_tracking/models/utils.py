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
    if not value:
        return False
    dt = parser.isoparse(value)
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
