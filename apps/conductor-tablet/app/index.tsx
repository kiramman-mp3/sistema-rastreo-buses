import { useEffect, useState } from 'react';
import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';

import { useSession } from '../src/state/SessionContext';
import { colors } from '../src/ui/theme';

export default function Index() {
  const { snapshot } = useSession();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), 2500);
    return () => clearTimeout(timer);
  }, []);

  if (!snapshot.ready && !timedOut) {
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
