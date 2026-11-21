export type Driver = { id: number; name: string };

export type Vehicle = {
  id: number;
  name: string;
  plate: string;
  route_id: number | null;
  available: boolean;
  /** False when the bus has no GPS device in Traccar yet: it cannot start a shift. */
  has_gps?: boolean;
};

export type Route = { id: number; code: string; name: string; color: string };

export type Shift = {
  id: number;
  vehicle_id: number;
  route_id: number;
  start: string;
};

/** A planned trip of this driver in the next hours: the tablet reminds them before it starts. */
export type UpcomingTrip = {
  id: number;
  planned_start: string;
  route_id: number;
  route_code: string;
  route_name: string;
  vehicle_id: number;
  vehicle_name: string;
};

export type MeResponse = {
  driver: Driver;
  vehicles: Vehicle[];
  routes: Route[];
  shift: Shift | null;
  /** Missing on servers older than the trip reminders. */
  upcoming?: UpcomingTrip[];
};

export type StartResponse = {
  shift: Shift;
  traccar_unique_id: string;
  gps_url: string;
};

export type StopState = {
  id: number;
  name: string;
  sequence: number;
  arrived_at: string | null;
  /** When the bus should be at this stop on its scheduled trip (null when it has none right now). */
  planned_at?: string | null;
  /** Minutes after the planned time once the bus reached the stop (negative: early). */
  delay_min?: number | null;
};

export type Alert = {
  id: number;
  kind: 'speeding' | 'offline' | 'long_stop' | 'off_route' | 'skipped_stop' | string;
  state: 'open' | 'closed' | string;
  detail: string;
  start: string;
};

export type SosState = {
  id: number;
  sent_at: string | null;
  seen_at: string | null;
  seen_by: string | null;
};

export type StateResponse = {
  shift: Shift;
  /** The last SOS of this shift and whether the office saw it (null when there was none). */
  sos?: SosState | null;
  current_stop_id: number | null;
  next_stop_id: number | null;
  /** 'back' once the bus reached the last stop; the stops then come in reverse order. */
  direction?: 'forward' | 'back';
  stops: StopState[];
  alerts: Alert[];
};

export type RouteStop = {
  id: number;
  name: string;
  sequence: number;
  lat: number;
  lon: number;
  radius: number;
};

export type RouteMap = {
  id: number;
  code: string;
  name: string;
  color: string;
  stops: RouteStop[];
  lines: { name: string; km: number; points: number[][] }[];
  /** Map tiles chosen in Odoo (Settings > Map tiles); older servers do not send it. */
  tile_url?: string;
};

export type IncidentKind = 'breakdown' | 'traffic' | 'accident' | 'other' | 'sos';

export type IncidentDraft = {
  kind: IncidentKind;
  note: string;
  lat: number | null;
  lon: number | null;
  /** When the driver pressed the button (ISO, UTC). Odoo keeps it for incidents sent later. */
  reported_at?: string;
};

export type FineCheck = { label: string; detail: string; ok: boolean };

/** A confirmed fine of this driver. Proposals still in review never reach the tablet. */
export type Fine = {
  id: number;
  number: string;
  type: string;
  rule: string;
  state: 'fined' | 'appealed' | 'discarded' | string;
  occurred_at: string | null;
  vehicle: string;
  route: string;
  /** One line with the figure that makes the fine, in the language of the app. */
  headline: string;
  /** Why the system proposed it, in plain words. */
  summary: string;
  amount: number;
  currency: string;
  simulated: boolean;
  can_appeal: boolean;
  appeal_deadline: string | null;
  appeal_text: string | null;
  appeal_date: string | null;
  appeal_result: 'accepted' | 'rejected' | null;
  /** What the office answered, once the appeal is resolved. */
  appeal_answer: string | null;
  checks: FineCheck[];
};

export type FinesResponse = {
  fines: Fine[];
};
