import logging
import re
from datetime import datetime, timedelta

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 10
# Traccar tokens expire; one asked with the password can last this long. Revoke it in Traccar if it leaks.
TOKEN_DAYS = 3650
TOKEN_RE = re.compile(r'^[A-Za-z0-9_\-.=]+$')


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
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            # A proxy error page answered instead of Traccar.
            raise UserError(_("Traccar did not answer with JSON: %s", resp.text[:200]))

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
    def get_positions(self, device_id, since, until):
        """The positions Traccar holds for a device between two UTC datetimes."""
        stamp = '%Y-%m-%dT%H:%M:%SZ'
        return self._get('/positions', params={
            'deviceId': device_id, 'from': since.strftime(stamp), 'to': until.strftime(stamp)}) or []

    @api.model
    def delete_positions(self, device_id, until):
        """Delete the positions Traccar holds for a device before a UTC datetime."""
        stamp = '%Y-%m-%dT%H:%M:%SZ'
        return self._call('delete', '/positions', params={
            'deviceId': device_id, 'from': '1970-01-01T00:00:00Z', 'to': until.strftime(stamp)})

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
        self.switch_to_token()
        return True

    @api.model
    def _request_token(self, conf):
        """A long-lived API token of the stored user. Traccar answers it as plain text, not JSON."""
        expiration = (datetime.utcnow() + timedelta(days=TOKEN_DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            resp = requests.post('%s/api/session/token' % conf['url'], data={'expiration': expiration},
                                 auth=(conf['user'], conf['password']), timeout=TIMEOUT)
        except requests.RequestException as e:
            raise UserError(_("Cannot reach Traccar: %s", e))
        token = (resp.text or '').strip() if resp.ok else ''
        if not TOKEN_RE.match(token):
            raise UserError(_("Traccar did not give an API token (error %s).", resp.status_code))
        return token

    @api.model
    def switch_to_token(self):
        """Keep an API token instead of the administrator password, so a copy of the database does not
        hold the password. Does nothing when a token is already stored or there is no password."""
        conf = self._get_conf()
        if conf['token'] or not (conf['user'] and conf['password']):
            return False
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('bus_tracking.traccar_token', self._request_token(conf))
        icp.set_param('bus_tracking.traccar_password', False)
        return True
