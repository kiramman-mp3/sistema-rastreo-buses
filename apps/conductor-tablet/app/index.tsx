import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';

import { useSession } from '../src/state/SessionContext';
import { colors } from '../src/ui/theme';

export default function Index() {
  const { snapshot } = useSession();

  // boot() always ends with ready = true, also without signal, so there is no timeout here:
  // redirecting early would send a driver with a saved session back to the login screen.
  if (!snapshot.ready) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.paper }}>
        <ActivityIndicator size="large" color={colors.route} />
      </View>
    );
  }
  if (!snapshot.token) return <Redirect href="/login" />;
  if (snapshot.shift) return <Redirect href="/shift" />;
  return <Redirect href="/select" />;
}
