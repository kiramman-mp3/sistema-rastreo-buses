"""Writes the six Grafana dashboards of the project (bi/grafana/dashboards/*.json).

The dashboards are code: this script is their source, the JSON files are what Grafana loads, and
addons/bus_tracking/tests/test_grafana_dashboards.py runs every query of every panel against a test database.

    python scripts/gen_grafana_dashboards.py

Every query reads only the kpi_* views of Odoo. The variables are:
  $route  lines (all by default)      $bus  buses (all by default)      $scope  all | real | simulated
and the time range of Grafana (the dashboards open on the last 30 days and refresh every 30 s).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'bi' / 'grafana' / 'dashboards'
DS = {'type': 'grafana-postgresql-datasource', 'uid': 'bus-kpi'}

# brand palette (docs/diseno): garnet, signal yellow, ink; plus the colours of the charts
GARNET, YELLOW, INK = '#7A1A22', '#FFC62B', '#172025'
TEAL, BROWN, INDIGO, OLIVE, PLUM = '#1E5560', '#9A4A14', '#3D4C8C', '#5C6F2B', '#6E4B80'
GOOD, WARN, BAD = '#1D6B44', '#C98A00', '#A1221B'
SERIES = [GARNET, TEAL, BROWN, INDIGO, YELLOW, OLIVE, PLUM]

DAY = "date_trunc('day', {col} - interval '5 hours') + interval '5 hours'"

SCOPE = "('$scope' = 'all' OR ('$scope' = 'real' AND NOT simulated) OR ('$scope' = 'simulated' AND simulated))"
CLOSED = "state IN ('done', 'incomplete')"

TRIPS = f"$__timeFilter(starts_at) AND {CLOSED} AND route_code IN ($route) AND bus IN ($bus) AND {SCOPE}"
STOPS = (f"$__timeFilter(starts_at) AND trip_state IN ('done', 'incomplete') AND route_code IN ($route) "
         f"AND bus IN ($bus) AND {SCOPE}")
ALERTS = (f"$__timeFilter(happened_at) AND (route_code IN ($route) OR route_code IS NULL) AND bus IN ($bus) "
          f"AND {SCOPE}")
REACHED = "actual_time IS NOT NULL"

# what each kind is called on screen (alerts of the rules and incidents of the drivers)
KINDS = {
    'speeding': 'Exceso de velocidad', 'offline': 'Sin señal', 'long_stop': 'Parada larga', 'off_route': 'Fuera de ruta',
    'late_arrival': 'Llegada tarde', 'skipped_stop': 'Parada omitida', 'incomplete_trip': 'Recorrido incompleto',
    'late_start': 'Salida tarde', 'breakdown': 'Avería', 'traffic': 'Tráfico', 'accident': 'Accidente',
    'other': 'Otro', 'sos': 'Emergencia (SOS)',
}
KIND_CASE = "CASE kind " + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in KINDS.items()) + " ELSE kind END"

# (good from, acceptable from, higher is better): the thresholds of addons/bus_tracking/models/bus_kpi.py
THRESHOLDS = {
    'T1': (90, 75, True), 'T2': (85, 70, True), 'T3': (5, 10, False), 'T4': (95, 85, True), 'T5': (50, 150, False),
    'T6': (5, 10, False), 'T7': (15, 30, False), 'S1': (99, 95, True), 'S2': (99, 95, True),
    'S3': (500, 2000, False), 'S4': (90, 75, True),
}

# code, title, unit, SQL (one number, in the first column)
INDICATORS = [
    ('T1', 'Cumplimiento de ruta', 'percent',
     f"SELECT 100.0 * COUNT(*) FILTER (WHERE state = 'done') / NULLIF(COUNT(*), 0) AS value "
     f"FROM kpi_trips WHERE {TRIPS}"),
    ('T2', 'Puntualidad', 'percent',
     f"SELECT 100.0 * COUNT(*) FILTER (WHERE status <> 'late') / NULLIF(COUNT(*), 0) AS value "
     f"FROM kpi_trip_stops WHERE {STOPS} AND {REACHED}"),
    ('T3', 'Retraso promedio', 'm',
     f"SELECT AVG(delay_min) AS value FROM kpi_trip_stops WHERE {STOPS} AND status = 'late'"),
    ('T4', 'Paradas atendidas', 'percent',
     f"SELECT 100.0 * COUNT(*) FILTER (WHERE {REACHED}) / NULLIF(COUNT(*), 0) AS value "
     f"FROM kpi_trip_stops WHERE {STOPS}"),
    ('T5', 'Desviación de la ruta', 'lengthm',
     f"SELECT AVG(deviation_avg_m) AS value FROM kpi_trips WHERE {TRIPS} AND distance_real_km > 0"),
    ('T6', 'Distancia estimada y recorrida (diferencia)', 'percent',
     f"SELECT ABS(100.0 * (SUM(distance_real_km) - SUM(distance_est_km)) / NULLIF(SUM(distance_est_km), 0)) "
     f"AS value FROM kpi_trips WHERE {TRIPS} AND distance_real_km > 0"),
    ('T7', 'Tiempo de recorrido contra el plan (diferencia)', 'percent',
     f"SELECT ABS(100.0 * (AVG(duration_real_min) - AVG(duration_est_min)) / NULLIF(AVG(duration_est_min), 0)) "
     f"AS value FROM kpi_trips WHERE {TRIPS} AND state = 'done' AND duration_real_min > 0"),
    ('T8', 'Incidencias', 'none',
     f"SELECT COUNT(*) AS value FROM kpi_alerts WHERE {ALERTS}"),
    ('S1', 'Integridad de los registros GPS', 'percent',
     "SELECT 100.0 * SUM(positions_stored) / NULLIF(SUM(positions_stored) + SUM(positions_rejected), 0) AS value "
     "FROM kpi_software WHERE $__timeFilter(day_start)"),
    ('S2', 'Exactitud de la sincronización con Traccar', 'percent',
     "SELECT 100.0 * SUM(audit_matched) / NULLIF(SUM(audit_total), 0) AS value "
     "FROM kpi_software WHERE $__timeFilter(day_start)"),
    ('S3', 'Tiempo de respuesta (p95)', 'ms',
     "SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS value "
     "FROM kpi_response WHERE $__timeFilter(sampled_at)"),
    ('S4', 'Detección correcta de incidencias', 'percent',
     f"SELECT 100.0 * COUNT(*) FILTER (WHERE detection_ok) / NULLIF(COUNT(*), 0) AS value "
     f"FROM kpi_trips WHERE {TRIPS} AND simulated AND expected_flags IS NOT NULL"),
]


class Board:
    """One dashboard: panels laid out in rows of a 24-column grid."""

    def __init__(self, uid, title, description, tags=()):
        self.uid, self.title, self.description, self.tags = uid, title, description, list(tags)
        self.panels, self.x, self.y, self.row_h, self.next_id = [], 0, 0, 0, 1
        self.variables = []
        self.annotations = []

    def add(self, panel, w, h):
        if self.x + w > 24:
            self.y += self.row_h
            self.x, self.row_h = 0, 0
        panel.update({'id': self.next_id, 'datasource': DS, 'gridPos': {'x': self.x, 'y': self.y, 'w': w, 'h': h}})
        self.next_id += 1
        self.x += w
        self.row_h = max(self.row_h, h)
        self.panels.append(panel)
        return panel

    def new_row(self, title):
        self.y += self.row_h
        self.x, self.row_h = 0, 0
        self.panels.append({'id': self.next_id, 'type': 'row', 'title': title, 'collapsed': False,
                            'gridPos': {'x': 0, 'y': self.y, 'w': 24, 'h': 1}, 'panels': []})
        self.next_id += 1
        self.y += 1

    def json(self, refresh='30s'):
        return {
            'uid': self.uid, 'title': self.title, 'description': self.description, 'tags': ['bus-tracking'] + self.tags,
            'schemaVersion': 39, 'version': 1, 'editable': False, 'graphTooltip': 1, 'liveNow': False,
            'refresh': refresh, 'timezone': 'America/Guayaquil', 'time': {'from': 'now-30d', 'to': 'now'},
            'timepicker': {'refresh_intervals': ['30s', '1m', '5m', '15m']},
            'links': [{'title': name, 'type': 'link', 'url': f'/d/{uid}', 'icon': 'dashboard', 'keepTime': True,
                       'includeVars': True, 'asDropdown': False, 'targetBlank': False}
                      for uid, name in LINKS if uid != self.uid],
            'templating': {'list': self.variables or filters()},
            'annotations': {'list': self.annotations},
            'panels': self.panels,
        }


def filters(extra=()):
    """The variables every dashboard has."""
    def query(name, label, sql):
        return {'name': name, 'label': label, 'type': 'query', 'datasource': DS, 'query': sql, 'refresh': 2,
                'multi': True, 'includeAll': True, 'current': {'text': 'All', 'value': '$__all'}, 'sort': 1}
    return [
        query('route', 'Línea', "SELECT route_code FROM kpi_routes WHERE active ORDER BY 1"),
        query('bus', 'Bus', "SELECT bus FROM (SELECT bus FROM kpi_trips UNION SELECT bus FROM kpi_alerts) b ORDER BY 1"),
        {'name': 'scope', 'label': 'Datos', 'type': 'custom', 'multi': False, 'includeAll': False,
         'query': 'Reales y simulados : all, Solo reales : real, Solo simulados : simulated',
         'current': {'text': 'Reales y simulados', 'value': 'all'},
         'options': [{'text': 'Reales y simulados', 'value': 'all', 'selected': True},
                     {'text': 'Solo reales', 'value': 'real', 'selected': False},
                     {'text': 'Solo simulados', 'value': 'simulated', 'selected': False}]},
    ] + list(extra)


def alert_annotation():
    return {'name': 'Alertas', 'datasource': DS, 'enable': False, 'iconColor': BAD, 'target': {
        'refId': 'Anno', 'datasource': DS, 'editorMode': 'code', 'format': 'table', 'rawQuery': True,
        'rawSql': f"SELECT happened_at AS time, {KIND_CASE} AS text, kind AS tags FROM kpi_alerts "
                  f"WHERE {ALERTS} AND origin = 'alert' ORDER BY 1"}}


# ------------------------------------------------------------------------------------------------ panels
def target(sql, fmt='table', ref='A'):
    return {'refId': ref, 'datasource': DS, 'editorMode': 'code', 'format': fmt, 'rawQuery': True, 'rawSql': sql}


def steps(code):
    good, ok, higher = THRESHOLDS[code]
    if higher:
        return [{'color': BAD, 'value': None}, {'color': WARN, 'value': ok}, {'color': GOOD, 'value': good}]
    return [{'color': GOOD, 'value': None}, {'color': WARN, 'value': good + 1e-9}, {'color': BAD, 'value': ok + 1e-9}]


NO_DATA = [{'type': 'special', 'options': {'match': 'null', 'result': {'text': 'Sin datos', 'color': '#6B7A80'}}}]


def stat(code, title, unit, sql, description=''):
    judged = code in THRESHOLDS
    return {
        'type': 'stat', 'title': f'{code} · {title}', 'description': description,
        'targets': [target(sql)],
        'fieldConfig': {'defaults': {
            'unit': unit, 'decimals': 0 if code == 'T8' else 1, 'noValue': 'Sin datos', 'mappings': NO_DATA,
            'color': {'mode': 'thresholds'} if judged else {'mode': 'fixed', 'fixedColor': INK},
            'thresholds': {'mode': 'absolute', 'steps': steps(code) if judged else [{'color': INK, 'value': None}]}},
            'overrides': []},
        'options': {'reduceOptions': {'calcs': ['lastNotNull'], 'fields': '', 'values': False},
                    'colorMode': 'background' if judged else 'none', 'graphMode': 'none', 'textMode': 'value',
                    'justifyMode': 'center', 'orientation': 'auto'},
    }


def timeseries(title, sql, colors=None, bars=False, unit=None, stack=False, description='', fill=18, max_=None):
    custom = {'drawStyle': 'bars' if bars else 'line', 'lineWidth': 2, 'fillOpacity': 80 if bars else fill,
              'showPoints': 'auto', 'spanNulls': True, 'barAlignment': 0,
              'stacking': {'mode': 'normal' if stack else 'none', 'group': 'A'}}
    defaults = {'custom': custom, 'color': {'mode': 'palette-classic'}}
    if unit:
        defaults['unit'] = unit
    if max_ is not None:
        defaults['max'], defaults['min'] = max_, 0
    overrides = [{'matcher': {'id': 'byName', 'options': name}, 'properties': [
        {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': color}}]} for name, color in (colors or {}).items()]
    return {'type': 'timeseries', 'title': title, 'description': description,
            'targets': [target(sql, 'time_series')],
            'fieldConfig': {'defaults': defaults, 'overrides': overrides},
            'options': {'legend': {'displayMode': 'list', 'placement': 'bottom', 'showLegend': True},
                        'tooltip': {'mode': 'multi', 'sort': 'none'}}}


def barchart(title, sql, colors=None, unit=None, stack=False, horizontal=False, description='', max_=None):
    defaults = {'custom': {'fillOpacity': 85, 'lineWidth': 0, 'gradientMode': 'none'}, 'color': {'mode': 'palette-classic'}}
    if unit:
        defaults['unit'] = unit
    if max_ is not None:
        defaults['max'], defaults['min'] = max_, 0
    overrides = [{'matcher': {'id': 'byName', 'options': name}, 'properties': [
        {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': color}}]} for name, color in (colors or {}).items()]
    return {'type': 'barchart', 'title': title, 'description': description, 'targets': [target(sql)],
            'fieldConfig': {'defaults': defaults, 'overrides': overrides},
            'options': {'orientation': 'horizontal' if horizontal else 'vertical', 'xTickLabelRotation': 0,
                        'stacking': 'normal' if stack else 'none', 'showValue': 'auto', 'barWidth': 0.8,
                        'groupWidth': 0.75, 'legend': {'displayMode': 'list', 'placement': 'bottom', 'showLegend': True},
                        'tooltip': {'mode': 'multi', 'sort': 'none'}}}


def piechart(title, sql, description=''):
    overrides = [{'matcher': {'id': 'byName', 'options': name}, 'properties': [
        {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': SERIES[i % len(SERIES)]}}]}
        for i, name in enumerate(KINDS.values())]
    return {'type': 'piechart', 'title': title, 'description': description, 'targets': [target(sql)],
            'fieldConfig': {'defaults': {'color': {'mode': 'palette-classic'}}, 'overrides': overrides},
            'options': {'pieType': 'donut', 'displayLabels': ['percent'], 'reduceOptions': {
                'calcs': ['lastNotNull'], 'fields': '', 'values': True},
                'legend': {'displayMode': 'table', 'placement': 'right', 'showLegend': True, 'values': ['value']},
                'tooltip': {'mode': 'single'}}}


def table(title, sql, overrides=None, description='', sort=None, cell=None):
    defaults = {'custom': {'align': 'auto', 'cellOptions': cell or {'type': 'auto'}, 'filterable': True},
                'noValue': '—'}
    return {'type': 'table', 'title': title, 'description': description, 'targets': [target(sql)],
            'fieldConfig': {'defaults': defaults, 'overrides': overrides or []},
            'options': {'showHeader': True, 'cellHeight': 'sm',
                        'sortBy': sort or [], 'footer': {'show': False}}}


def override(name, **props):
    ids = {'unit': 'unit', 'decimals': 'decimals', 'width': 'custom.width', 'mappings': 'mappings',
           'cell': 'custom.cellOptions', 'thresholds': 'thresholds', 'color': 'color', 'min': 'min', 'max': 'max'}
    return {'matcher': {'id': 'byName', 'options': name},
            'properties': [{'id': ids[k], 'value': v} for k, v in props.items()]}


STATES = {'done': ('Completo', GOOD), 'incomplete': ('Incompleto', BAD)}
STATE_MAP = [{'type': 'value', 'options': {k: {'text': v[0], 'color': v[1]} for k, v in STATES.items()}}]
STOP_MAP = [{'type': 'value', 'options': {
    'on_time': {'text': 'A tiempo', 'color': GOOD}, 'late': {'text': 'Tarde', 'color': BAD},
    'early': {'text': 'Adelantado', 'color': TEAL}, 'skipped': {'text': 'Omitida', 'color': BAD},
    'pending': {'text': 'Pendiente', 'color': INK}}}]
DELAY_CELLS = {'type': 'color-background', 'mode': 'basic'}
BLANK = [{'type': 'special', 'options': {'match': 'null', 'result': {'text': '', 'color': 'transparent'}}}]
DELAY_STEPS = {'mode': 'absolute', 'steps': [{'color': 'rgba(29,107,68,0.35)', 'value': None},
                                             {'color': 'rgba(201,138,0,0.55)', 'value': 5.0001},
                                             {'color': 'rgba(161,34,27,0.65)', 'value': 10.0001}]}


# ------------------------------------------------------------------------------------------------ dashboards
LINKS = [('bus-resumen', 'Resumen'), ('bus-rutas', 'Rutas'), ('bus-puntualidad', 'Puntualidad'),
         ('bus-recorridos', 'Recorridos'), ('bus-incidencias', 'Incidencias'), ('bus-calidad', 'Calidad del sistema')]
BEFORE = ("$__timeFrom()::timestamptz - ($__timeTo()::timestamptz - $__timeFrom()::timestamptz)")


def resumen():
    board = Board('bus-resumen', 'Resumen', 'Los doce indicadores del proyecto, con su estado y la comparación con el '
                  'periodo anterior.')
    board.variables = filters()
    board.annotations = [alert_annotation()]
    board.new_row('Servicio de transporte (T1 a T8)')
    for code, title, unit, sql in INDICATORS[:8]:
        board.add(stat(code, title, unit, sql), 6, 4)
    board.new_row('Calidad del software (S1 a S4)')
    for code, title, unit, sql in INDICATORS[8:]:
        board.add(stat(code, title, unit, sql), 6, 4)
    board.new_row('Evolución')
    board.add(timeseries('Recorridos por día', f"""SELECT {DAY.format(col='starts_at')} AS time,
        COUNT(*) FILTER (WHERE state = 'done') AS "Completos", COUNT(*) FILTER (WHERE state = 'incomplete') AS "Incompletos"
        FROM kpi_trips WHERE {TRIPS} GROUP BY 1 ORDER BY 1""", {'Completos': GOOD, 'Incompletos': BAD}, bars=True,
        stack=True), 12, 8)
    board.add(timeseries('Puntualidad por día (%)', f"""SELECT {DAY.format(col='starts_at')} AS time,
        100.0 * COUNT(*) FILTER (WHERE status <> 'late') / NULLIF(COUNT(*), 0) AS "Puntualidad"
        FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY 1 ORDER BY 1""", {'Puntualidad': GARNET},
        unit='percent', max_=100), 12, 8)

    def period(col, which):
        if which == 'now':
            return f"$__timeFilter({col})"
        return f"{col} >= {BEFORE} AND {col} < $__timeFrom()::timestamptz"

    def compare(code, title, unit_text, expr, source, where_now_extra=''):
        """One row of the comparison table: this period against the one just before."""
        def one(which):
            where = {'T1': TRIPS, 'T2': STOPS, 'T3': STOPS, 'T4': STOPS, 'T8': ALERTS}[code]
            col = 'happened_at' if code == 'T8' else 'starts_at'
            where = where.replace(f"$__timeFilter({col})", period(col, which))
            return f"(SELECT {expr} FROM {source} WHERE {where}{where_now_extra})"
        return (f"SELECT '{code} · {title}' AS \"Indicador\", '{unit_text}' AS \"Unidad\", ROUND({one('now')}::numeric, 1) "
                f"AS \"Este periodo\", ROUND({one('before')}::numeric, 1) AS \"Periodo anterior\"")
    rows = [
        compare('T1', 'Cumplimiento de ruta', '%',
                "100.0 * COUNT(*) FILTER (WHERE state = 'done') / NULLIF(COUNT(*), 0)", 'kpi_trips'),
        compare('T2', 'Puntualidad', '%',
                "100.0 * COUNT(*) FILTER (WHERE status <> 'late') / NULLIF(COUNT(*), 0)", 'kpi_trip_stops',
                f" AND {REACHED}"),
        compare('T3', 'Retraso promedio', 'min', "AVG(delay_min)", 'kpi_trip_stops', " AND status = 'late'"),
        compare('T4', 'Paradas atendidas', '%',
                f"100.0 * COUNT(*) FILTER (WHERE {REACHED}) / NULLIF(COUNT(*), 0)", 'kpi_trip_stops'),
        compare('T8', 'Incidencias', 'n', "COUNT(*)", 'kpi_alerts'),
    ]
    sql = ' UNION ALL '.join(rows)
    sql = f"SELECT *, \"Este periodo\" - \"Periodo anterior\" AS \"Cambio\" FROM ({sql}) c ORDER BY 1"
    board.add(table('Este periodo contra el anterior', sql, [override('Cambio', decimals=1)],
                    description='El periodo anterior es el de igual duración justo antes del elegido.'), 24, 7)
    return board


def rutas():
    board = Board('bus-rutas', 'Rutas', 'Cada línea frente a las demás: puntualidad, cumplimiento, retraso y distancia.')
    board.variables = filters()
    board.add(barchart('Puntualidad por línea (%)', f"""SELECT route_code AS "Línea",
        100.0 * COUNT(*) FILTER (WHERE status <> 'late') / NULLIF(COUNT(*), 0) AS "Puntualidad"
        FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY 1 ORDER BY 1""", {'Puntualidad': GARNET},
        unit='percent', max_=100), 8, 8)
    board.add(barchart('Cumplimiento de ruta por línea (%)', f"""SELECT route_code AS "Línea",
        100.0 * COUNT(*) FILTER (WHERE state = 'done') / NULLIF(COUNT(*), 0) AS "Cumplimiento"
        FROM kpi_trips WHERE {TRIPS} GROUP BY 1 ORDER BY 1""", {'Cumplimiento': TEAL}, unit='percent', max_=100), 8, 8)
    board.add(barchart('Retraso promedio por línea (min)', f"""SELECT route_code AS "Línea",
        AVG(delay_min) AS "Retraso" FROM kpi_trip_stops WHERE {STOPS} AND status = 'late' GROUP BY 1 ORDER BY 1""",
        {'Retraso': BROWN}, unit='m'), 8, 8)
    board.add(barchart('Distancia estimada y recorrida por línea (km)', f"""SELECT route_code AS "Línea",
        SUM(distance_est_km) AS "Estimada", SUM(distance_real_km) AS "Recorrida"
        FROM kpi_trips WHERE {TRIPS} AND distance_real_km > 0 GROUP BY 1 ORDER BY 1""",
        {'Estimada': YELLOW, 'Recorrida': INK}, unit='km'), 12, 8)
    board.add(barchart('Alertas por línea', f"""SELECT COALESCE(route_code, 'Sin línea') AS "Línea", COUNT(*) AS "Alertas"
        FROM kpi_alerts WHERE {ALERTS} GROUP BY 1 ORDER BY 1""", {'Alertas': BAD}), 12, 8)
    sql = f"""WITH trips AS (
            SELECT route_code, COUNT(*) AS trips, 100.0 * COUNT(*) FILTER (WHERE state = 'done') / COUNT(*) AS compliance,
                   COALESCE(SUM(distance_est_km) FILTER (WHERE distance_real_km > 0), 0) AS est_km,
                   COALESCE(SUM(distance_real_km), 0) AS real_km
              FROM kpi_trips WHERE {TRIPS} GROUP BY 1
        ), stops AS (
            SELECT route_code, 100.0 * COUNT(*) FILTER (WHERE status <> 'late') / COUNT(*) AS punctuality,
                   AVG(delay_min) FILTER (WHERE status = 'late') AS delay
              FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY 1
        ), alerts AS (
            SELECT route_code, COUNT(*) AS alerts FROM kpi_alerts WHERE {ALERTS} GROUP BY 1
        )
        SELECT r.route_code AS "Línea", r.route_name AS "Nombre", COALESCE(trips.trips, 0) AS "Recorridos",
               ROUND(trips.compliance::numeric, 1) AS "Cumplimiento %", ROUND(stops.punctuality::numeric, 1) AS "Puntualidad %",
               ROUND(stops.delay::numeric, 1) AS "Retraso prom. (min)", ROUND(trips.est_km::numeric, 1) AS "Km estimados",
               ROUND(trips.real_km::numeric, 1) AS "Km recorridos", COALESCE(alerts.alerts, 0) AS "Alertas"
          FROM kpi_routes r LEFT JOIN trips USING (route_code) LEFT JOIN stops USING (route_code)
          LEFT JOIN alerts USING (route_code) WHERE r.active AND r.route_code IN ($route) ORDER BY 1"""
    board.add(table('Comparación de líneas', sql), 24, 7)
    return board


def puntualidad():
    board = Board('bus-puntualidad', 'Puntualidad', 'Cuándo y dónde se retrasan los buses.')
    board.variables = filters()
    board.annotations = [alert_annotation()]
    board.add(timeseries('Puntualidad por día (%)', f"""SELECT {DAY.format(col='starts_at')} AS time,
        100.0 * COUNT(*) FILTER (WHERE status <> 'late') / NULLIF(COUNT(*), 0) AS "Puntualidad"
        FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY 1 ORDER BY 1""", {'Puntualidad': GARNET},
        unit='percent', max_=100), 12, 8)
    board.add(timeseries('Retraso promedio por día (min)', f"""SELECT {DAY.format(col='starts_at')} AS time,
        AVG(delay_min) AS "Retraso promedio" FROM kpi_trip_stops WHERE {STOPS} AND status = 'late' GROUP BY 1 ORDER BY 1""",
        {'Retraso promedio': BROWN}, unit='m'), 12, 8)
    board.add(barchart('Cómo llegan los buses a las paradas', f"""SELECT label AS "Llegada", n AS "Paradas" FROM (
        SELECT CASE WHEN delay_min < -5 THEN 0 WHEN delay_min <= 5 THEN 1 WHEN delay_min <= 10 THEN 2
                    WHEN delay_min <= 15 THEN 3 WHEN delay_min <= 20 THEN 4 ELSE 5 END AS ord,
               CASE WHEN delay_min < -5 THEN 'Adelantado (más de 5 min)' WHEN delay_min <= 5 THEN 'A tiempo (hasta 5 min)'
                    WHEN delay_min <= 10 THEN 'Retraso de 5 a 10 min' WHEN delay_min <= 15 THEN 'Retraso de 10 a 15 min'
                    WHEN delay_min <= 20 THEN 'Retraso de 15 a 20 min' ELSE 'Retraso de más de 20 min' END AS label,
               COUNT(*) AS n
          FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY 1, 2) b ORDER BY ord""", {'Paradas': GARNET}), 12, 8)
    board.add(barchart('Las paradas con más retraso (min)', f"""SELECT stop_name || ' (' || route_code || ')' AS "Parada",
        AVG(delay_min) AS "Retraso promedio" FROM kpi_trip_stops WHERE {STOPS} AND {REACHED}
        GROUP BY stop_name, route_code ORDER BY 2 DESC LIMIT 12""", {'Retraso promedio': BROWN}, unit='m',
        horizontal=True), 12, 8)
    hours = range(5, 23)
    columns = ', '.join(f"AVG(delay_min) FILTER (WHERE local_hour = {h}) AS \"{h:02d} h\"" for h in hours)
    sql = f"""SELECT stop_name AS "Parada", route_code AS "Línea", {columns}
        FROM kpi_trip_stops WHERE {STOPS} AND {REACHED} GROUP BY stop_name, route_code
        ORDER BY route_code, MIN(sequence)"""
    overrides = [override(f'{h:02d} h', unit='m', decimals=1, cell=DELAY_CELLS, thresholds=DELAY_STEPS, width=62,
                          mappings=BLANK)
                 for h in hours]
    board.add(table('Retraso promedio por parada y hora de salida (min)', sql, overrides,
                    description='Verde hasta 5 min, ámbar hasta 10 min, rojo más allá. La hora es la planificada, hora local.'),
              24, 9)
    return board


def recorridos():
    board = Board('bus-recorridos', 'Recorridos', 'Cada recorrido programado: lo que se planeó y lo que pasó.')
    trip_var = {'name': 'trip', 'label': 'Recorrido', 'type': 'query', 'datasource': DS, 'refresh': 2, 'multi': False,
                'includeAll': False, 'sort': 0, 'query': f"""SELECT 'Recorrido ' || trip_id || ' · ' || route_code || ' · ' ||
        to_char(local_day, 'DD/MM') || CASE WHEN simulated THEN ' (simulado)' ELSE '' END AS __text, trip_id::text AS __value
        FROM kpi_trips WHERE {CLOSED} AND route_code IN ($route) AND bus IN ($bus) ORDER BY starts_at DESC LIMIT 100"""}
    board.variables = filters([trip_var])
    sql = f"""SELECT trip_id AS "N.º", to_char(local_day, 'YYYY-MM-DD') AS "Fecha", route_code AS "Línea", bus AS "Bus", state AS "Estado",
        CASE WHEN simulated THEN 'Simulado' ELSE 'Real' END AS "Origen", stops_visited AS "Paradas atendidas",
        stops_total AS "Paradas", stops_late AS "Con retraso", stops_skipped AS "Omitidas",
        ROUND(delay_end_min::numeric, 1) AS "Retraso al final (min)", ROUND(distance_est_km::numeric, 1) AS "Km estimados",
        ROUND(distance_real_km::numeric, 1) AS "Km recorridos", COALESCE(NULLIF(detected_flags, ''), '—') AS "Detectado"
        FROM kpi_trips WHERE {TRIPS} ORDER BY starts_at DESC LIMIT 200"""
    board.add(table('Recorridos del periodo', sql, [override('Estado', mappings=STATE_MAP,
                                                              cell={'type': 'color-text'})]), 24, 9)
    stops_sql = """SELECT sequence AS "N.º", stop_name AS "Parada", to_char(planned_time - interval '5 hours', 'HH24:MI') AS "Hora planificada",
        to_char(actual_time - interval '5 hours', 'HH24:MI') AS "Hora real", status AS "Estado", ROUND(delay_min::numeric, 1) AS "Retraso (min)"
        FROM kpi_trip_stops WHERE trip_id = $trip ORDER BY sequence"""
    board.add(table('Paradas del recorrido elegido', stops_sql, [
        override('Estado', mappings=STOP_MAP, cell={'type': 'color-text'}),
        override('Retraso (min)', cell=DELAY_CELLS, thresholds=DELAY_STEPS)]), 10, 10)
    positions = {'refId': 'A', 'datasource': DS, 'editorMode': 'code', 'format': 'table', 'rawQuery': True,
                 'rawSql': "SELECT fix_time AS time, latitude, longitude, speed AS \"Velocidad\" FROM kpi_positions "
                           "WHERE trip_id = $trip ORDER BY fix_time"}
    stops = {'refId': 'B', 'datasource': DS, 'editorMode': 'code', 'format': 'table', 'rawQuery': True,
             'rawSql': "SELECT s.stop_name AS \"Parada\", s.latitude, s.longitude FROM kpi_route_stops s "
                       "JOIN kpi_trips t ON t.route_code = s.route_code WHERE t.trip_id = $trip ORDER BY s.sequence"}
    layer_path = {'type': 'route', 'name': 'Trazado', 'config': {'style': {
        'color': {'fixed': GARNET}, 'opacity': 0.9, 'size': {'fixed': 3}, 'lineWidth': 3, 'rotation': {'fixed': 0, 'min': -360, 'max': 360, 'mode': 'mod'}}},
        'filterData': {'id': 'byRefId', 'options': 'A'}, 'location': {'mode': 'coords', 'latitude': 'latitude',
                                                                       'longitude': 'longitude'}}
    layer_stops = {'type': 'markers', 'name': 'Paradas', 'config': {'showLegend': False, 'style': {
        'color': {'fixed': YELLOW}, 'opacity': 1, 'size': {'fixed': 9}, 'symbol': {'fixed': 'img/icons/marker/circle.svg', 'mode': 'fixed'},
        'text': {'field': 'Parada', 'fixed': '', 'mode': 'field'}, 'textConfig': {'fontSize': 11, 'offsetY': -14, 'textAlign': 'center', 'textBaseline': 'middle'}}},
        'filterData': {'id': 'byRefId', 'options': 'B'}, 'location': {'mode': 'coords', 'latitude': 'latitude',
                                                                       'longitude': 'longitude'}}
    board.add({'type': 'geomap', 'title': 'Trazado del recorrido elegido y sus paradas',
               'description': 'Las posiciones GPS recibidas durante el recorrido (granate) y las paradas de la línea (amarillo).',
               'targets': [positions, stops],
               'fieldConfig': {'defaults': {}, 'overrides': []},
               'options': {'view': {'id': 'fit', 'allLayers': True, 'zoom': 14, 'lat': -1.25, 'lon': -78.62},
                           'controls': {'showZoom': True, 'mouseWheelZoom': True, 'showAttribution': True},
                           'basemap': {'type': 'osm-standard', 'name': 'OpenStreetMap'}, 'layers': [layer_path, layer_stops],
                           'tooltip': {'mode': 'details'}}}, 14, 10)
    return board


def incidencias():
    board = Board('bus-incidencias', 'Incidencias', 'Qué falla, cuánto y dónde: alertas de las reglas e incidentes de los '
                  'choferes.')
    board.variables = filters()
    board.annotations = [alert_annotation()]
    kinds = f"SELECT {KIND_CASE} AS \"Tipo\", COUNT(*) AS \"Cantidad\" FROM kpi_alerts WHERE {ALERTS} GROUP BY kind"
    board.add(piechart('Incidencias por tipo', kinds + " ORDER BY 2 DESC"), 8, 9)
    pareto = f"""SELECT "Tipo", "Cantidad", ROUND(100.0 * SUM("Cantidad") OVER (ORDER BY "Cantidad" DESC, "Tipo")
                                                / SUM("Cantidad") OVER (), 1) AS "% acumulado"
        FROM ({kinds}) k ORDER BY "Cantidad" DESC, "Tipo\""""
    board.add(table('Pareto: pocos tipos causan la mayoría', pareto, [
        override('% acumulado', unit='percent', min=0, max=100, cell={'type': 'gauge', 'mode': 'gradient'},
                 color={'mode': 'fixed', 'fixedColor': GARNET}),
        ],
        description='Los tipos están ordenados de mayor a menor; el porcentaje acumulado dice cuántos tipos explican '
                    'el 80 % de lo que ocurre (principio de Pareto).'), 8, 9)
    board.add(barchart('Incidencias por línea y origen', f"""SELECT COALESCE(route_code, 'Sin línea') AS "Línea",
        COUNT(*) FILTER (WHERE origin = 'alert') AS "Alertas", COUNT(*) FILTER (WHERE origin = 'incident') AS "Incidentes"
        FROM kpi_alerts WHERE {ALERTS} GROUP BY 1 ORDER BY 1""", {'Alertas': GARNET, 'Incidentes': YELLOW}, stack=True), 8, 9)
    board.add(timeseries('Frecuencia por día', f"""SELECT {DAY.format(col='happened_at')} AS time,
        COUNT(*) FILTER (WHERE origin = 'alert') AS "Alertas", COUNT(*) FILTER (WHERE origin = 'incident') AS "Incidentes"
        FROM kpi_alerts WHERE {ALERTS} GROUP BY 1 ORDER BY 1""", {'Alertas': GARNET, 'Incidentes': YELLOW}, bars=True,
        stack=True), 24, 8)
    return board


def calidad():
    board = Board('bus-calidad', 'Calidad del sistema', 'Los cuatro indicadores del software (S1 a S4) y su evolución.')
    board.variables = filters()
    for code, title, unit, sql in INDICATORS[8:]:
        board.add(stat(code, title, unit, sql), 6, 5)
    board.add(timeseries('Posiciones guardadas y rechazadas por día', """SELECT day_start AS time,
        positions_stored AS "Guardadas", positions_rejected AS "Rechazadas" FROM kpi_software
        WHERE $__timeFilter(day_start) ORDER BY 1""", {'Guardadas': TEAL, 'Rechazadas': BAD}, bars=True, stack=True), 12, 8)
    board.add(timeseries('Tiempo de respuesta (ms)', f"""SELECT {DAY.format(col='sampled_at')} AS time,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY ms) AS "Mediana",
        percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS "p95"
        FROM kpi_response WHERE $__timeFilter(sampled_at) GROUP BY 1 ORDER BY 1""",
        {'Mediana': TEAL, 'p95': GARNET}, unit='ms'), 12, 8)
    board.add(timeseries('Auditoría de sincronización con Traccar (%)', """SELECT day_start AS time,
        100.0 * audit_matched / NULLIF(audit_total, 0) AS "Exactitud" FROM kpi_software
        WHERE $__timeFilter(day_start) AND audit_total > 0 ORDER BY 1""", {'Exactitud': INDIGO}, unit='percent', max_=100), 12, 8)
    board.add(table('Resultado de la auditoría, por día', """SELECT to_char(local_day, 'YYYY-MM-DD') AS "Día", audit_total AS "Posiciones comparadas",
        audit_matched AS "Coinciden", audit_total - audit_matched AS "Difieren"
        FROM kpi_software WHERE $__timeFilter(day_start) AND audit_total > 0 ORDER BY 1 DESC""", []), 12, 8)
    board.add(timeseries('Detección correcta en los recorridos simulados (%)', """SELECT day_start AS time,
        100.0 * detected_ok / NULLIF(simulated_trips, 0) AS "Detección correcta" FROM kpi_software
        WHERE $__timeFilter(day_start) AND simulated_trips > 0 ORDER BY 1""", {'Detección correcta': OLIVE},
        unit='percent', max_=100), 24, 8)
    return board


BOARDS = [('01-resumen', resumen), ('02-rutas', rutas), ('03-puntualidad', puntualidad),
          ('04-recorridos', recorridos), ('05-incidencias', incidencias), ('06-calidad', calidad)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in BOARDS:
        data = build().json()
        (OUT / f'{name}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
        print(name, len([p for p in data['panels'] if p['type'] != 'row']), 'panels')


if __name__ == '__main__':
    main()
