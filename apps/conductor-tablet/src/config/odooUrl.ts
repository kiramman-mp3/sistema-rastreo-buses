export const PRODUCTION_ODOO_URL = 'https://busesuta2340.eastus2.cloudapp.azure.com';

export function defaultBaseUrl(): string {
  return normalizeOdooUrl(process.env.EXPO_PUBLIC_ODOO_URL || PRODUCTION_ODOO_URL) || PRODUCTION_ODOO_URL;
}

export function normalizeOdooUrl(raw: string): string | null {
  const fromQr = odooFromPayload(raw.trim());
  if (!fromQr) return null;
  try {
    const url = new URL(fromQr);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    url.hash = '';
    url.search = '';
    url.pathname = url.pathname.replace(/\/web\/?$/, '').replace(/\/+$/, '');
    return url.toString().replace(/\/$/, '');
  } catch {
    return null;
  }
}

function odooFromPayload(raw: string): string | null {
  if (!raw) return null;
  if (raw.startsWith('{')) {
    try {
      const parsed = JSON.parse(raw) as { odoo?: string };
      return parsed.odoo || null;
    } catch {
      return null;
    }
  }
  if (raw.includes('odoo=')) {
    const query = raw.includes('?') ? raw.slice(raw.indexOf('?') + 1) : raw;
    return new URLSearchParams(query).get('odoo');
  }
  if (raw.startsWith('org.traccar.client://')) return null;
  return raw;
}
