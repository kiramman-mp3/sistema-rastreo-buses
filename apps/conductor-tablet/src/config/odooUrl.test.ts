import { normalizeOdooUrl, PRODUCTION_ODOO_URL } from './odooUrl';

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
});
