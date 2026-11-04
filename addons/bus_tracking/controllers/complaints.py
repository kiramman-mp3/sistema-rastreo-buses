import hmac
import re
import time

from odoo import http
from odoo.http import request
from odoo.tools import misc

from ..models.bus_complaint import KINDS, MAX_DESCRIPTION
from .portal import RateLimiter, portal_context, public_routes, render_portal

MIN_DESCRIPTION = 10
MIN_FILL_SECONDS = 3              # a person cannot read the form and write 10 characters faster
MAX_FORM_AGE = 24 * 3600
MAX_BODY_BYTES = 20000
SUBMIT_LIMIT = 5                  # complaints per IP and hour, per worker process
SUBMIT_WINDOW = 3600.0

EMAIL_RE = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$')
PHONE_RE = re.compile(r'^[0-9+()\-\s]{6,30}$')
FOLIO_RE = re.compile(r'^Q-\d{5,}$')
SCOPE = 'bus_tracking.complaint_form'

submit_limiter = RateLimiter(SUBMIT_LIMIT, SUBMIT_WINDOW)


def _clean(text, limit):
    """Postgres rejects NUL characters; also trim and cap the length."""
    return (text or '').replace('\x00', '').strip()[:limit]


def _sign(ts):
    return misc.hmac(request.env(su=True), SCOPE, str(ts))


def new_form_token():
    ts = int(time.time())
    return '%d.%s' % (ts, _sign(ts))


def token_status(token, now=None):
    """The signed timestamp proves the form was served here and not filled in instantly.
    Returns 'ok', 'fast' (posted too soon), 'expired' or 'invalid' (missing or forged)."""
    try:
        ts_text, sig = (token or '').split('.', 1)
        ts = int(ts_text)
    except ValueError:
        return 'invalid'
    if not hmac.compare_digest(sig, _sign(ts)):
        return 'invalid'
    age = (now or time.time()) - ts
    if age < MIN_FILL_SECONDS:
        return 'fast'
    return 'expired' if age > MAX_FORM_AGE else 'ok'


class BusComplaints(http.Controller):

    # ------------------------------------------------------------------
    def _retention_days(self):
        value = request.env(su=True)['ir.config_parameter'].get_param('bus_tracking.complaint_retention_days')
        return int(value) if value not in (False, None, '') else 90

    def _form_values(self, post=None, errors=None, selected_route=None, text=None):
        routes = public_routes()
        post = post or {}
        values = portal_context(
            routes=[{'code': r.code, 'name': r.name} for r in routes],
            buses=[{'id': b.id, 'name': b.name, 'route': r.code}
                   for r in routes for b in r.vehicle_ids],
            kinds=[(key, 'kind_' + key) for key, _label in KINDS],
            token=new_form_token(),
            errors=errors or {},
            form={
                'route': post.get('route') or selected_route or '',
                'bus': post.get('bus') or '',
                'kind': post.get('kind') or 'other',
                'description': post.get('description') or _clean(text, MAX_DESCRIPTION),
                'email': post.get('email') or '',
                'phone': post.get('phone') or '',
            },
        )
        values['privacy_text'] = values['s']['privacy'].format(days=self._retention_days())
        values['max_description'] = MAX_DESCRIPTION
        values['privacy_url'] = values['privacy_link']
        return values

    def _thanks(self, folio=None, has_contact=True):
        query = ''
        if folio:
            query = '?f=%s&c=%d' % (folio, 1 if has_contact else 0)
        return request.redirect('/quejas/gracias' + query, code=303)

    # ------------------------------------------------------------------
    @http.route(['/quejas', '/transporte/quejas'], type='http', auth='public', methods=['GET'])
    def form(self, ruta=None, texto=None, **kwargs):
        # `texto` comes from the one-field box on the home page.
        return render_portal('bus_tracking.complaint_form', self._form_values(selected_route=ruta, text=texto))

    @http.route(['/quejas', '/transporte/quejas'], type='http', auth='public', methods=['POST'])
    def submit(self, **post):
        if (request.httprequest.content_length or 0) > MAX_BODY_BYTES:
            return request.make_response('', status=413)

        # Bots fill the hidden field or forge the token: pretend it worked and store nothing.
        status = token_status(post.get('t'))
        if post.get('website') or status == 'invalid':
            return self._thanks()
        if status == 'fast':
            # Too fast for a person typing, but a text brought from the home page can be sent
            # this quickly: ask to send again instead of dropping it while saying "thanks".
            strings = portal_context()['s']
            return render_portal('bus_tracking.complaint_form', self._form_values(
                post, {'form': strings['err_fast']}), status=400)
        if status == 'expired':
            return self._reject_expired(post)

        env = request.env(su=True)
        routes = public_routes()
        route = routes.filtered(lambda r: r.code == post.get('route'))[:1]
        bus = route.vehicle_ids.filtered(lambda b: str(b.id) == post.get('bus'))[:1] if route else env['bus.vehicle']
        values = portal_context()
        strings = values['s']

        kind = post.get('kind') if post.get('kind') in dict(KINDS) else 'other'
        description = _clean(post.get('description'), MAX_DESCRIPTION + 1)
        email = _clean(post.get('email'), 255)
        phone = _clean(post.get('phone'), 40)

        errors = {}
        if not MIN_DESCRIPTION <= len(description) <= MAX_DESCRIPTION:
            errors['description'] = strings['err_description']
        if email and not EMAIL_RE.match(email):
            errors['email'] = strings['err_email']
        if phone and not PHONE_RE.match(phone):
            errors['phone'] = strings['err_phone']
        if errors:
            return render_portal('bus_tracking.complaint_form', self._form_values(post, errors), status=400)

        if not submit_limiter.allow(request.httprequest.remote_addr):
            return render_portal('bus_tracking.complaint_form', self._form_values(
                post, {'form': strings['err_rate']}), status=429)

        complaint = env['bus.complaint'].create({
            'route_id': route.id,
            'vehicle_id': bus.id,
            'kind': kind,
            'description': description,
            'contact_email': email or False,
            'contact_phone': phone or False,
            'lang': values['lang'],
        })
        return self._thanks(complaint.name, bool(email or phone))

    def _reject_expired(self, post):
        """The page was open for a day: show it again, keeping what was typed."""
        strings = portal_context()['s']
        return render_portal('bus_tracking.complaint_form', self._form_values(
            post, {'form': strings['err_expired']}), status=400)

    @http.route(['/quejas/gracias', '/transporte/quejas/gracias'], type='http', auth='public', methods=['GET'])
    def thanks(self, f=None, c='1', **kwargs):
        return render_portal('bus_tracking.complaint_thanks', portal_context(
            folio=f if f and FOLIO_RE.match(f) else None, has_contact=(c != '0')))
