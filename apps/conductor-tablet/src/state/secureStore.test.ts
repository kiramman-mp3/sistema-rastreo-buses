import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

import { odooUrlStore, secureStore } from './secureStore';

jest.mock('@react-native-async-storage/async-storage', () => {
  const store = new Map<string, string>();
  return {
    getItem: jest.fn(async (key: string) => store.get(key) ?? null),
    setItem: jest.fn(async (key: string, val: string) => {
      store.set(key, val);
    }),
    removeItem: jest.fn(async (key: string) => {
      store.delete(key);
    }),
    clear: jest.fn(async () => {
      store.clear();
    }),
  };
});

jest.mock('expo-secure-store', () => ({
  isAvailableAsync: jest.fn(),
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

describe('secureStore resilient storage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('falls back to AsyncStorage when SecureStore throws an error', async () => {
    (SecureStore.isAvailableAsync as jest.Mock).mockRejectedValue(new Error('Keystore corrupted'));
    await AsyncStorage.setItem('bus.driver.token', 'fallback-tok');

    const token = await secureStore.get();
    expect(token).toBe('fallback-tok');
  });

  test('falls back to AsyncStorage when SecureStore.isAvailableAsync is false', async () => {
    (SecureStore.isAvailableAsync as jest.Mock).mockResolvedValue(false);
    await AsyncStorage.setItem('bus.driver.token', 'async-tok');

    const token = await secureStore.get();
    expect(token).toBe('async-tok');
  });

  test('returns value from SecureStore when available', async () => {
    (SecureStore.isAvailableAsync as jest.Mock).mockResolvedValue(true);
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('secure-tok');

    const token = await secureStore.get();
    expect(token).toBe('secure-tok');
  });

  test('odooUrlStore reads and writes without KeyStore dependency', async () => {
    await odooUrlStore.set('https://odoo.uta.edu.ec');
    expect(await odooUrlStore.get()).toBe('https://odoo.uta.edu.ec');
    await odooUrlStore.clear();
    expect(await odooUrlStore.get()).toBeNull();
  });
});
