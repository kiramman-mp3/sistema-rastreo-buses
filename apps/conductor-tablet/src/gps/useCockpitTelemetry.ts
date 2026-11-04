import { useEffect, useMemo, useState } from 'react';

function toRad(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

/**
 * Calculates straight-line distance in meters between two coordinates (Haversine)
 */
export function calculateDistanceMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6371000; // Earth's radius in meters
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

export function formatDistance(meters: number | null): string {
  if (meters === null || meters < 0) return '';
  if (meters < 100) return 'Arribando ahora';
  if (meters < 1000) return `En ${meters} metros`;
  return `En ${(meters / 1000).toFixed(1)} km`;
}

function clock(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
}

export function useCockpitTelemetry(
  busFix: { lat: number; lon: number } | null,
  nextStopCoords: { lat: number; lon: number } | null,
) {
  // Hours and minutes only: seconds ticking in the corner of the eye are a distraction while driving.
  const [currentTime, setCurrentTime] = useState<string>(clock);

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(clock()), 15_000);
    return () => clearInterval(interval);
  }, []);

  const busLat = busFix?.lat;
  const busLon = busFix?.lon;
  const stopLat = nextStopCoords?.lat;
  const stopLon = nextStopCoords?.lon;
  const distanceMeters = useMemo(() => {
    if (busLat === undefined || busLon === undefined || stopLat === undefined || stopLon === undefined) return null;
    return calculateDistanceMeters(busLat, busLon, stopLat, stopLon);
  }, [busLat, busLon, stopLat, stopLon]);

  return {
    currentTime,
    distanceMeters,
    distanceFormatted: formatDistance(distanceMeters),
  };
}
