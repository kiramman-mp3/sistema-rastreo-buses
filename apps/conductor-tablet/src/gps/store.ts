import AsyncStorage from '@react-native-async-storage/async-storage';

import { LocationQueue } from './queue';
import { CREDS_KEY, LAST_KEY, type GpsCreds, type LastSent } from './runtime';
import type { GpsStore } from './types';

export const gpsKv = {
  getItem: (key: string) => AsyncStorage.getItem(key),
  setItem: (key: string, value: string) => AsyncStorage.setItem(key, value),
  removeItem: (key: string) => AsyncStorage.removeItem(key),
};

export const locationQueue = new LocationQueue(gpsKv);

export const gpsStore: GpsStore = {
  async get() {
    const raw = await AsyncStorage.getItem(CREDS_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as GpsCreds;
      if (parsed.uniqueId && parsed.url) return parsed;
      return null;
    } catch {
      return null;
    }
  },
  set(value) {
    return AsyncStorage.setItem(CREDS_KEY, JSON.stringify(value));
  },
  clear() {
    return AsyncStorage.removeItem(CREDS_KEY);
  },
};

export async function readLastSent(): Promise<LastSent | null> {
  const raw = await AsyncStorage.getItem(LAST_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LastSent;
  } catch {
    return null;
  }
}

export function writeLastSent(last: LastSent) {
  return AsyncStorage.setItem(LAST_KEY, JSON.stringify(last));
}
