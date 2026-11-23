"""Datos de demostración para los reportes: viajes simulados de varias semanas, choferes y quejas.

No se ejecuta con Python: se pasa a `odoo shell`. Sirve en desarrollo y en el servidor, porque no toca lo real:
los viajes salen de los buses simulados («Sim Lx») y las rutas, choferes y quejas llevan el prefijo de demo.

    docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo \\
        --log-level=error < scripts/demo_reportes.py

Es idempotente por día: el simulador salta los días que ya tienen viaje, así que repetirlo agrega viajes en
días anteriores (DAYS), no duplica los de hoy. Las quejas solo se crean la primera vez.
"""
import random
import secrets
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied

DAYS = 21
rnd = random.Random(2026)

LINES = [   # code, name, color, stops (name, lat, lon), long stretches (they can show a deviation / speeding)
    ('L1', 'Huachi – Ingahurco', '#7A1A22', False, [
        ('Campus Huachi', -1.26870, -78.62470), ('Mall de los Andes', -1.26330, -78.62480),
        ('Redondel de Huachi Chico', -1.25700, -78.62300), ('Parque Cevallos', -1.24400, -78.62300),
        ('Mercado Central', -1.24100, -78.62000), ('Campus Ingahurco', -1.24940, -78.61530)]),
    ('L2', 'Huachi – Querochaca', '#1E5560', True, [
        ('Campus Huachi', -1.26870, -78.62470), ('Huachi Grande', -1.29050, -78.62700),
        ('Montalvo', -1.31300, -78.62150), ('Cevallos', -1.35450, -78.61500),
        ('Campus Querochaca', -1.36850, -78.60670)]),
    ('L3', 'Ingahurco – Izamba', '#9A4A12', False, [
        ('Campus Ingahurco', -1.24940, -78.61530), ('Terminal Terrestre', -1.22970, -78.62220),
        ('Av. Indoamérica', -1.21900, -78.60700), ('Izamba', -1.20750, -78.59170)]),
    ('L4', 'Ambato – Píllaro', '#3D4F8A', True, [
        ('Campus Ingahurco', -1.24940, -78.61530), ('Izamba', -1.20750, -78.59170),
        ('San Miguelito', -1.18600, -78.56000), ('Píllaro', -1.17000, -78.54000)]),
]
DRIVERS = [('Luis Pacheco', 'chofer1'), ('María Torres', 'chofer2'),
           ('Carlos Villacís', 'chofer3'), ('Andrea Sánchez', 'chofer4')]
# scenario -> weight: most trips go well, the rest feed the reports
WEIGHTS = {'punctual': 38, 'within_tolerance': 16, 'early': 6, 'late': 14, 'skipped_stop': 5, 'incomplete_end': 3,
           'long_stop': 4, 'not_started': 3, 'late_deviation': 3, 'deviation': 4, 'speeding': 4}
LONG_ONLY = {'deviation', 'late_deviation', 'speeding', 'long_stop'}
COMPLAINTS = [
    ('delay', 'Esperé 25 minutos en la parada y el bus pasó lleno sin parar.'),
    ('delay', 'El bus de la mañana llegó casi veinte minutos tarde otra vez.'),
    ('safety', 'El bus iba muy rápido en la bajada, con gente de pie.'),
    ('safety', 'El conductor frenó de golpe y una señora se cayó.'),
    ('cleanliness', 'Los asientos del fondo estaban mojados y había basura en el piso.'),
    ('cleanliness', 'El bus olía mal y las ventanas no abrían.'),
    ('behavior', 'El conductor fue muy amable y esperó a una compañera que venía corriendo.'),
    ('behavior', 'El conductor discutió con un pasajero por el cambio.'),
    ('delay', 'No pasó el bus de las 12:00, lo vimos en el mapa detenido.'),
    ('safety', 'Se paró lejos de la parada y tuvimos que cruzar la vía.'),
]

env = globals()['env']
Route, Users = env['bus.route'], env['res.users'].with_context(no_reset_password=True)
Simulator = env['bus.trip.simulator']
group_ids = [env.ref('base.group_portal').id, env.ref('bus_tracking.group_bus_driver').id]

routes = {}
for code, name, color, long_stretch, stops in LINES:
    route = Route.with_context(active_test=False).search([('code', '=', code)], limit=1)
    if not route:
        route = Route.create({
            'code': code, 'name': name, 'color': color, 'public': True,
            'stop_ids': [(0, 0, {'sequence': (i + 1) * 10, 'name': n, 'latitude': la, 'longitude': lo,
                                 'radius': 120}) for i, (n, la, lo) in enumerate(stops)]})
    routes[code] = (route, long_stretch)
    Simulator._ensure_plan(route)


def weak_password(user):
    """Older versions of this script gave each driver its login as password: anyone could sign in with it."""
    try:
        user.with_user(user)._check_credentials(user.login, {'interactive': False})
    except AccessDenied:
        return False
    return True


# The site is public: each demo driver gets a random password, shown once here and never stored in the repository.
# A driver an older run left with the login as password gets a new one too.
drivers, passwords = [], []
for name, login in DRIVERS:
    user = Users.search([('login', '=', login)], limit=1)
    if not user:
        password = secrets.token_urlsafe(12)
        user = Users.create({
            'name': name, 'login': login, 'password': password, 'tz': 'America/Guayaquil', 'lang': 'es_EC',
            'groups_id': [(6, 0, group_ids)]})
        passwords.append((login, password))
    elif weak_password(user):
        password = secrets.token_urlsafe(12)
        user.password = password
        passwords.append((login, password))
    drivers.append(user)
env.cr.commit()

scenarios, weights = zip(*WEIGHTS.items())
made = 0
for code, (route, long_stretch) in routes.items():
    for days_ago in range(1, DAYS + 1):
        scenario = rnd.choices(scenarios, weights)[0]
        if scenario in LONG_ONLY and not long_stretch:
            scenario = 'late'
        Simulator._simulate(route, scenario, days_ago=days_ago, driver=rnd.choice(drivers))
        made += 1
    env.cr.commit()

first_run = not env['bus.complaint'].search_count([('description', '=', COMPLAINTS[0][1])])
if first_run:
    for i in range(24):
        kind, text = COMPLAINTS[i % len(COMPLAINTS)]
        route = routes[rnd.choice(list(routes))][0]
        complaint = env['bus.complaint'].create({'route_id': route.id, 'kind': kind, 'description': text, 'lang': 'es'})
        when = fields.Datetime.now() - timedelta(days=rnd.randint(0, DAYS), hours=rnd.randint(0, 12))
        env.cr.execute('UPDATE bus_complaint SET create_date = %s WHERE id = %s', (when, complaint.id))
    env.cr.commit()

print('demo ok: %d viajes simulados nuevos, %d viajes en total, %d multas, %d quejas' % (
    made, env['bus.trip'].search_count([]), env['bus.fine'].search_count([]), env['bus.complaint'].search_count([])))
for login, password in passwords:
    print('chofer %s: contraseña nueva %s (se muestra una sola vez; guárdala en un gestor de contraseñas)' % (
        login, password))
