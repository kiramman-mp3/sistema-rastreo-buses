import type { IncidentDraft, MeResponse, RouteMap, StartResponse, StateResponse } from './types';

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
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 10000) : null;
    try {
      response = await http(root + path, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller?.signal,
      });
    } catch {
      throw new NetworkError();
    } finally {
      if (timer) clearTimeout(timer);
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
    loginBadge(badgeToken: string, device = 'tablet') {
      return post<{ token: string; driver: { id: number; name: string } }>(
        '/bus_tracking/driver/login_badge',
        { badge_token: badgeToken, device },
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
    state() {
      return post<StateResponse>('/bus_tracking/driver/state');
    },
    routeMap() {
      return post<RouteMap>('/bus_tracking/driver/route');
    },
    incident(draft: IncidentDraft) {
      const body: Record<string, unknown> = { kind: draft.kind, note: draft.note };
      if (draft.lat !== null && draft.lon !== null) {
        body.lat = draft.lat;
        body.lon = draft.lon;
      }
      if (draft.reported_at) body.reported_at = draft.reported_at;
      return post<{ id: number }>('/bus_tracking/driver/incident', body);
    },
  };
}

export type DriverClient = ReturnType<typeof createClient>;

export { defaultBaseUrl } from '../config/odooUrl';
