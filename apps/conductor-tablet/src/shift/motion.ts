/**
 * The screen locks while the bus moves: above `thresholdKmh` for `holdMs` in a row, every control
 * except SOS stops responding. It unlocks as soon as the bus slows down or the speed is unknown
 * (a stale fix must never trap the driver behind a locked screen).
 */
export type MotionLockOptions = { thresholdKmh?: number; holdMs?: number; staleMs?: number };

export function createMotionLock({ thresholdKmh = 10, holdMs = 5_000, staleMs = 30_000 }: MotionLockOptions = {}) {
  let fastSince: number | null = null;
  return function update(speedKmh: number | null, sampleAt: number | null, now: number): boolean {
    const fresh = sampleAt !== null && now - sampleAt <= staleMs;
    if (!fresh || speedKmh === null || speedKmh <= thresholdKmh) {
      fastSince = null;
      return false;
    }
    if (fastSince === null) fastSince = sampleAt ?? now;
    return now - fastSince >= holdMs;
  };
}
