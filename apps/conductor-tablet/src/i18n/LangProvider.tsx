import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import { deviceLocale, getLang, languageForLocale, onLang, setLang, type Lang } from './index';

const KEY = 'uta.lang';
const LangContext = createContext<Lang>('es');

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, set] = useState<Lang>(getLang());
  useEffect(() => onLang(set), []);
  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((value) => {
        if (value === 'es' || value === 'en' || value === 'qu') setLang(value);
        else setLang(languageForLocale(deviceLocale()));
      })
      .catch(() => setLang(languageForLocale(deviceLocale())));
  }, []);
  return <LangContext.Provider value={lang}>{children}</LangContext.Provider>;
}

export function useLang(): Lang {
  return useContext(LangContext);
}

export async function persistLang(next: Lang) {
  setLang(next);
  await AsyncStorage.setItem(KEY, next);
}
