import { createMotionLock } from './motion';

describe('motion lock', () => {
  test('locks only after 5 s above 10 km/h', () => {
    const lock = createMotionLock();
    expect(lock(30, 0, 0)).toBe(false);
    expect(lock(30, 4_000, 4_000)).toBe(false);
    expect(lock(30, 5_000, 5_000)).toBe(true);
  });

  test('unlocks at once when the bus slows down', () => {
    const lock = createMotionLock();
    lock(40, 0, 0);
    expect(lock(40, 6_000, 6_000)).toBe(true);
    expect(lock(8, 7_000, 7_000)).toBe(false);
  });

  test('a stale or unknown speed never locks the screen', () => {
    const lock = createMotionLock();
    lock(50, 0, 0);
    expect(lock(50, 0, 40_000)).toBe(false);
    expect(lock(null, 41_000, 41_000)).toBe(false);
  });
});
