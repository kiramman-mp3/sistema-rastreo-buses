import { LocationQueue, memoryKv } from './queue';
import { ingestLocations, sendFix, type LastError, type LocationSample } from './runtime';

const creds = { uniqueId: 'dev-1', url: 'https://gps.example.com' };

function sample(timestamp: number, lat = -1.24): LocationSample {
  return {
    timestamp,
    coords: { latitude: lat, longitude: -78.62, altitude: null, accuracy: 5, heading: null, speed: 3 },
  };
}

function ok() {
  return Promise.resolve({ ok: true, status: 200 } as Response);
}

describe('gps runtime', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  test('gives up on a request that hangs', async () => {
    jest.useFakeTimers();
    const hanging = jest.fn(() => new Promise<Response>(() => undefined));
    const result = sendFix(hanging as unknown as typeof fetch, creds, {
      lat: 1,
      lon: 1,
      timestampMs: Date.now(),
    } as never, 50);
    jest.advanceTimersByTime(60);
    await expect(result).resolves.toBe('timeout');
  });

  test('says why traccar refused a point and keeps it queued', async () => {
    const queue = new LocationQueue(memoryKv());
    const errors: LastError[] = [];
    const refused = jest.fn(() => Promise.resolve({ ok: false, status: 400 } as Response));
    const result = await ingestLocations([sample(Date.now())], {
      queue,
      creds,
      battery: async () => 80,
      http: refused as unknown as typeof fetch,
      onError: async (last) => {
        errors.push(last);
      },
    });
    expect(result.sent).toBe(0);
    expect(errors.map((e) => e.error)).toEqual(['http 400']);
    expect(await queue.size()).toBe(1);
  });

  test('two runs at once neither lose nor repeat points', async () => {
    const queue = new LocationQueue(memoryKv());
    const sent: string[] = [];
    const http = jest.fn(async (url: string) => {
      await new Promise((resolve) => setTimeout(resolve, 5));
      sent.push(new URL(url).searchParams.get('timestamp') ?? '');
      return { ok: true, status: 200 } as Response;
    });
    const now = Date.now();
    await Promise.all([
      ingestLocations([sample(now - 2000), sample(now - 1000)], {
        queue, creds, battery: async () => null, http: http as unknown as typeof fetch,
      }),
      ingestLocations([sample(now)], { queue, creds, battery: async () => null, http: http as unknown as typeof fetch }),
    ]);
    expect(sent).toHaveLength(3);
    expect(new Set(sent).size).toBe(3);
    expect(await queue.size()).toBe(0);
  });

  test('a good send reports no error', async () => {
    const queue = new LocationQueue(memoryKv());
    const onError = jest.fn(async () => undefined);
    const result = await ingestLocations([sample(Date.now())], {
      queue, creds, battery: async () => null, http: ok as unknown as typeof fetch, onError,
    });
    expect(result.sent).toBe(1);
    expect(onError).not.toHaveBeenCalled();
  });
});
