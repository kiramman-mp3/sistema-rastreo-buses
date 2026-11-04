import { useEffect, useState } from 'react';

import { gpsHealth, type GpsHealth } from './health';
import { gpsPermissionSnapshot } from './permissions';
import { locationQueue, readLastSample, readLastSent } from './store';

export type GpsReading = {
  health: GpsHealth;
  queued: number;
  speedKmh: number | null;
  sampleAt: number | null;
  lat: number | null;
  lon: number | null;
  /** When this reading was taken: the clock the motion lock compares the sample against. */
  readAt: number;
};

const EMPTY: GpsReading = { health: 'waiting', queued: 0, speedKmh: null, sampleAt: null, lat: null, lon: null, readAt: 0 };

/** Reads what the background GPS task left on the device every few seconds. */
export function useGpsHealth(everyMs = 3_000): GpsReading {
  const [reading, setReading] = useState<GpsReading>(EMPTY);

  useEffect(() => {
    let live = true;
    async function read() {
      const [permissions, sample, sent, queued] = await Promise.all([
        gpsPermissionSnapshot().catch(() => ({ background: 'unknown' as const })),
        readLastSample().catch(() => null),
        readLastSent().catch(() => null),
        locationQueue.size().catch(() => 0),
      ]);
      if (!live) return;
      const readAt = Date.now();
      const permission =
        permissions.background === 'granted' ? 'granted' : permissions.background === 'denied' ? 'denied' : 'unknown';
      setReading({
        health: gpsHealth({
          permission,
          lastSampleAt: sample?.at ?? null,
          lastSentAt: sent?.at ?? null,
          queued,
          now: readAt,
        }),
        readAt,
        queued,
        speedKmh: sample?.speedKmh ?? null,
        sampleAt: sample?.at ?? null,
        lat: sample?.lat ?? sent?.lat ?? null,
        lon: sample?.lon ?? sent?.lon ?? null,
      });
    }
    read();
    const id = setInterval(read, everyMs);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [everyMs]);

  return reading;
}
