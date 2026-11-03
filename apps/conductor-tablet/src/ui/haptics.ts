/**
 * One short vibration for the moments that commit something, never for decoration. Rules: one per
 * action, in the same instant as what the eye sees, and never the only feedback (many phones have
 * vibration off, and the web has none). A failure to vibrate is never an error.
 */
import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

async function run(effect: () => Promise<void>): Promise<void> {
  if (Platform.OS === 'web') return;
  try {
    await effect();
  } catch {
    // no vibration motor, or the system turned it off
  }
}

/** Something was committed: the SOS fired, the shift ended. */
export function hapticCommit(): Promise<void> {
  return run(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium));
}

/** An operation the driver started finished well. */
export function hapticDone(): Promise<void> {
  return run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success));
}

/** An operation the driver started failed. */
export function hapticFail(): Promise<void> {
  return run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error));
}
