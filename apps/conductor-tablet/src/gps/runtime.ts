import { buildOsmAndUrl, locationToFix, type Fix } from './osmand';
import { flushQueue, LocationQueue } from './queue';

export type GpsCreds = { uniqueId: string; url: string };

export type LastSent = {
  at: number;
  lat: number;
  lon: number;
  error: string | null;
};

export const CREDS_KEY = 'uta.gps.creds';
export const LAST_KEY = 'uta.gps.last';

export type LocationSample = {
  timestamp: number;
  coords: {
    latitude: number;
    longitude: number;
    altitude: number | null;
    accuracy: number | null;
    heading: number | null;
    speed: number | null;
  };
};

export async function sendFix(
  http: typeof fetch,
  creds: GpsCreds,
  fix: Fix,
): Promise<boolean> {
  try {
    const response = await http(buildOsmAndUrl(creds.url, creds.uniqueId, fix), { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}

export async function ingestLocations(
  locations: LocationSample[],
  options: {
    queue: LocationQueue;
    creds: GpsCreds;
    battery: () => Promise<number | null>;
    http?: typeof fetch;
    onSent?: (last: LastSent) => Promise<void>;
  },
): Promise<{ queued: number; sent: number }> {
  if (!locations.length) return { queued: 0, sent: 0 };
  const batt = await options.battery();
  for (const location of locations) {
    await options.queue.push(locationToFix(location, batt));
  }
  const http = options.http ?? fetch;
  const sent = await flushQueue(options.queue, (fix) => sendFix(http, options.creds, fix));
  const last = locations[locations.length - 1];
  if (sent > 0 && options.onSent && last) {
    await options.onSent({
      at: Date.now(),
      lat: last.coords.latitude,
      lon: last.coords.longitude,
      error: null,
    });
  }
  return { queued: locations.length, sent };
}
