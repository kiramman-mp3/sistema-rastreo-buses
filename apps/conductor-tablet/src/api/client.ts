import type { MeResponse, StartResponse } from './types';

export class AuthError extends Error {
  constructor() {
    super('unauthorized');
    this.name = 'AuthError';
  }
}

export class NetworkError extends Error {
  constructor() {
    super('network');
    this.name = 'NetworkError';
  }
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string) {
    super(code);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export type TokenStore = {
  get(): Promise<string | null>;
  set(token: string): Promise<void>;
  clear(): Promise<void>;
};

export type ClientOptions = {
  baseUrl: string;
  store: TokenStore;
  fetch?: typeof fetch;
};

function errorCode(body: unknown): string {
  if (body && typeof body === 'object' && 'error' in body && typeof body.error === 'string') {
    return body.error;
  }
  return 'error';
}

export function createClient(options: ClientOptions) {
  const http = options.fetch ?? fetch;
  const root = options.baseUrl.replace(/\/$/, '');

  async function post<T>(path: string, body: object = {}, withToken = true): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (withToken) {
      const token = await options.store.get();
      if (token) headers.Authorization = 'Bearer ' + token;
    }
    let response: Response;
    try {
      response = await http(root + path, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
    } catch {
      throw new NetworkError();
    }
    if (response.status === 401) {
      await options.store.clear();
      throw new AuthError();
    }
    let data: unknown = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
    if (!response.ok) {
      throw new ApiError(response.status, errorCode(data));
    }
    return data as T;
  }

  return {
    login(login: string, password: string, device = 'tablet') {
      return post<{ token: string; driver: { id: number; name: string } }>(
        '/bus_tracking/driver/login',
        { login, password, device },
        false,
      );
    },
    logout() {
      return post<{ ok: boolean }>('/bus_tracking/driver/logout');
    },
    me() {
      return post<MeResponse>('/bus_tracking/driver/me');
    },
    startShift(vehicleId: number, routeId: number) {
      return post<StartResponse>('/bus_tracking/driver/shift/start', {
        vehicle_id: vehicleId,
        route_id: routeId,
      });
    },
    endShift() {
      return post<{ ok: boolean }>('/bus_tracking/driver/shift/end');
    },
  };
}

export type DriverClient = ReturnType<typeof createClient>;

export function defaultBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_ODOO_URL || 'http://10.0.2.2:8069').replace(/\/$/, '');
}
