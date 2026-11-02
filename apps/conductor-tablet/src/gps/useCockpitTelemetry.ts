import { useEffect, useState } from 'react';

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

export function useCockpitTelemetry(
  busFix: { lat: number; lon: number } | null,
  nextStopCoords: { lat: number; lon: number } | null,
) {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [distanceMeters, setDistanceMeters] = useState<number | null>(null);

  // 1-second system clock for cockpit display
  useEffect(() => {
    function updateClock() {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const mins = String(now.getMinutes()).padStart(2, '0');
      const secs = String(now.getSeconds()).padStart(2, '0');
      setCurrentTime(`${hours}:${mins}:${secs}`);
    }
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Compute distance to next stop
  useEffect(() => {
    if (busFix && nextStopCoords) {
      const dist = calculateDistanceMeters(
        busFix.lat,
        busFix.lon,
        nextStopCoords.lat,
        nextStopCoords.lon,
      );
      setDistanceMeters(dist);
    } else {
      setDistanceMeters(null);
    }
  }, [busFix?.lat, busFix?.lon, nextStopCoords?.lat, nextStopCoords?.lon]);

  return {
    currentTime,
    distanceMeters,
    distanceFormatted: formatDistance(distanceMeters),
  };
}
