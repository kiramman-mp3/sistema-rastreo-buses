import { ApiError, AuthError, createClient, defaultBaseUrl, NetworkError, type DriverClient, type TokenStore } from '../api/client';
import { normalizeOdooUrl } from '../config/odooUrl';
import type {
  Driver,
  Fine,
  FinesResponse,
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
import type { TripReminders } from '../shift/reminders';

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
    /** Local notifications before the driver's next trips. */
    private reminders?: TripReminders,
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
    void this.reminders?.sync(me.upcoming ?? []);
  }

  async setOdooUrl(raw: string) {
    const url = normalizeOdooUrl(raw);
    if (!url) throw new Error('bad_odoo_url');
    // A session belongs to its server: its token is never sent to another one (DEF-061).
    if (url !== this.snapshot.odooUrl) {
      if (await this.store.get()) await this.signOutHere();
      // An end of shift saved without signal belongs to the old server.
      await this.endStore?.clear();
    }
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
    let client = this.client;
    const url = odooUrl ? normalizeOdooUrl(odooUrl) : null;
    if (odooUrl && !url) throw new Error('bad_odoo_url');
    // The tablet moves to the badge's server only once that server accepts the badge.
    if (url && url !== this.snapshot.odooUrl) client = createClient({ baseUrl: url, store: this.store });
    // The badge only buys a session; it is never kept as one. An old server without
    // login_badge answers 404 and the error reaches the scan screen.
    const { token, driver } = await client.loginBadge(badgeToken);
    if (url) await this.setOdooUrl(url);
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
    await this.signOutHere();
  }

  /** Forget the session on this tablet only. */
  private async signOutHere() {
    await this.stopGps();
    // The next driver of this tablet must not hear about the trips of this one.
    await this.reminders?.clear();
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

  /**
   * What the driver asks for by pulling the screen down: the buses, lines and next trips again and, during a
   * shift, its state and the map of the line. Throws NetworkError without signal, like the calls it makes.
   */
  async refreshAll() {
    await this.refreshMe();
    if (!this.snapshot.shift) return;
    await this.pullState();
    await this.loadRouteMap();
  }

  async loadRouteMap(): Promise<RouteMap> {
    const routeMap = await this.client.routeMap();
    this.set({ routeMap });
    return routeMap;
  }

  /** The confirmed fines of the driver. They are read when the screen opens, never kept on the tablet. */
  async loadFines(): Promise<FinesResponse> {
    return this.client.fines(getLang());
  }

  async appealFine(id: number, text: string): Promise<Fine> {
    const { fine } = await this.client.appealFine(id, text, getLang());
    return fine;
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
        // Kept for later on no signal, a server error or no session: the server takes an incident up to two
        // hours after its shift ended, so a driver signed out meanwhile can still send it. Only a request the
        // server refuses for good (bad data, no shift) is dropped.
        return !(error instanceof NetworkError || error instanceof AuthError || isServerError(error));
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
    // Stopping the GPS sends the positions saved without signal. It goes first: once the shift is closed the
    // server drops every position of the bus (DEF-058).
    await this.stopGps();
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
