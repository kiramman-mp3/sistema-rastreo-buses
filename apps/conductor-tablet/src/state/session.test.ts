import { AuthError, createClient, type TokenStore } from '../api/client';
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
});
