"""Crea los recorridos de prueba simulados (el conjunto de 12) en el Odoo de DESARROLLO y escribe su informe.

No se ejecuta con Python: se pasa a `odoo shell`. Los recorridos se marcan como simulados y el simulador solo
produce posiciones: lo que fue tarde, omitido o desviado lo deciden las reglas del sistema.

    docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo \\
        --log-level=error < scripts/seed_recorridos.py

Imprime el informe entre las marcas <<<INFORME y INFORME>>>
(es lo que se copia a docs/calidad/13-recorridos-de-prueba.md).
Repetirlo agrega otros 12 recorridos en días anteriores.
"""
SCENARIO_ES = {
    'punctual': "Puntual",
    'within_tolerance': "Algo tarde, dentro de la tolerancia",
    'early': "Adelantado",
    'late': "Con retraso",
    'skipped_stop': "Parada del medio omitida",
    'incomplete_end': "Se detuvo antes de la última parada",
    'deviation': "Fuera de ruta en el tramo más largo",
    'speeding': "Exceso de velocidad",
    'not_started': "Nunca arrancó",
    'late_deviation': "Con retraso y fuera de ruta",
}
FLAG_ES = {
    'late': 'retraso', 'early': 'adelanto', 'skipped': 'parada omitida', 'incomplete': 'incompleto',
    'not_started': 'no arrancó', 'off_route': 'desvío', 'speeding': 'velocidad',
}


def words(flags):
    return ', '.join(FLAG_ES[f] for f in (flags or '').split(',') if f) or 'ninguna'


env = globals()['env']
Simulator = env['bus.trip.simulator']
for route in env['bus.route'].search([]):
    Simulator._ensure_plan(route)
trips = Simulator._simulate_demo_set()
env.cr.commit()

rows = []
for trip in trips.sorted(lambda t: (t.route_id.code, t.planned_start)):
    rows.append('| %s | %s | %s | %s | %s | %s | %s | %d / %d / %d | %s | %.2f / %.2f |' % (
        trip.id, trip.route_id.code, trip.date, SCENARIO_ES[trip.scenario], words(trip.expected_flags),
        words(trip.detected_flags), 'Sí' if trip.detection_ok else 'NO',
        trip.stops_visited, trip.stops_late, trip.stops_skipped,
        ('%+.0f' % trip.delay_end_min) if trip.stops_visited else '—',
        trip.distance_est_km, trip.distance_real_km))
ok = len(trips.filtered('detection_ok'))
print('<<<INFORME')
print('| N.º | Ruta | Fecha | Escenario | Qué debía detectarse | Qué detectó el sistema | Coincide '
      '| Paradas visitadas / tarde / omitidas | Retraso al final (min) | Distancia estimada / recorrida (km) |')
print('|---|---|---|---|---|---|---|---|---|---|')
print('\n'.join(rows))
print()
print('Recorridos simulados: %d. Detección correcta: %d de %d (%.1f %%).'
      % (len(trips), ok, len(trips), 100.0 * ok / len(trips)))
print('INFORME>>>')
