import '../src/gps/task';

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { LangProvider } from '../src/i18n/LangProvider';
import { SessionProvider } from '../src/state/SessionContext';
import { colors } from '../src/ui/theme';

export default function Layout() {
  return (
    <SessionProvider>
      <LangProvider>
      <StatusBar style="dark" hidden />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.paper },
          animation: 'none',
        }}
      />
      </LangProvider>
    </SessionProvider>
  );
}
