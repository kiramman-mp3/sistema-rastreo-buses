import { AuthError, ApiError, NetworkError, createClient, type TokenStore } from './client';

function store(initial: string | null = 'tok'): TokenStore {
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

function json(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as Response);
}

describe('driver API client', () => {
  test('sends the bearer token', async () => {
    const tokens = store('abc');
    const fetchMock = jest.fn().mockResolvedValue(json(200, { driver: { id: 1, name: 'A' }, vehicles: [], routes: [], shift: null }));
    const client = createClient({ baseUrl: 'http://odoo:8069/', store: tokens, fetch: fetchMock });
    await client.me();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://odoo:8069/bus_tracking/driver/me',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer abc' }),
      }),
    );
  });

  test('clears the token on 401', async () => {
    const tokens = store('abc');
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: tokens,
      fetch: () => json(401, { error: 'unauthorized' }),
    });
    await expect(client.me()).rejects.toBeInstanceOf(AuthError);
    expect(await tokens.get()).toBeNull();
  });

  test('maps a dropped connection to NetworkError', async () => {
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: store(),
      fetch: () => Promise.reject(new TypeError('Failed to fetch')),
    });
    await expect(client.me()).rejects.toBeInstanceOf(NetworkError);
  });

  test('keeps the API error code from a 409', async () => {
    const client = createClient({
      baseUrl: 'http://odoo:8069',
      store: store(),
      fetch: () => json(409, { error: 'no_gps' }),
    });
    try {
      await client.startShift(1, 2);
      throw new Error('expected failure');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).code).toBe('no_gps');
    }
  });

  test('asks for the state in the language of the app', async () => {
    const fetchMock = jest.fn().mockResolvedValue(json(200, { stops: [], alerts: [] }));
    const client = createClient({ baseUrl: 'http://odoo:8069', store: store(), fetch: fetchMock });
    await client.state('es');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ lang: 'es' });
    await client.state();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({});
  });

  test('sends an app failure to the client_error endpoint', async () => {
    const fetchMock = jest.fn().mockResolvedValue(json(200, { ok: true }));
    const client = createClient({ baseUrl: 'http://odoo:8069', store: store(), fetch: fetchMock });
    const report = { message: 'Error: boom', app: '1.0.0', at: '2026-11-02T20:00:00.000Z' };
    await client.clientError(report);
    expect(fetchMock.mock.calls[0][0]).toBe('http://odoo:8069/bus_tracking/driver/client_error');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(report);
  });
});
