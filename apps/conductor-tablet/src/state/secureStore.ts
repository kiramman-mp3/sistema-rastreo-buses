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

async function safeSecureGet(key: string): Promise<string | null> {
  try {
    const isAvail = await withTimeout(
      SecureStore.isAvailableAsync().catch(() => false),
      TIMEOUT_MS,
      false,
    );
    if (!isAvail) {
      return AsyncStorage.getItem(key);
    }
    const val = await withTimeout(SecureStore.getItemAsync(key), TIMEOUT_MS, null);
    if (val !== null) return val;
    return AsyncStorage.getItem(key);
  } catch {
    try {
      await SecureStore.deleteItemAsync(key).catch(() => undefined);
    } catch {
      // ignore
    }
    return AsyncStorage.getItem(key).catch(() => null);
  }
}

async function safeSecureSet(key: string, value: string): Promise<void> {
  try {
    await withTimeout(SecureStore.setItemAsync(key, value), TIMEOUT_MS, undefined);
  } catch {
    // ignore secure store write failure, fall back to AsyncStorage
  }
  await AsyncStorage.setItem(key, value).catch(() => undefined);
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

export const odooUrlStore: TokenStore = {
  get: () => AsyncStorage.getItem(URL_KEY).catch(() => null),
  set: (url) => AsyncStorage.setItem(URL_KEY, url).catch(() => undefined),
  clear: () => AsyncStorage.removeItem(URL_KEY).catch(() => undefined),
};
