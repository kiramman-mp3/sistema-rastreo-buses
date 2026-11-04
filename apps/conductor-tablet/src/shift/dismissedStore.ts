
import type { KeyValue } from '../gps/queue';

/** What the driver closed on the shift screen, kept for the shift so a refresh never brings it back. */
const key = (shiftId: number) => `uta.dismissed.${shiftId}`;
const MAX_KEPT = 50;

export function parseDismissed(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
  } catch {
    return [];
  }
}

export async function loadDismissed(shiftId: number, kv: KeyValue): Promise<string[]> {
  try {
    return parseDismissed(await kv.getItem(key(shiftId)));
  } catch {
    return [];
  }
}

export async function saveDismissed(shiftId: number, keys: string[], kv: KeyValue): Promise<void> {
  try {
    await kv.setItem(key(shiftId), JSON.stringify(keys.slice(-MAX_KEPT)));
  } catch {
    // Not remembered: the notice would show again after a restart, which is only a nuisance.
  }
}
