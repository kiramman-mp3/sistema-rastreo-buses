import { normalizeOdooUrl, parseDriverBadge, PRODUCTION_ODOO_URL } from './odooUrl';

describe('Odoo URL from QR or typing', () => {
  test('strips /web and a trailing slash', () => {
    expect(normalizeOdooUrl('https://busesuta2340.eastus2.cloudapp.azure.com/web')).toBe(PRODUCTION_ODOO_URL);
    expect(normalizeOdooUrl(PRODUCTION_ODOO_URL + '/')).toBe(PRODUCTION_ODOO_URL);
  });

  test('reads the tablet setup QR', () => {
    const payload = 'uta-buses://setup?odoo=' + encodeURIComponent(PRODUCTION_ODOO_URL + '/web');
    expect(normalizeOdooUrl(payload)).toBe(PRODUCTION_ODOO_URL);
  });

  test('reads a JSON payload', () => {
    expect(normalizeOdooUrl(JSON.stringify({ odoo: PRODUCTION_ODOO_URL }))).toBe(PRODUCTION_ODOO_URL);
  });

  test('ignores the old Traccar Client QR (no Odoo URL in it)', () => {
    expect(normalizeOdooUrl('org.traccar.client://config?url=https://gps.example&id=bus-1')).toBeNull();
  });

  describe('parseDriverBadge', () => {
    test('parses uta-buses://login deep link with token, odoo, and driver', () => {
      const qr = 'uta-buses://login?odoo=https%3A%2F%2Fbusesuta2340.eastus2.cloudapp.azure.com&token=secret-token-123&driver=Carlos+Mendoza';
      const parsed = parseDriverBadge(qr);
      expect(parsed).toEqual({
        odooUrl: PRODUCTION_ODOO_URL,
        token: 'secret-token-123',
        driverName: 'Carlos Mendoza',
      });
    });

    test('parses JSON format driver badge', () => {
      const qr = JSON.stringify({
        odoo: PRODUCTION_ODOO_URL,
        token: 'badge-token-456',
        driver: 'Juan Perez',
      });
      const parsed = parseDriverBadge(qr);
      expect(parsed).toEqual({
        odooUrl: PRODUCTION_ODOO_URL,
        token: 'badge-token-456',
        driverName: 'Juan Perez',
      });
    });

    test('returns null for server setup QR (no token)', () => {
      expect(parseDriverBadge('uta-buses://setup?odoo=https://busesuta2340.eastus2.cloudapp.azure.com')).toBeNull();
    });

    test('returns null for arbitrary strings or empty input', () => {
      expect(parseDriverBadge('')).toBeNull();
      expect(parseDriverBadge('just-a-random-string')).toBeNull();
    });
  });
});
