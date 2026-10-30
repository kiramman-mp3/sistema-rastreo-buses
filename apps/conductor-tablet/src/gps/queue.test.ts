import { ingestLocations } from './runtime';
import { flushQueue, LocationQueue, MAX_QUEUE_AGE_MS, MAX_QUEUE_ITEMS, memoryKv } from './queue';
import type { Fix } from './osmand';

function fix(n: number, at = 1_000): Fix {
  return {
    lat: n,
    lon: n,
    timestampMs: at,
    speedMs: 1,
    bearing: 0,
    altitude: 0,
    accuracy: 5,
    batt: 50,
  };
}

describe('location queue', () => {
  test('retries in insertion order and stops on the first failure', async () => {
    const queue = new LocationQueue(memoryKv(), () => 2_000);
    await queue.push(fix(1));
    await queue.push(fix(2));
    await queue.push(fix(3));
    const seen: number[] = [];
    const sent = await flushQueue(queue, async (item) => {
      seen.push(item.lat);
      return item.lat !== 2;
    });
    expect(sent).toBe(1);
    expect(seen).toEqual([1, 2]);
    const left = await queue.load();
    expect(left.map((item) => item.lat)).toEqual([2, 3]);
  });

  test('drops points older than the age cap', async () => {
    const now = 10_000 + MAX_QUEUE_AGE_MS;
    const queue = new LocationQueue(memoryKv(), () => now);
    await queue.push(fix(1, 9_999));
    await queue.push(fix(2, now));
    expect((await queue.load()).map((item) => item.lat)).toEqual([2]);
  });

  test('keeps the newest points when the size cap is exceeded', async () => {
    const queue = new LocationQueue(memoryKv(), () => 1, 3, MAX_QUEUE_AGE_MS);
    for (let n = 1; n <= 5; n += 1) await queue.push(fix(n, 1));
    expect((await queue.load()).map((item) => item.lat)).toEqual([3, 4, 5]);
    expect(MAX_QUEUE_ITEMS).toBeGreaterThan(3);
  });

  test('simulated location is queued then drained when the send succeeds', async () => {
    const kv = memoryKv();
    const queue = new LocationQueue(kv, () => 1_700_000_000_000);
    const urls: string[] = [];
    const result = await ingestLocations(
      [
        {
          timestamp: 1_700_000_000_000,
          coords: {
            latitude: -1.24,
            longitude: -78.62,
            altitude: 2600,
            accuracy: 8,
            heading: 90,
            speed: 10,
          },
        },
      ],
      {
        queue,
        creds: { uniqueId: 'bus-1', url: 'http://gps.example:5055' },
        battery: async () => 80,
        http: async (url) => {
          urls.push(String(url));
          return { ok: true } as Response;
        },
      },
    );
    expect(result.queued).toBe(1);
    expect(result.sent).toBe(1);
    expect(await queue.size()).toBe(0);
    expect(urls[0]).toContain('id=bus-1');
    expect(urls[0]).toContain('lat=-1.240000');
  });

  test('keeps the point when the network fails', async () => {
    const queue = new LocationQueue(memoryKv(), () => 1_700_000_000_000);
    await ingestLocations(
      [
        {
          timestamp: 1_700_000_000_000,
          coords: {
            latitude: 0,
            longitude: 0,
            altitude: null,
            accuracy: null,
            heading: null,
            speed: null,
          },
        },
      ],
      {
        queue,
        creds: { uniqueId: 'id', url: 'http://gps.example' },
        battery: async () => null,
        http: async () => {
          throw new Error('offline');
        },
      },
    );
    expect(await queue.size()).toBe(1);
  });
});
