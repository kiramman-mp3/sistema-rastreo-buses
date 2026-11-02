import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

import type { TokenStore } from '../api/client';

const KEY = 'bus.driver.token';
const URL_KEY = 'bus.odoo.url';
const TIMEOUT_MS = 1500;

function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<T>((resolve) => {
    timer = setTimeout(() => resolve(fallback), ms);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timer) clearTimeout(timer);
  });
}

async function secureAvailable(): Promise<boolean> {
  return withTimeout(
    SecureStore.isAvailableAsync().catch(() => false),
    TIMEOUT_MS,
    false,
  );
}

/**
 * The session token lives only in the OS keystore. AsyncStorage is plain text and goes into
 * Android backups, so it is used only where there is no keystore at all (the web preview).
 * A token an older version left in AsyncStorage is moved to the keystore on the first read.
 */
async function safeSecureGet(key: string): Promise<string | null> {
  if (!(await secureAvailable())) return AsyncStorage.getItem(key).catch(() => null);
  let value: string | null = null;
  try {
    value = await withTimeout(SecureStore.getItemAsync(key), TIMEOUT_MS, null);
  } catch {
    value = null;
  }
  if (value !== null) return value;
  const legacy = await AsyncStorage.getItem(key).catch(() => null);
  if (legacy !== null) {
    try {
      await withTimeout(SecureStore.setItemAsync(key, legacy), TIMEOUT_MS, undefined);
    } catch {
      // Still usable for this run; the copy below is removed anyway.
    }
    await AsyncStorage.removeItem(key).catch(() => undefined);
  }
  return legacy;
}

async function safeSecureSet(key: string, value: string): Promise<void> {
  if (!(await secureAvailable())) {
    await AsyncStorage.setItem(key, value).catch(() => undefined);
    return;
  }
  try {
    await withTimeout(SecureStore.setItemAsync(key, value), TIMEOUT_MS, undefined);
  } catch {
    // Never fall back to plain text: at worst the driver signs in again after a restart.
  }
  await AsyncStorage.removeItem(key).catch(() => undefined);
}

async function safeSecureClear(key: string): Promise<void> {
  try {
    await withTimeout(SecureStore.deleteItemAsync(key), TIMEOUT_MS, undefined);
  } catch {
    // ignore
  }
  await AsyncStorage.removeItem(key).catch(() => undefined);
}

export const secureStore: TokenStore = {
  get: () => safeSecureGet(KEY),
  set: (token) => safeSecureSet(KEY, token),
  clear: () => safeSecureClear(KEY),
};

const PENDING_END_KEY = 'bus.shift.pending_end';

/** A shift the driver ended without signal, still to be closed on the server. */
export const pendingEndStore: TokenStore = {
  get: () => AsyncStorage.getItem(PENDING_END_KEY).catch(() => null),
  set: (value) => AsyncStorage.setItem(PENDING_END_KEY, value).catch(() => undefined),
  clear: () => AsyncStorage.removeItem(PENDING_END_KEY).catch(() => undefined),
};

export const odooUrlStore: TokenStore = {
  get: () => AsyncStorage.getItem(URL_KEY).catch(() => null),
  set: (url) => AsyncStorage.setItem(URL_KEY, url).catch(() => undefined),
  clear: () => AsyncStorage.removeItem(URL_KEY).catch(() => undefined),
};
