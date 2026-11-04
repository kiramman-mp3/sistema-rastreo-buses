import { ApiError, AuthError, createClient, type TokenStore } from '../api/client';
import { ErrorQueue, memoryKv } from '../diagnostics/queue';
import type { ErrorReport } from '../diagnostics/report';
import { GpsPermissionError, type GpsController, type GpsStore } from '../gps/types';
import { IncidentQueue } from '../incidents/queue';
import { Session } from './session';

function memoryStore(initial: string | null = null): TokenStore {
  let value = initial;
  return {
    get: async () => value,
    set: async (token) => {
      value = token;
    },
    clear: async () => {
      value = null;
    },
  };
}

const me = {
  driver: { id: 7, name: 'Chofer Uno' },
  vehicles: [{ id: 1, name: 'Bus 1', plate: 'ABC', route_id: 2, available: true }],
  routes: [{ id: 2, code: 'L1', name: 'Centro', color: '#3388ff' }],
  shift: null as { id: number; vehicle_id: number; route_id: number; start: string } | null,
};

function json(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as Response);
}

function gpsMock(): GpsController & { started: string[] } {
  const started: string[] = [];
  return {
    started,
    prepare: async () => undefined,
    start: async (uniqueId, url) => {
      started.push(`${uniqueId}@${url}`);
    },
    stop: async () => {
      started.length = 0;
    },
  };
}

function gpsMemory(): GpsStore {
  let value: { uniqueId: string; url: string } | null = null;
  return {
    get: async () => value,
    set: async (next) => {
      value = next;
    },
    clear: async () => {
      value = null;
    },
  };
}

describe('session', () => {
  test('boot restores an active shift from /me', async () => {
    const tokens = memoryStore('saved');
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(200, { ...me, shift: { id: 9, vehicle_id: 1, route_id: 2, start: '2026-10-30T15:00:00Z' } }),
    });
    const session = new Session(tokens, client);
    await session.boot();
    expect(session.snapshot.token).toBe('saved');
    expect(session.snapshot.shift?.id).toBe(9);
    expect(session.snapshot.driver?.name).toBe('Chofer Uno');
  });

  test('boot with a 401 forgets the session', async () => {
    const tokens = memoryStore('dead');
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(401, { error: 'unauthorized' }),
    });
    const session = new Session(tokens, client);
    await session.boot();
    expect(session.snapshot.token).toBeNull();
    expect(session.snapshot.shift).toBeNull();
    expect(await tokens.get()).toBeNull();
  });

  test('boot without signal keeps the session and the GPS instead of logging out', async () => {
    const tokens = memoryStore('saved');
    const gps = gpsMock();
    const stored = gpsMemory();
    await stored.set({ uniqueId: 'dev-9', url: 'http://gps:5055' });
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => Promise.reject(new TypeError('Network request failed')),
    });
    const session = new Session(tokens, client, gps, stored);
    await session.boot();
    expect(session.snapshot.ready).toBe(true);
    expect(session.snapshot.token).toBe('saved');
    expect(session.snapshot.offline).toBe(true);
    expect(gps.started).toEqual(['dev-9@http://gps:5055']);
    expect(await tokens.get()).toBe('saved');
  });

  test('refreshMe after an offline start loads the shift', async () => {
    const tokens = memoryStore('saved');
    let online = false;
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () =>
        online
          ? json(200, { ...me, shift: { id: 9, vehicle_id: 1, route_id: 2, start: '2026-10-30T15:00:00Z' } })
          : Promise.reject(new TypeError('Network request failed')),
    });
    const session = new Session(tokens, client);
    await session.boot();
    expect(session.snapshot.offline).toBe(true);
    online = true;
    await session.refreshMe();
    expect(session.snapshot.offline).toBe(false);
    expect(session.snapshot.shift?.id).toBe(9);
  });

  test('login stores the token and loads /me', async () => {
    const tokens = memoryStore();
    const fetchMock = jest.fn(async (url: string) => {
      if (String(url).endsWith('/login')) return json(200, { token: 'new', driver: me.driver });
      return json(200, me);
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client);
    await session.login('chofer1', 'clave');
    expect(await tokens.get()).toBe('new');
    expect(session.snapshot.vehicles).toHaveLength(1);
  });

  test('login failure does not keep a token', async () => {
    const tokens = memoryStore();
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(401, { error: 'invalid_credentials' }),
    });
    const session = new Session(tokens, client);
    await expect(session.login('x', 'y')).rejects.toBeInstanceOf(AuthError);
    expect(await tokens.get()).toBeNull();
  });

  test('startShift asks for GPS before opening the shift and then starts the task', async () => {
    const tokens = memoryStore('tok');
    const order: string[] = [];
    const gps = gpsMock();
    gps.prepare = async () => {
      order.push('prepare');
    };
    gps.start = async (uniqueId, url) => {
      order.push(`start:${uniqueId}@${url}`);
    };
    const fetchMock = jest.fn(async (url: string) => {
      if (String(url).endsWith('/shift/start')) {
        order.push('api');
        return json(200, {
          shift: { id: 3, vehicle_id: 1, route_id: 2, start: '2026-10-30T16:00:00Z' },
          traccar_unique_id: 'dev-9',
          gps_url: 'http://gps:5055',
        });
      }
      return json(200, me);
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, gps, gpsMemory());
    await session.startShift(1, 2);
    expect(order).toEqual(['prepare', 'api', 'start:dev-9@http://gps:5055']);
    expect(session.snapshot.gps?.uniqueId).toBe('dev-9');
  });

  test('denied location permission never calls shift/start', async () => {
    const tokens = memoryStore('tok');
    const fetchMock = jest.fn(() => json(200, {}));
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const gps = gpsMock();
    gps.prepare = async () => {
      throw new GpsPermissionError();
    };
    const session = new Session(tokens, client, gps);
    await expect(session.startShift(1, 2)).rejects.toBeInstanceOf(GpsPermissionError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test('boot with an active shift restarts GPS from the stored id', async () => {
    const tokens = memoryStore('saved');
    const gps = gpsMock();
    const stored = gpsMemory();
    await stored.set({ uniqueId: 'dev-9', url: 'http://gps:5055' });
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(200, { ...me, shift: { id: 9, vehicle_id: 1, route_id: 2, start: '2026-10-30T15:00:00Z' } }),
    });
    const session = new Session(tokens, client, gps, stored);
    await session.boot();
    expect(gps.started).toEqual(['dev-9@http://gps:5055']);
    expect(session.snapshot.gps?.url).toBe('http://gps:5055');
  });

  test('logout stops GPS', async () => {
    const tokens = memoryStore('tok');
    const gps = gpsMock();
    gps.started.push('running');
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(200, { ok: true }),
    });
    const session = new Session(tokens, client, gps, gpsMemory());
    await session.logout();
    expect(gps.started).toEqual([]);
  });

  test('endShift stops GPS and clears the shift', async () => {
    const tokens = memoryStore('tok');
    const gps = gpsMock();
    gps.started.push('running');
    const fetchMock = jest.fn(async (url: string) => {
      if (String(url).endsWith('/shift/end')) return json(200, { ok: true });
      return json(200, { ok: true });
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, gps, gpsMemory());
    session.snapshot.shift = { id: 3, vehicle_id: 1, route_id: 2, start: '2026-10-30T16:00:00Z' };
    await session.endShift();
    expect(session.snapshot.shift).toBeNull();
    expect(gps.started).toEqual([]);
  });

  test('loginWithBadge exchanges badge token for a session and populates driver state', async () => {
    const tokens = memoryStore(null);
    const fetchMock = jest.fn(async (url: string) => {
      const u = String(url);
      if (u.endsWith('/login_badge')) {
        return json(200, { token: 'session-tok-123', driver: { id: 7, name: 'Chofer Uno' } });
      }
      if (u.endsWith('/me')) {
        return json(200, me);
      }
      return json(404, { error: 'not_found' });
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client);
    await session.loginWithBadge('raw-badge-token-abc');

    expect(session.snapshot.token).toBe('session-tok-123');
    expect(session.snapshot.driver?.name).toBe('Chofer Uno');
    expect(session.snapshot.vehicles).toHaveLength(1);
    expect(session.snapshot.routes).toHaveLength(1);
  });

  test('loginWithBadge never keeps the badge as a session when the server rejects it', async () => {
    const tokens = memoryStore(null);
    const fetchMock = jest.fn(async () => json(404, { error: 'not_found' }));
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client);
    await expect(session.loginWithBadge('raw-badge-token-abc')).rejects.toBeInstanceOf(ApiError);
    expect(await tokens.get()).toBeNull();
    expect(session.snapshot.token).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  const activeShift = { id: 3, vehicle_id: 1, route_id: 2, start: '2026-10-30T16:00:00Z' };

  function routed(routes: Record<string, () => Promise<Response>>) {
    return jest.fn(async (url: string) => {
      const path = Object.keys(routes).find((key) => String(url).endsWith(key));
      return path ? routes[path]() : json(200, { ok: true });
    });
  }

  test('a shift closed by the office stops the gps', async () => {
    const tokens = memoryStore('tok');
    const gps = gpsMock();
    gps.started.push('running');
    const fetchMock = routed({ '/state': () => json(409, { error: 'no_shift' }) });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, gps, gpsMemory());
    session.snapshot.shift = activeShift;
    await expect(session.pullState()).rejects.toBeInstanceOf(ApiError);
    expect(gps.started).toEqual([]);
    expect(session.snapshot.shift).toBeNull();
  });

  test('ending a shift the server already closed still ends it on the tablet', async () => {
    const tokens = memoryStore('tok');
    const gps = gpsMock();
    gps.started.push('running');
    const fetchMock = routed({ '/shift/end': () => json(409, { error: 'no_shift' }) });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, gps, gpsMemory());
    session.snapshot.shift = activeShift;
    await expect(session.endShift()).resolves.toBe('ended');
    expect(gps.started).toEqual([]);
    expect(session.snapshot.shift).toBeNull();
  });

  test('ending without signal turns the gps off and closes the shift once back online', async () => {
    const tokens = memoryStore('tok');
    const pending = memoryStore(null);
    const gps = gpsMock();
    gps.started.push('running');
    let online = false;
    const ends: string[] = [];
    const fetchMock = jest.fn(async (url: string) => {
      if (!online) throw new TypeError('Network request failed');
      if (String(url).endsWith('/shift/end')) ends.push('end');
      if (String(url).endsWith('/me')) return json(200, { ...me, shift: activeShift });
      return json(200, { ok: true });
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, gps, gpsMemory(), undefined, undefined, pending);
    session.snapshot.shift = activeShift;
    await expect(session.endShift()).resolves.toBe('queued');
    expect(gps.started).toEqual([]);
    expect(await pending.get()).toBe('3');

    online = true;
    await session.refreshMe();
    expect(ends).toEqual(['end']);
    expect(await pending.get()).toBeNull();
    // The server answered /me before seeing the end: the tablet does not bring the shift back.
    expect(gps.started).toEqual([]);
  });

  test('incidents wait on server errors, are dropped when refused and keep their time', async () => {
    const tokens = memoryStore('tok');
    const kv = new Map<string, string>();
    const queue = new IncidentQueue({
      getItem: async (key) => kv.get(key) ?? null,
      setItem: async (key, value) => {
        kv.set(key, value);
      },
    });
    let status = 500;
    const bodies: { reported_at?: string }[] = [];
    const fetchMock = jest.fn(async (url: string, init?: RequestInit) => {
      if (String(url).endsWith('/incident')) {
        bodies.push(JSON.parse(String(init?.body)));
        return json(status, status === 200 ? { id: 1 } : { error: 'x' });
      }
      return json(200, { ok: true });
    });
    const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: fetchMock as unknown as typeof fetch });
    const session = new Session(tokens, client, undefined, undefined, queue);
    await expect(session.reportIncident({ kind: 'sos', note: '', lat: null, lon: null })).resolves.toBe('queued');
    expect(await queue.size()).toBe(1);
    const pressed = bodies[0].reported_at;
    expect(pressed).toMatch(/Z$/);

    await session.flushIncidents();
    expect(await queue.size()).toBe(1);
    status = 200;
    await session.flushIncidents();
    expect(await queue.size()).toBe(0);
    expect(bodies[bodies.length - 1].reported_at).toBe(pressed);

    status = 400;
    await expect(session.reportIncident({ kind: 'traffic', note: '', lat: null, lon: null })).rejects.toBeInstanceOf(ApiError);
    expect(await queue.size()).toBe(0);
  });

  describe('app failures waiting for the office', () => {
    const waiting: ErrorReport = { message: 'Error: boom', app: '1.0.0', at: '2026-11-02T20:00:00.000Z' };

    async function arrange(answer: (url: string) => Promise<Response>) {
      const tokens = memoryStore('saved');
      const calls: string[] = [];
      const client = createClient({
        baseUrl: 'http://odoo:8069',
        store: tokens,
        fetch: (url) => {
          calls.push(String(url));
          return answer(String(url));
        },
      });
      const errors = new ErrorQueue(memoryKv());
      await errors.push(waiting);
      const session = new Session(tokens, client, undefined, undefined, undefined, undefined, undefined, errors);
      return { session, errors, calls };
    }

    const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
    const answers = (clientError: () => Promise<Response>) => (url: string) =>
      url.endsWith('/driver/client_error') ? clientError() : json(200, me);

    test('are sent once the driver is signed in and then forgotten', async () => {
      const { session, errors, calls } = await arrange(answers(() => json(200, { ok: true })));
      await session.boot();
      await settle();
      expect(calls.filter((u) => u.endsWith('/client_error'))).toHaveLength(1);
      expect(await errors.size()).toBe(0);
      expect((await errors.last())?.message).toBe('Error: boom');
    });

    test('stay for later without signal or with a failing server', async () => {
      for (const reply of [() => Promise.reject(new Error('offline')), () => json(500, { error: 'x' })]) {
        const { session, errors } = await arrange(answers(reply));
        await session.boot();
        await settle();
        expect(await errors.size()).toBe(1);
      }
    });

    test('stay when the server is busy (429) and go when it refuses them for good (400)', async () => {
      const busy = await arrange(answers(() => json(429, { error: 'too_many_requests' })));
      await busy.session.boot();
      await settle();
      expect(await busy.errors.size()).toBe(1);
      const refused = await arrange(answers(() => json(400, { error: 'bad_request' })));
      await refused.session.boot();
      await settle();
      expect(await refused.errors.size()).toBe(0);
    });

    test('a session without an error queue works as before', async () => {
      const tokens = memoryStore('saved');
      const client = createClient({ baseUrl: 'http://odoo:8069', store: tokens, fetch: () => json(200, me) });
      const session = new Session(tokens, client);
      await session.boot();
      await expect(session.flushErrors()).resolves.toBeUndefined();
    });
  });
});
