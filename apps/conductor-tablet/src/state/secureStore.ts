import * as SecureStore from 'expo-secure-store';

import type { TokenStore } from '../api/client';

const KEY = 'bus.driver.token';

export const secureStore: TokenStore = {
  get: () => SecureStore.getItemAsync(KEY),
  set: (token) => SecureStore.setItemAsync(KEY, token),
  clear: () => SecureStore.deleteItemAsync(KEY),
};
