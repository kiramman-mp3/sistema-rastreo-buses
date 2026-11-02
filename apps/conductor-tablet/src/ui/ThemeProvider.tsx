import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { palettes, type Palette } from './theme';

export type ModeChoice = 'auto' | 'day' | 'night';

const KEY = 'uta.cabin.mode';

/** Day from 06:00 to 18:30: Ambato is near the equator, sunset hardly moves during the year. */
export function modeForHour(date: Date): 'day' | 'night' {
  const minutes = date.getHours() * 60 + date.getMinutes();
  return minutes >= 6 * 60 && minutes < 18 * 60 + 30 ? 'day' : 'night';
}

type ThemeValue = {
  palette: Palette;
  choice: ModeChoice;
  setChoice: (choice: ModeChoice) => void;
};

const ThemeContext = createContext<ThemeValue>({
  palette: palettes.day,
  choice: 'auto',
  setChoice: () => undefined,
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ModeChoice>('auto');
  const [autoMode, setAutoMode] = useState<'day' | 'night'>(() => modeForHour(new Date()));

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((saved) => {
        if (saved === 'day' || saved === 'night' || saved === 'auto') setChoiceState(saved);
      })
      .catch(() => undefined);
    const id = setInterval(() => setAutoMode(modeForHour(new Date())), 60_000);
    return () => clearInterval(id);
  }, []);

  const value = useMemo<ThemeValue>(() => {
    const mode = choice === 'auto' ? autoMode : choice;
    return {
      palette: palettes[mode],
      choice,
      setChoice: (next) => {
        setChoiceState(next);
        AsyncStorage.setItem(KEY, next).catch(() => undefined);
      },
    };
  }, [choice, autoMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
