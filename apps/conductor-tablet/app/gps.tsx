import { useCallback, useRef, useState } from 'react';
import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { t } from '../src/i18n';
import { gpsPermissionSnapshot } from '../src/gps/permissions';
import { locationQueue, readLastSent } from '../src/gps/store';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, type } from '../src/ui/theme';

export default function GpsScreen() {
  const session = useSession();
  const [foreground, setForeground] = useState('—');
  const [background, setBackground] = useState('—');
  const [queue, setQueue] = useState(0);
  const [last, setLast] = useState('');

  const refresh = useCallback(async () => {
    const permissions = await gpsPermissionSnapshot();
    setForeground(permissions.foreground === 'granted' ? t('granted') : t('denied'));
    setBackground(permissions.background === 'granted' ? t('granted') : t('denied'));
    setQueue(await locationQueue.size());
    const sent = await readLastSent();
    setLast(
      sent
        ? `${new Date(sent.at).toISOString()} · ${sent.lat.toFixed(5)}, ${sent.lon.toFixed(5)}`
        : t('gpsNone'),
    );
  }, []);

  const opened = useRef(false);

  const id = session.snapshot.gps?.uniqueId;
  const host = session.snapshot.gps?.url;

  return (
    <View
      style={styles.page}
      onLayout={() => {
        if (opened.current) return;
        opened.current = true;
        void refresh();
      }}
    >
      <Text style={styles.title}>{t('gpsStatus')}</Text>
      <Text style={styles.body}>{t('gpsForeground')}: {foreground}</Text>
      <Text style={styles.body}>{t('gpsBackground')}: {background}</Text>
      <Text style={styles.body}>{t('gpsQueue')}: {queue}</Text>
      <Text style={styles.body}>{t('gpsLast')}: {last}</Text>
      <Text style={styles.body}>id: {id ? `…${id.slice(-4)}` : '—'}</Text>
      <Text style={styles.body}>{host ?? '—'}</Text>
      <Button label={t('onShift')} onPress={() => router.back()} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper, padding: 32, justifyContent: 'center', gap: 14, maxWidth: 720, alignSelf: 'center', width: '100%' },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700' },
  body: { fontSize: type.body, color: colors.ink },
});
