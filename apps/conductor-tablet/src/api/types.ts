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
