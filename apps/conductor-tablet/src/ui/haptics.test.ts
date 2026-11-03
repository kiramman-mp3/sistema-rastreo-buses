import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

import { hapticCommit, hapticDone, hapticFail } from './haptics';

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Medium: 'medium' },
  NotificationFeedbackType: { Success: 'success', Error: 'error' },
}));

const impact = Haptics.impactAsync as jest.Mock;
const notification = Haptics.notificationAsync as jest.Mock;

describe('haptics', () => {
  const original = Platform.OS;
  beforeEach(() => {
    impact.mockClear();
    notification.mockClear();
  });
  afterEach(() => {
    Platform.OS = original;
  });

  test('a commit is one medium impact', async () => {
    await hapticCommit();
    expect(impact).toHaveBeenCalledTimes(1);
    expect(impact).toHaveBeenCalledWith('medium');
  });

  test('a good result and a failure are one notification each', async () => {
    await hapticDone();
    await hapticFail();
    expect(notification.mock.calls).toEqual([['success'], ['error']]);
  });

  test('a device that cannot vibrate never throws', async () => {
    impact.mockRejectedValueOnce(new Error('no vibrator'));
    await expect(hapticCommit()).resolves.toBeUndefined();
  });

  test('the web has no vibration and is left alone', async () => {
    Platform.OS = 'web';
    await hapticCommit();
    await hapticDone();
    expect(impact).not.toHaveBeenCalled();
    expect(notification).not.toHaveBeenCalled();
  });
});
