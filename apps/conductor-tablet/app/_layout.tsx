import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { SessionProvider } from '../src/state/SessionContext';
import { colors } from '../src/ui/theme';

export default function Layout() {
  return (
    <SessionProvider>
      <StatusBar style="dark" hidden />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.paper },
          animation: 'none',
        }}
      />
    </SessionProvider>
  );
}
