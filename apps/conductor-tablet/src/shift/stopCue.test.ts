import { shouldCueStopChange } from './stopCue';

describe('stop change cue', () => {
  test('plays when the next stop becomes another one', () => {
    expect(shouldCueStopChange(3, 4, false)).toBe(true);
  });

  test('does not play when the stop is the same', () => {
    expect(shouldCueStopChange(3, 3, false)).toBe(false);
  });

  test('does not play on the first render or when the first stop arrives late', () => {
    expect(shouldCueStopChange(undefined, 3, false)).toBe(false);
    expect(shouldCueStopChange(null, 3, false)).toBe(false);
  });

  test('does not play when there is no next stop any more', () => {
    expect(shouldCueStopChange(3, null, false)).toBe(false);
  });

  test('never plays for people who reduce motion', () => {
    expect(shouldCueStopChange(3, 4, true)).toBe(false);
  });
});
