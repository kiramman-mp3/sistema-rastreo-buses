import * as SecureStore from 'expo-secure-store';

import type { TokenStore } from '../api/client';

const KEY = 'bus.driver.token';

export const secureStore: TokenStore = {
  get: () => SecureStore.getItemAsync(KEY),
  set: (token) => SecureStore.setItemAsync(KEY, token),
  clear: () => SecureStore.deleteItemAsync(KEY),
};

const URL_KEY = 'bus.odoo.url';

export const odooUrlStore: TokenStore = {
  get: () => SecureStore.getItemAsync(URL_KEY),
  set: (url) => SecureStore.setItemAsync(URL_KEY, url),
  clear: () => SecureStore.deleteItemAsync(URL_KEY),
};
