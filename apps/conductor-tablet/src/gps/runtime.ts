import { buildOsmAndUrl, locationToFix, type Fix } from './osmand';
import { flushQueue, LocationQueue } from './queue';

export type GpsCreds = { uniqueId: string; url: string };

export type LastSent = {
  at: number;
  lat: number;
  lon: number;
  error: string | null;
};

/** The last fix the GPS produced, sent or not: it tells whether the GPS works and how fast the bus goes. */
export type LastSample = {
  at: number;
  lat: number;
  lon: number;
  speedKmh: number | null;
};

export const SAMPLE_KEY = 'uta.gps.sample';
export const CREDS_KEY = 'uta.gps.creds';
export const LAST_KEY = 'uta.gps.last';
export const ERROR_KEY = 'uta.gps.error';
export const SEND_TIMEOUT_MS = 10_000;

/** Why the last send failed, for the GPS diagnostic screen. */
export type LastError = { at: number; error: string };

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

/**
 * Send one fix. Returns null when Traccar took it, or why it did not. A request that hangs is
 * given up after ten seconds: otherwise it would block the background task and the whole queue.
 */
export async function sendFix(
  http: typeof fetch,
  creds: GpsCreds,
  fix: Fix,
  timeoutMs = SEND_TIMEOUT_MS,
): Promise<string | null> {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<string>((resolve) => {
    timer = setTimeout(() => {
      controller?.abort();
      resolve('timeout');
    }, timeoutMs);
  });
  const request = http(buildOsmAndUrl(creds.url, creds.uniqueId, fix), { method: 'GET', signal: controller?.signal })
    .then((response) => (response.ok ? null : `http ${response.status}`))
    .catch(() => 'network');
  try {
    return await Promise.race([request, timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

/** Send what is queued, oldest first, stopping at the first failure. */
export async function flushFixes(
  queue: LocationQueue,
  creds: GpsCreds,
  http: typeof fetch = fetch,
): Promise<{ sent: number; error: string | null }> {
  let error: string | null = null;
  const sent = await flushQueue(queue, async (fix) => {
    error = await sendFix(http, creds, fix);
    return error === null;
  });
  return { sent, error };
}

export async function ingestLocations(
  locations: LocationSample[],
  options: {
    queue: LocationQueue;
    creds: GpsCreds;
    battery: () => Promise<number | null>;
    http?: typeof fetch;
    onSent?: (last: LastSent) => Promise<void>;
    onSample?: (sample: LastSample) => Promise<void>;
    onError?: (last: LastError) => Promise<void>;
  },
): Promise<{ queued: number; sent: number }> {
  if (!locations.length) return { queued: 0, sent: 0 };
  const newest = locations[locations.length - 1];
  if (options.onSample && newest) {
    const speed = newest.coords.speed;
    await options.onSample({
      at: newest.timestamp,
      lat: newest.coords.latitude,
      lon: newest.coords.longitude,
      speedKmh: speed !== null && speed >= 0 ? Math.round(speed * 3.6) : null,
    });
  }
  const batt = await options.battery();
  // Two runs of the background task must not read and write the queue at the same time.
  const { sent, error } = await options.queue.exclusive(async () => {
    await options.queue.pushMany(locations.map((location) => locationToFix(location, batt)));
    return flushFixes(options.queue, options.creds, options.http ?? fetch);
  });
  if (error && options.onError) await options.onError({ at: Date.now(), error });
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
