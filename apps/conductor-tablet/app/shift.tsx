import { useEffect } from 'react';
import { router } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import { StyleSheet, Text, View } from 'react-native';

import { t } from '../src/i18n';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, type } from '../src/ui/theme';

export default function ShiftScreen() {
  const session = useSession();
  const { shift, vehicles, routes, driver } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);

  useEffect(() => {
    activateKeepAwakeAsync();
    return () => {
      deactivateKeepAwake();
    };
  }, []);

  async function signOut() {
    await session.logout();
    router.replace('/login');
  }

  return (
    <View style={styles.page}>
      <Text style={styles.title}>{t('onShift')}</Text>
      <Text style={styles.body}>{driver?.name}</Text>
      <Text style={styles.body}>{t('bus')}: {bus?.name ?? shift?.vehicle_id}</Text>
      <Text style={styles.body}>{t('route')}: {route ? `${route.code} · ${route.name}` : shift?.route_id}</Text>
      <Button label={t('gpsStatus')} onPress={() => router.push('/gps')} />
      <Button label={t('signOut')} onPress={signOut} danger />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper, padding: 32, justifyContent: 'center', gap: 16, maxWidth: 640, alignSelf: 'center', width: '100%' },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700' },
  body: { fontSize: type.body, color: colors.ink },
});
