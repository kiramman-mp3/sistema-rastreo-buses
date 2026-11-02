/**
 * What the cabin says about the GPS. It is computed from what the GPS really did, not from whether
 * the server answered: a tablet with signal but without location permission is not "sending".
 */
export type GpsHealth = 'sending' | 'saving' | 'waiting' | 'off';

export type GpsFacts = {
  permission: 'granted' | 'denied' | 'unknown';
  lastSampleAt: number | null;
  lastSentAt: number | null;
  queued: number;
  now: number;
};

/** The GPS reports every 10 s; a minute without a fix means it is not working. */
export const SAMPLE_STALE_MS = 60_000;

export function gpsHealth(facts: GpsFacts): GpsHealth {
  if (facts.permission === 'denied') return 'off';
  if (facts.lastSampleAt === null || facts.now - facts.lastSampleAt > SAMPLE_STALE_MS) return 'waiting';
  const sentRecently = facts.lastSentAt !== null && facts.now - facts.lastSentAt <= SAMPLE_STALE_MS;
  if (facts.queued > 0 && !sentRecently) return 'saving';
  return 'sending';
}
