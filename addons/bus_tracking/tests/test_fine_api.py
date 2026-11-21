import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from ..controllers.driver_api import account_limiter, login_limiter
from .test_driver_auth import make_driver

LOGIN = '/bus_tracking/driver/login'
FINES = '/bus_tracking/driver/fines'
APPEAL = '/bus_tracking/driver/fines/appeal'


@tagged('post_install', '-at_install')
class TestFineDriverApi(HttpCase):
    """The tablet lists the confirmed fines of its driver and sends one statement per fine."""

    def setUp(self):
        super().setUp()
        login_limiter.reset()
        account_limiter.reset()
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
        self.driver = make_driver(self.env, login='chofer_api_multas')
        self.other = make_driver(self.env, login='otro_api_multas')
        route = self.env['bus.route'].create({'name': 'Linea API', 'code': 'LA'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus API', 'route_id': route.id})
        self.speeding = self.env.ref('bus_tracking.fine_type_speeding')
        self.token = self.login('chofer_api_multas')

    def login(self, login):
        resp = self.post(LOGIN, {'login': login, 'password': 'clave-segura-1'})
        return resp.json()['token']

    def post(self, url, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        resp = self.url_open(url, data=json.dumps(data if data is not None else {}), headers=headers)
        self.env.invalidate_all()
        return resp

    def fine(self, state='new', driver=None, **vals):
        values = {
            'type_id': self.speeding.id, 'rule': 'speeding', 'severity': 'serious',
            'driver_id': (driver or self.driver).id, 'vehicle_id': self.bus.id,
            'occurred_at': fields.Datetime.now() - timedelta(hours=2), 'amount_proposed': 25.0,
            'evidence_json': json.dumps({'facts': {'threshold': 70, 'limit': 50, 'seconds': 45, 'min_seconds': 30,
                                                   'max': 84, 'avg': 79, 'meters': 900}}),
            'checks_json': json.dumps([{'key': 'threshold', 'ok': True, 'params': {}}]),
        }
        values.update(vals)
        fine = self.env['bus.fine'].sudo().create(values)
        if state == 'fined':
            fine.action_fine()
        return fine

    def test_needs_a_session(self):
        self.assertEqual(self.post(FINES).status_code, 401)
        self.assertEqual(self.post(APPEAL, {'id': 1, 'text': 'x'}).status_code, 401)

    def test_only_confirmed_fines_of_the_driver_are_listed(self):
        confirmed = self.fine('fined')
        self.fine('new')                                   # a proposal in review is not the driver's business yet
        self.fine('fined', driver=self.other)
        resp = self.post(FINES, {'lang': 'es'}, token=self.token)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn('demo', data)
        self.assertEqual([f['id'] for f in data['fines']], confirmed.ids)
        item = data['fines'][0]
        self.assertEqual((item['state'], item['amount'], item['currency']), ('fined', 25.0, '$'))
        self.assertTrue(item['can_appeal'])
        self.assertIn('84', item['summary'])
        self.assertEqual(item['checks'][0]['ok'], True)
        self.assertIsNone(item['appeal_text'])

    def test_appeal_once(self):
        fine = self.fine('fined')
        resp = self.post(APPEAL, {'id': fine.id, 'text': 'Llevaba a un pasajero al hospital'}, token=self.token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['fine']['state'], 'appealed')
        self.assertEqual(fine.state, 'appealed')
        self.assertIn(self.driver.partner_id, fine.message_ids.mapped('author_id'))
        again = self.post(APPEAL, {'id': fine.id, 'text': 'Otra vez'}, token=self.token)
        self.assertEqual((again.status_code, again.json()['error']), (409, 'closed'))

    def test_appeal_checks_the_body(self):
        fine = self.fine('fined')
        for body in ({'id': fine.id}, {'id': fine.id, 'text': '   '}, {'id': str(fine.id), 'text': 'x'},
                     {'id': fine.id, 'text': 'x' * 1001}, {'id': True, 'text': 'x'}):
            with self.subTest(body=body):
                self.assertEqual(self.post(APPEAL, body, token=self.token).status_code, 400)
        self.assertEqual(fine.state, 'fined')

    def test_cannot_appeal_the_fine_of_someone_else_or_a_proposal(self):
        theirs = self.fine('fined', driver=self.other)
        proposal = self.fine('new')
        for fine in (theirs, proposal):
            with self.subTest(fine=fine.id):
                resp = self.post(APPEAL, {'id': fine.id, 'text': 'No fui yo'}, token=self.token)
                self.assertEqual(resp.status_code, 404)
        self.assertEqual((theirs.state, proposal.state), ('fined', 'new'))

    def test_after_the_deadline_the_appeal_is_closed(self):
        fine = self.fine('fined')
        fine.sudo().write({'appeal_deadline': fields.Datetime.now() - timedelta(minutes=1)})
        self.assertFalse(self.post(FINES, token=self.token).json()['fines'][0]['can_appeal'])
        resp = self.post(APPEAL, {'id': fine.id, 'text': 'Tarde'}, token=self.token)
        self.assertEqual(resp.status_code, 409)

    def test_the_answer_reaches_the_driver_once_resolved(self):
        fine = self.fine('fined')
        self.post(APPEAL, {'id': fine.id, 'text': 'El GPS falló'}, token=self.token)
        fine.appeal_answer = 'Se revisó el GPS del bus: falló ese día.'
        self.assertIsNone(self.post(FINES, token=self.token).json()['fines'][0]['appeal_answer'])
        fine.sudo().action_accept_appeal()
        item = self.post(FINES, token=self.token).json()['fines'][0]
        self.assertEqual((item['state'], item['appeal_result'], item['amount']), ('discarded', 'accepted', 0.0))
        self.assertEqual(item['appeal_answer'], 'Se revisó el GPS del bus: falló ese día.')
