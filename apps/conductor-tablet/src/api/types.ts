export type Driver = { id: number; name: string };

export type Vehicle = {
  id: number;
  name: string;
  plate: string;
  route_id: number | null;
  available: boolean;
};

export type Route = { id: number; code: string; name: string; color: string };

export type Shift = {
  id: number;
  vehicle_id: number;
  route_id: number;
  start: string;
};

export type MeResponse = {
  driver: Driver;
  vehicles: Vehicle[];
  routes: Route[];
  shift: Shift | null;
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
};

export type Alert = {
  id: number;
  kind: 'speeding' | 'offline' | 'long_stop' | 'off_route' | string;
  state: 'open' | 'closed' | string;
  detail: string;
  start: string;
};

export type StateResponse = {
  shift: Shift;
  current_stop_id: number | null;
  next_stop_id: number | null;
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
};

export type IncidentKind = 'breakdown' | 'traffic' | 'accident' | 'other';

export type IncidentDraft = {
  kind: IncidentKind;
  note: string;
  lat: number | null;
  lon: number | null;
};
