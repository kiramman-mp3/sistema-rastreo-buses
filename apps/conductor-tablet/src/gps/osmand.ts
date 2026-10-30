export const MS_TO_KNOTS = 1.94384;

export type Fix = {
  lat: number;
  lon: number;
  timestampMs: number;
  speedMs: number | null;
  bearing: number | null;
  altitude: number | null;
  accuracy: number | null;
  batt: number | null;
};

function param(url: URL, key: string, value: number | string | null, digits?: number) {
  if (value === null || Number.isNaN(Number(value))) return;
  if (typeof value === 'number' && !Number.isFinite(value)) return;
  url.searchParams.set(key, typeof value === 'number' && digits !== undefined ? value.toFixed(digits) : String(value));
}

export function buildOsmAndUrl(gpsUrl: string, uniqueId: string, fix: Fix): string {
  const url = new URL(gpsUrl.includes('://') ? gpsUrl : `http://${gpsUrl}`);
  url.searchParams.set('id', uniqueId);
  param(url, 'lat', fix.lat, 6);
  param(url, 'lon', fix.lon, 6);
  param(url, 'timestamp', Math.floor(fix.timestampMs / 1000));
  if (fix.speedMs !== null && fix.speedMs >= 0) {
    param(url, 'speed', fix.speedMs * MS_TO_KNOTS, 2);
  }
  if (fix.bearing !== null && fix.bearing >= 0) {
    param(url, 'bearing', fix.bearing, 1);
  }
  if (fix.altitude !== null) param(url, 'altitude', fix.altitude, 1);
  if (fix.accuracy !== null && fix.accuracy >= 0) param(url, 'accuracy', fix.accuracy, 1);
  if (fix.batt !== null && fix.batt >= 0) param(url, 'batt', Math.round(fix.batt));
  return url.toString();
}

export function locationToFix(
  location: {
    timestamp: number;
    coords: {
      latitude: number;
      longitude: number;
      altitude: number | null;
      accuracy: number | null;
      heading: number | null;
      speed: number | null;
    };
  },
  batt: number | null,
): Fix {
  const heading = location.coords.heading;
  const speed = location.coords.speed;
  return {
    lat: location.coords.latitude,
    lon: location.coords.longitude,
    timestampMs: location.timestamp,
    speedMs: speed !== null && speed >= 0 ? speed : null,
    bearing: heading !== null && heading >= 0 ? heading : null,
    altitude: location.coords.altitude,
    accuracy: location.coords.accuracy,
    batt,
  };
}
