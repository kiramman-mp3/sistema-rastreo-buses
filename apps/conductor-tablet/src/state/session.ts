import { AuthError, createClient, defaultBaseUrl, NetworkError, type DriverClient, type TokenStore } from '../api/client';
import type {
  Driver,
  IncidentDraft,
  MeResponse,
  Route,
  RouteMap,
  Shift,
  StartResponse,
  StateResponse,
  Vehicle,
} from '../api/types';
import type { GpsController, GpsStore } from '../gps/types';
import { flushIncidents, IncidentQueue } from '../incidents/queue';

export type SessionSnapshot = {
  ready: boolean;
  token: string | null;
  driver: Driver | null;
  vehicles: Vehicle[];
  routes: Route[];
  shift: Shift | null;
  gps: { uniqueId: string; url: string } | null;
  shiftState: StateResponse | null;
  routeMap: RouteMap | null;
};

const empty: Omit<SessionSnapshot, 'ready'> = {
  token: null,
  driver: null,
  vehicles: [],
  routes: [],
  shift: null,
  gps: null,
  shiftState: null,
  routeMap: null,
};

export class Session {
  snapshot: SessionSnapshot = { ready: false, ...empty };
  private listeners = new Set<() => void>();

  constructor(
    private store: TokenStore,
    private client: DriverClient = createClient({ baseUrl: defaultBaseUrl(), store }),
    private gps?: GpsController,
    private gpsStore?: GpsStore,
    private incidents: IncidentQueue = new IncidentQueue({
      getItem: async () => null,
      setItem: async () => undefined,
    }),
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
      await this.restoreGps(me.shift);
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
    await this.restoreGps(me.shift);
  }

  async logout() {
    try {
      await this.client.logout();
    } catch {
      // The tablet still signs out locally even if the server is unreachable.
    }
    await this.stopGps();
    await this.store.clear();
    this.set({ ready: true, ...empty });
  }

  async startShift(vehicleId: number, routeId: number): Promise<StartResponse> {
    await this.gps?.prepare();
    const started = await this.client.startShift(vehicleId, routeId);
    const gps = { uniqueId: started.traccar_unique_id, url: started.gps_url };
    await this.gpsStore?.set(gps);
    try {
      await this.gps?.start(gps.uniqueId, gps.url);
    } catch {
      // Shift is already open; the diagnostic screen shows why GPS did not start.
    }
    this.set({
      shift: started.shift,
      gps,
      vehicles: this.snapshot.vehicles.map((bus) =>
        bus.id === vehicleId ? { ...bus, available: true, route_id: routeId } : { ...bus, available: bus.available && bus.id !== vehicleId },
      ),
    });
    return started;
  }

  async pullState(): Promise<StateResponse> {
    const state = await this.client.state();
    this.set({ shiftState: state, shift: state.shift });
    await this.flushIncidents();
    return state;
  }

  async loadRouteMap(): Promise<RouteMap> {
    const routeMap = await this.client.routeMap();
    this.set({ routeMap });
    return routeMap;
  }

  async reportIncident(draft: IncidentDraft) {
    try {
      await this.client.incident(draft);
    } catch (error) {
      if (error instanceof NetworkError) {
        await this.incidents.push(draft);
        return 'queued' as const;
      }
      throw error;
    }
    return 'sent' as const;
  }

  async flushIncidents() {
    await flushIncidents(this.incidents, async (draft) => {
      try {
        await this.client.incident(draft);
        return true;
      } catch (error) {
        return !(error instanceof NetworkError);
      }
    });
  }

  async endShift() {
    await this.flushIncidents();
    await this.client.endShift();
    await this.stopGps();
    this.set({ shift: null, gps: null, shiftState: null, routeMap: null });
  }

  private async restoreGps(shift: Shift | null) {
    if (!shift) {
      await this.stopGps();
      return;
    }
    const gps = await this.gpsStore?.get();
    if (!gps) return;
    this.set({ gps });
    try {
      await this.gps?.start(gps.uniqueId, gps.url);
    } catch {
      // Permissions can be missing after a reinstall; the shift screen still opens.
    }
  }

  private async stopGps() {
    try {
      await this.gps?.stop();
    } catch {
      // Local sign-out must succeed even if the OS task is already gone.
    }
    await this.gpsStore?.clear();
  }
}
