import '../src/gps/task';

import { useFonts } from 'expo-font';
import { Stack, usePathname } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { View } from 'react-native';

import { appVersion, errorQueue } from '../src/diagnostics';
import { installErrorReporting, setCurrentScreen, type ErrorUtilsLike } from '../src/diagnostics/install';
import { LangProvider } from '../src/i18n/LangProvider';
import { SessionProvider } from '../src/state/SessionContext';
import { fonts } from '../src/ui/theme';
import { ThemeProvider, useTheme } from '../src/ui/ThemeProvider';

// Uncaught errors are kept (and sent to the office when there is signal) before React Native handles them.
installErrorReporting((globalThis as { ErrorUtils?: ErrorUtilsLike }).ErrorUtils, errorQueue, appVersion);

function Screens() {
  const { palette } = useTheme();
  const pathname = usePathname();
  useEffect(() => {
    setCurrentScreen(pathname);
  }, [pathname]);
  return (
    <>
      <StatusBar style={palette.mode === 'day' ? 'dark' : 'light'} hidden />
      <Stack
        screenOptions={{
          headerShown: false,
          // the same ground as the screen: no white flash between screens at night
          contentStyle: { backgroundColor: palette.ground },
          animation: 'fade',
          animationDuration: 160,
        }}
      />
    </>
  );
}

export default function Layout() {
  const [loaded, failed] = useFonts({
    [fonts.text]: require('../assets/fonts/AtkinsonHyperlegible-Regular.ttf'),
    [fonts.bold]: require('../assets/fonts/AtkinsonHyperlegible-Bold.ttf'),
  });

  return (
    <ThemeProvider>
      <SessionProvider>
        <LangProvider>
          {loaded || failed ? <Screens /> : <Blank />}
        </LangProvider>
      </SessionProvider>
    </ThemeProvider>
  );
}

function Blank() {
  const { palette } = useTheme();
  return <View style={{ flex: 1, backgroundColor: palette.ground }} />;
}
