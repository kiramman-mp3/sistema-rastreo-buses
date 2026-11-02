"""Development data for screenshots and manual testing. NOT for production.

Run inside the Odoo container (local docker compose):

    docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo < scripts/dev_seed.py

It is idempotent: the first run creates lines, stops, buses, a driver and a few complaints;
every later run only moves the buses forward along their lines with fresh timestamps, so the
maps show "live" buses again. Coordinates are approximate (OpenStreetMap), only for testing.
"""
from datetime import timedelta

from odoo import fields

LINES = [
    ('L1', 'Huachi – Ingahurco', '#7A1A22', [
        ('Campus Huachi', -1.26870, -78.62470),
        ('Mall de los Andes', -1.26330, -78.62480),
        ('Redondel de Huachi Chico', -1.25700, -78.62300),
        ('Parque Cevallos', -1.24400, -78.62300),
        ('Mercado Central', -1.24100, -78.62000),
        ('Campus Ingahurco', -1.24940, -78.61530),
    ]),
    ('L2', 'Huachi – Querochaca', '#1E5560', [
        ('Campus Huachi', -1.26870, -78.62470),
        ('Huachi Grande', -1.29050, -78.62700),
        ('Montalvo', -1.31300, -78.62150),
        ('Cevallos', -1.35450, -78.61500),
        ('Campus Querochaca', -1.36850, -78.60670),
    ]),
    ('L3', 'Ingahurco – Izamba', '#9A4A12', [
        ('Campus Ingahurco', -1.24940, -78.61530),
        ('Terminal Terrestre', -1.22970, -78.62220),
        ('Av. Indoamérica', -1.21900, -78.60700),
        ('Izamba', -1.20750, -78.59170),
    ]),
    ('L4', 'Ambato – Píllaro', '#3D4F8A', [
        ('Campus Ingahurco', -1.24940, -78.61530),
        ('Izamba', -1.20750, -78.59170),
        ('San Miguelito', -1.18600, -78.56000),
        ('Píllaro', -1.17000, -78.54000),
    ]),
]

# bus name, plate, line, progress along the line (0..1), speed km/h, minutes since last fix
BUSES = [
    ('Bus 01', 'TAA-1021', 'L1', 0.18, 28.0, 0),
    ('Bus 04', 'TAA-1044', 'L1', 0.62, 0.0, 0),
    ('Bus 07', 'TBA-2207', 'L2', 0.40, 46.0, 0),
    ('Bus 09', 'TBA-2209', 'L2', 0.85, 31.0, 0),
    ('Bus 11', 'TCA-3011', 'L3', 0.30, 24.0, 0),
    ('Bus 12', 'TCA-3012', 'L3', 0.70, 0.0, 9),     # quiet for 9 min: "sin señal" in the panel
]
KNOTS = 1.0 / 1.852
STEP_PER_RUN = 0.035


def point_at(stops, t):
    """Point and heading at fraction t of the polyline through the stops."""
    t = max(0.0, min(1.0, t))
    pts = [(lat, lon) for _n, lat, lon in stops]
    seg = t * (len(pts) - 1)
    i = min(int(seg), len(pts) - 2)
    f = seg - i
    (a_lat, a_lon), (b_lat, b_lon) = pts[i], pts[i + 1]
    import math
    course = (math.degrees(math.atan2(b_lon - a_lon, b_lat - a_lat)) + 360) % 360
    return a_lat + (b_lat - a_lat) * f, a_lon + (b_lon - a_lon) * f, course


ICP = env['ir.config_parameter'].sudo()
ICP.set_param('bus_tracking.brand_name', 'Buses UTA')
# Where the tablets send their GPS (Traccar's OsmAnd port). Without it no shift can start.
if not ICP.get_param('bus_tracking.gps_url'):
    ICP.set_param('bus_tracking.gps_url', 'http://localhost:5055')
env.user.tz = 'America/Guayaquil'
env.company.partner_id.tz = 'America/Guayaquil'

Route = env['bus.route']
routes = {}
for code, name, color, stops in LINES:
    route = Route.with_context(active_test=False).search([('code', '=', code)], limit=1)
    if not route:
        route = Route.create({
            'code': code, 'name': name, 'color': color, 'public': True,
            'stop_ids': [(0, 0, {'sequence': (i + 1) * 10, 'name': n, 'latitude': la, 'longitude': lo,
                                 'radius': 120}) for i, (n, la, lo) in enumerate(stops)],
        })
    routes[code] = (route, stops)

Vehicle = env['bus.vehicle']
first_run = not Vehicle.search_count([('plate', '=', 'TAA-1021')])
now = fields.Datetime.now()
for idx, (name, plate, code, progress, speed, minutes_ago) in enumerate(BUSES):
    route, stops = routes[code]
    bus = Vehicle.search([('plate', '=', plate)], limit=1)
    if not bus:
        bus = Vehicle.create({'name': name, 'plate': plate, 'route_id': route.id, 'capacity': 40,
                              'traccar_unique_id': 'dev-%s' % plate.lower()})
        start = max(0.0, progress - 0.25)
    else:
        last = ICP.get_param('bus_tracking.dev_progress_%s' % bus.id)
        start = float(last) if last else progress
        progress = start + (STEP_PER_RUN if speed else 0.0)
        if progress > 1.0:
            progress, start = 0.02, 0.0
    # A short trail of positions up to "progress", so arrivals and the 4 h track exist.
    steps = 6
    for k in range(steps + 1):
        frac = start + (progress - start) * k / steps
        lat, lon, course = point_at(stops, frac)
        when = now - timedelta(minutes=minutes_ago, seconds=(steps - k) * 20)
        bus._apply_position({
            'fixTime': when.strftime('%Y-%m-%dT%H:%M:%S.000+00:00'),
            'latitude': lat, 'longitude': lon,
            'speed': (speed if k == steps else max(speed, 20.0)) * KNOTS,
            'course': course,
        })
    ICP.set_param('bus_tracking.dev_progress_%s' % bus.id, str(progress))

if first_run:
    Users = env['res.users'].with_context(no_reset_password=True)
    driver = Users.search([('login', '=', 'chofer1')], limit=1)
    if not driver:
        driver = Users.create({
            'name': 'Luis Pacheco', 'login': 'chofer1', 'password': 'chofer1',
            'tz': 'America/Guayaquil', 'lang': 'es_EC',
            'groups_id': [(6, 0, [env.ref('base.group_portal').id, env.ref('bus_tracking.group_bus_driver').id])],
        })
    bus01 = Vehicle.search([('plate', '=', 'TAA-1021')], limit=1)
    shift = env['bus.shift'].create({'user_id': driver.id, 'vehicle_id': bus01.id,
                                     'route_id': bus01.route_id.id})
    bus01.driver_id = driver.partner_id
    env['bus.incident'].create({'shift_id': shift.id, 'vehicle_id': bus01.id, 'kind': 'traffic',
                                'note': 'Trancón en la Av. Bolivariana', 'latitude': bus01.last_latitude,
                                'longitude': bus01.last_longitude})
    Complaint = env['bus.complaint']
    for code, kind, text in [
        ('L1', 'delay', 'Esperé 25 minutos en el Mall de los Andes y el bus pasó lleno sin parar.'),
        ('L2', 'safety', 'El bus iba muy rápido bajando a Cevallos, con gente de pie.'),
        ('L1', 'cleanliness', 'Los asientos del fondo estaban mojados y había basura en el piso.'),
        ('L3', 'behavior', 'El conductor fue muy amable y esperó a una compañera que venía corriendo.'),
    ]:
        Complaint.create({'route_id': routes[code][0].id, 'kind': kind, 'description': text, 'lang': 'es'})

# A second driver without a shift, to see the bus selection screen.
Users2 = env['res.users'].with_context(no_reset_password=True)
if not Users2.search([('login', '=', 'chofer2')], limit=1):
    Users2.create({
        'name': 'María Torres', 'login': 'chofer2', 'password': 'chofer2',
        'tz': 'America/Guayaquil', 'lang': 'es_EC',
        'groups_id': [(6, 0, [env.ref('base.group_portal').id, env.ref('bus_tracking.group_bus_driver').id])],
    })

# Make the admin's panel Spanish and in Ecuador's time zone.
env.ref('base.user_admin').write({'lang': 'es_EC', 'tz': 'America/Guayaquil'})
env.cr.commit()
print('dev seed ok: %d lines, %d buses' % (len(routes), Vehicle.search_count([])))
