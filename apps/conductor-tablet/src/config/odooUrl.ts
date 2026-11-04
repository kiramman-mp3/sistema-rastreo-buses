export const PRODUCTION_ODOO_URL = 'https://busesuta2340.eastus2.cloudapp.azure.com';

export function defaultBaseUrl(): string {
  return normalizeOdooUrl(process.env.EXPO_PUBLIC_ODOO_URL || PRODUCTION_ODOO_URL) || PRODUCTION_ODOO_URL;
}

/** Plain http is only for a server on this network (development, a lab); anything else needs https. */
export function isLocalHost(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (host === 'localhost' || host === '::1' || host.endsWith('.local')) return true;
  const parts = host.split('.').map(Number);
  if (parts.length !== 4 || parts.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) return false;
  const [a, b] = parts;
  return a === 127 || a === 10 || (a === 192 && b === 168) || (a === 172 && b >= 16 && b <= 31);
}

export function normalizeOdooUrl(raw: string): string | null {
  const fromQr = odooFromPayload(raw.trim());
  if (!fromQr) return null;
  try {
    const url = new URL(fromQr);
    if (url.protocol !== 'https:' && !(url.protocol === 'http:' && isLocalHost(url.hostname))) return null;
    url.hash = '';
    url.search = '';
    url.pathname = url.pathname.replace(/\/web\/?$/, '').replace(/\/+$/, '');
    return url.toString().replace(/\/$/, '');
  } catch {
    return null;
  }
}

export type DriverBadgePayload = {
  odooUrl: string | null;
  token: string;
  driverName: string | null;
};

export function parseDriverBadge(raw: string): DriverBadgePayload | null {
  if (!raw) return null;
  const trimmed = raw.trim();

  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed) as { odoo?: string; token?: string; driver?: string };
      if (parsed.token && typeof parsed.token === 'string') {
        const odooUrl = parsed.odoo ? normalizeOdooUrl(parsed.odoo) : null;
        return {
          odooUrl,
          token: parsed.token.trim(),
          driverName: parsed.driver || null,
        };
      }
    } catch {
      // not JSON
    }
  }

  if (trimmed.includes('token=')) {
    try {
      const query = trimmed.includes('?') ? trimmed.slice(trimmed.indexOf('?') + 1) : trimmed;
      const params = new URLSearchParams(query);
      const token = params.get('token');
      if (token) {
        const rawOdoo = params.get('odoo');
        const odooUrl = rawOdoo ? normalizeOdooUrl(rawOdoo) : null;
        const driverName = params.get('driver') || null;
        return {
          odooUrl,
          token: token.trim(),
          driverName,
        };
      }
    } catch {
      return null;
    }
  }

  return null;
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
