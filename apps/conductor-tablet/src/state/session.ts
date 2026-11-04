import { ApiError, AuthError, createClient, defaultBaseUrl, NetworkError, type DriverClient, type TokenStore } from '../api/client';
import { normalizeOdooUrl } from '../config/odooUrl';
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
import { flushErrors, type ErrorQueue } from '../diagnostics/queue';
import { getLang } from '../i18n';
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
  odooUrl: string;
  /** True when the tablet has a saved session but could not reach the server yet. */
  offline: boolean;
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
  odooUrl: defaultBaseUrl(),
  offline: false,
};

function isServerError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 500;
}

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
    private urlStore?: TokenStore,
    /** Remembers a shift the driver ended without signal, to close it on the server later. */
    private endStore?: TokenStore,
    /** Failures of the app itself, waiting to be told to the office. */
    private errors?: ErrorQueue,
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
      offline: false,
    });
  }

  async setOdooUrl(raw: string) {
    const url = normalizeOdooUrl(raw);
    if (!url) throw new Error('bad_odoo_url');
    await this.urlStore?.set(url);
    this.client = createClient({ baseUrl: url, store: this.store });
    this.set({ odooUrl: url });
  }

  async boot() {
    try {
      const savedUrl = await this.urlStore?.get();
      if (savedUrl) {
        this.client = createClient({ baseUrl: savedUrl, store: this.store });
        this.set({ odooUrl: savedUrl });
      }
      const token = await this.store.get();
      if (!token) {
        this.set({ ready: true, ...empty, odooUrl: this.snapshot.odooUrl });
        return;
      }
      try {
        const pendingEnd = await this.flushPendingEnd();
        const me = await this.client.me();
        // The driver already ended it: never bring its GPS back.
        if (pendingEnd) me.shift = null;
        this.applyMe(me, token);
        this.sendErrors();
        if (me.shift) {
          try {
            await this.pullState();
            await this.loadRouteMap();
          } catch {
            // The shift screen keeps retrying.
          }
        }
        await this.restoreGps(me.shift);
      } catch (error) {
        if (error instanceof AuthError) {
          this.set({ ready: true, ...empty, odooUrl: this.snapshot.odooUrl });
          return;
        }
        // No signal while opening the app: keep the session and the GPS running, retry later.
        // Sending the driver back to the login screen here would force them to type the password
        // again in a moving bus.
        this.set({ ready: true, token, offline: true });
        const gps = await this.gpsStore?.get();
        if (gps) {
          this.set({ gps });
          try {
            await this.gps?.start(gps.uniqueId, gps.url);
          } catch {
            // The diagnostic screen shows why.
          }
        }
      }
    } catch {
      // Unexpected storage error: never leave the app stuck on the loading screen.
      this.set({ ready: true });
    }
  }

  /** Ask the server again after an offline start. Throws NetworkError while there is no signal. */
  async refreshMe() {
    const token = await this.store.get();
    if (!token) return;
    try {
      const pendingEnd = await this.flushPendingEnd();
      const me = await this.client.me();
      if (pendingEnd) me.shift = null;
      this.applyMe(me, token);
      await this.restoreGps(me.shift);
    } catch (error) {
      if (error instanceof AuthError) {
        await this.stopGps();
        this.set({ ready: true, ...empty, odooUrl: this.snapshot.odooUrl });
        return;
      }
      throw error;
    }
  }

  async login(login: string, password: string) {
    const { token, driver } = await this.client.login(login, password);
    await this.store.set(token);
    const me = await this.client.me();
    this.applyMe({ ...me, driver }, token);
    this.sendErrors();
    await this.restoreGps(me.shift);
  }

  async loginWithBadge(badgeToken: string, odooUrl?: string | null) {
    if (odooUrl) {
      await this.setOdooUrl(odooUrl);
    }
    // The badge only buys a session; it is never kept as one. An old server without
    // login_badge answers 404 and the error reaches the scan screen.
    const { token, driver } = await this.client.loginBadge(badgeToken);
    await this.store.set(token);
    const me = await this.client.me();
    this.applyMe({ ...me, driver }, token);
    this.sendErrors();
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
    this.set({ ready: true, ...empty, odooUrl: this.snapshot.odooUrl });
  }

  async startShift(vehicleId: number, routeId: number): Promise<StartResponse> {
    // A shift ended without signal must be closed first, or the server answers conflict.
    await this.flushPendingEnd();
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
    try {
      await this.pullState();
      await this.loadRouteMap();
    } catch {
      // Non-blocking fallback
    }
    return started;
  }

  async pullState(): Promise<StateResponse> {
    let state: StateResponse;
    try {
      state = await this.client.state(getLang());
    } catch (error) {
      // The office or the stale-shift cron closed it, or the tablet was signed out:
      // the tablet must stop sending positions right away.
      if (error instanceof ApiError && error.code === 'no_shift') await this.dropShift();
      throw error;
    }
    this.set({ shiftState: state, shift: state.shift });
    await this.flushIncidents();
    this.sendErrors();
    return state;
  }

  async loadRouteMap(): Promise<RouteMap> {
    const routeMap = await this.client.routeMap();
    this.set({ routeMap });
    return routeMap;
  }

  async reportIncident(input: IncidentDraft) {
    const draft = { ...input, reported_at: input.reported_at ?? new Date().toISOString() };
    try {
      await this.client.incident(draft);
    } catch (error) {
      if (error instanceof NetworkError || isServerError(error)) {
        await this.incidents.push(draft);
        return 'queued' as const;
      }
      throw error;
    }
    return 'sent' as const;
  }

  /** Tell the office about the app failures that are waiting. Fire and forget: it must never get in the way. */
  private sendErrors() {
    this.flushErrors().catch(() => undefined);
  }

  async flushErrors() {
    if (!this.errors) return;
    await flushErrors(this.errors, async (report) => {
      try {
        await this.client.clientError(report);
        return true;
      } catch (error) {
        // Kept for later without signal, without a session or when the server is busy or failing; a report the
        // server refuses for good (bad data) is dropped.
        if (error instanceof NetworkError || error instanceof AuthError || isServerError(error)) return false;
        return !(error instanceof ApiError && error.status === 429);
      }
    });
  }

  async flushIncidents() {
    await flushIncidents(this.incidents, async (draft) => {
      try {
        await this.client.incident(draft);
        return true;
      } catch (error) {
        // Kept for later on no signal or a server error; only a request the server refuses
        // for good (bad data, no shift) is dropped.
        return !(error instanceof NetworkError || isServerError(error));
      }
    });
  }

  /**
   * End the shift. The GPS always stops here, with or without signal: without it the end is
   * remembered and sent later (the stale-shift cron closes it on the server otherwise).
   */
  async endShift(): Promise<'ended' | 'queued'> {
    try {
      await this.flushIncidents();
    } catch {
      // Incidents stay queued; ending the shift must not wait for them.
    }
    let result: 'ended' | 'queued' = 'ended';
    try {
      await this.client.endShift();
    } catch (error) {
      if (error instanceof NetworkError || isServerError(error)) {
        result = 'queued';
        await this.endStore?.set(String(this.snapshot.shift?.id ?? 'pending'));
      } else if (!(error instanceof ApiError && error.code === 'no_shift')) {
        throw error;
      }
    }
    await this.dropShift();
    return result;
  }

  /** Forget the shift on this tablet and stop its GPS. */
  async dropShift() {
    await this.stopGps();
    this.set({ shift: null, gps: null, shiftState: null, routeMap: null });
  }

  /** Send an end of shift saved without signal. True while it is still pending. */
  async flushPendingEnd(): Promise<boolean> {
    if (!this.endStore || !(await this.endStore.get())) return false;
    try {
      await this.client.endShift();
    } catch (error) {
      if (error instanceof NetworkError || isServerError(error)) return true;
      if (error instanceof AuthError) throw error;
      // no_shift: it was already closed.
    }
    await this.endStore.clear();
    return false;
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
