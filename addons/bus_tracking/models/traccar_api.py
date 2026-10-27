import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 10


class BusTraccarApi(models.AbstractModel):
    _name = 'bus.traccar.api'
    _description = 'Traccar REST API client'

    @api.model
    def _get_conf(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'url': (icp.get_param('bus_tracking.traccar_url') or '').rstrip('/'),
            'user': icp.get_param('bus_tracking.traccar_user') or '',
            'password': icp.get_param('bus_tracking.traccar_password') or '',
            'token': icp.get_param('bus_tracking.traccar_token') or '',
        }

    @api.model
    def is_configured(self):
        conf = self._get_conf()
        return bool(conf['url'] and (conf['token'] or conf['user']))

    @api.model
    def _call(self, verb, path, params=None, json=None, conf=None, anonymous=False):
        conf = conf or self._get_conf()
        if not conf['url']:
            raise UserError(_("Traccar URL is not configured."))
        headers = {'Accept': 'application/json'}
        auth = None
        if not anonymous:
            if conf['token']:
                headers['Authorization'] = 'Bearer %s' % conf['token']
            else:
                auth = (conf['user'], conf['password'])
        kwargs = {'headers': headers, 'auth': auth, 'params': params, 'timeout': TIMEOUT}
        if json is not None:
            kwargs['json'] = json
        try:
            resp = getattr(requests, verb)('%s/api%s' % (conf['url'], path), **kwargs)
        except requests.RequestException as e:
            raise UserError(_("Cannot reach Traccar: %s", e))
        if resp.status_code == 401:
            raise UserError(_("Traccar rejected the credentials."))
        if not resp.ok:
            raise UserError(_("Traccar error %(code)s: %(body)s", code=resp.status_code, body=resp.text[:200]))
        return resp.json() if resp.content else {}

    @api.model
    def _get(self, path, params=None, conf=None):
        return self._call('get', path, params=params, conf=conf)

    @api.model
    def get_devices(self, conf=None):
        return self._get('/devices', conf=conf)

    @api.model
    def get_latest_positions(self):
        """Latest known position of every device."""
        return self._get('/positions')

    @api.model
    def create_device(self, name, unique_id):
        return self._call('post', '/devices', json={'name': name, 'uniqueId': unique_id})

    @api.model
    def bootstrap_admin(self, email, password):
        """First run: register Traccar's first user (it becomes the administrator),
        remember its credentials and close self-registration. Does nothing when
        credentials are already stored."""
        if self.is_configured():
            return False
        icp = self.env['ir.config_parameter'].sudo()
        self._call('post', '/users', json={'name': 'admin', 'email': email, 'password': password},
                   anonymous=True)
        icp.set_param('bus_tracking.traccar_user', email)
        icp.set_param('bus_tracking.traccar_password', password)
        server = self._get('/server')
        server['registration'] = False
        self._call('put', '/server', json=server)
        return True
