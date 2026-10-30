import { AuthError, createClient, defaultBaseUrl, type DriverClient, type TokenStore } from '../api/client';
import type { Driver, MeResponse, Route, Shift, StartResponse, Vehicle } from '../api/types';

export type SessionSnapshot = {
  ready: boolean;
  token: string | null;
  driver: Driver | null;
  vehicles: Vehicle[];
  routes: Route[];
  shift: Shift | null;
  gps: { uniqueId: string; url: string } | null;
};

const empty: Omit<SessionSnapshot, 'ready'> = {
  token: null,
  driver: null,
  vehicles: [],
  routes: [],
  shift: null,
  gps: null,
};

export class Session {
  snapshot: SessionSnapshot = { ready: false, ...empty };
  private listeners = new Set<() => void>();

  constructor(
    private store: TokenStore,
    private client: DriverClient = createClient({ baseUrl: defaultBaseUrl(), store }),
  ) {}

  subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit() {
    this.listeners.forEach((listener) => listener());
  }

  private set(partial: Partial<SessionSnapshot>) {
    this.snapshot = { ...this.snapshot, ...partial };
    this.emit();
  }

  private applyMe(me: MeResponse, token: string) {
    this.set({
      ready: true,
      token,
      driver: me.driver,
      vehicles: me.vehicles,
      routes: me.routes,
      shift: me.shift,
    });
  }

  async boot() {
    const token = await this.store.get();
    if (!token) {
      this.set({ ready: true, ...empty });
      return;
    }
    try {
      const me = await this.client.me();
      this.applyMe(me, token);
    } catch (error) {
      if (error instanceof AuthError) {
        this.set({ ready: true, ...empty });
        return;
      }
      this.set({ ready: true, token });
      throw error;
    }
  }

  async login(login: string, password: string) {
    const { token, driver } = await this.client.login(login, password);
    await this.store.set(token);
    const me = await this.client.me();
    this.applyMe({ ...me, driver }, token);
  }

  async logout() {
    try {
      await this.client.logout();
    } catch {
      // The tablet still signs out locally even if the server is unreachable.
    }
    await this.store.clear();
    this.set({ ready: true, ...empty });
  }

  async startShift(vehicleId: number, routeId: number): Promise<StartResponse> {
    const started = await this.client.startShift(vehicleId, routeId);
    this.set({
      shift: started.shift,
      gps: { uniqueId: started.traccar_unique_id, url: started.gps_url },
      vehicles: this.snapshot.vehicles.map((bus) =>
        bus.id === vehicleId ? { ...bus, available: true, route_id: routeId } : { ...bus, available: bus.available && bus.id !== vehicleId },
      ),
    });
    return started;
  }
}
