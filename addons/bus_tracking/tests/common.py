from odoo.tests.common import TransactionCase

# (name, lat, lon): ~1 km apart so radii never overlap
STOPS = [
    ('Terminal', -33.4500, -70.6600),
    ('Plaza', -33.4540, -70.6500),
    ('Hospital', -33.4600, -70.6400),
]


def traccar_position(device_id, fix_time, lat, lon, speed_knots=0.0, **extra):
    pos = {
        'deviceId': device_id,
        'fixTime': fix_time,
        'latitude': lat,
        'longitude': lon,
        'speed': speed_knots,
        'course': 90.0,
    }
    pos.update(extra)
    return pos


class BusCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route = cls.env['bus.route'].create({
            'name': 'Linea Centro',
            'code': 'L1',
            'stop_ids': [
                (0, 0, {'sequence': i * 10, 'name': name, 'latitude': lat,
                        'longitude': lon, 'radius': 80})
                for i, (name, lat, lon) in enumerate(STOPS, start=1)
            ],
        })
        cls.bus = cls.env['bus.vehicle'].create({
            'name': 'Bus 1',
            'route_id': cls.route.id,
            'traccar_device_id': 7,
            'traccar_unique_id': 'BUS007',
        })
        cls.stop = {s.name: s for s in cls.route.stop_ids}
