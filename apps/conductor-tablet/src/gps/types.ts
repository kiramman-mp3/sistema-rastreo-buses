export class GpsPermissionError extends Error {
  constructor() {
    super('gps_permission');
    this.name = 'GpsPermissionError';
  }
}

export type GpsController = {
  prepare(): Promise<void>;
  start(uniqueId: string, url: string): Promise<void>;
  stop(): Promise<void>;
};

export type GpsStore = {
  get(): Promise<{ uniqueId: string; url: string } | null>;
  set(value: { uniqueId: string; url: string }): Promise<void>;
  clear(): Promise<void>;
};
