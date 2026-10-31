import { useCallback, useRef, useState } from 'react';
import { router } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { gpsPermissionSnapshot } from '../src/gps/permissions';
import { locationQueue, readLastSent } from '../src/gps/store';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, type } from '../src/ui/theme';

export default function GpsScreen() {
  useLang();
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
        ? `${new Date(sent.at).toLocaleTimeString()} (${sent.lat.toFixed(5)}, ${sent.lon.toFixed(5)})`
        : t('gpsNone'),
    );
  }, []);

  const opened = useRef(false);

  const id = session.snapshot.gps?.uniqueId;
  const host = session.snapshot.gps?.url;

  const isFgOk = foreground === t('granted');
  const isBgOk = background === t('granted');

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      onLayout={() => {
        if (opened.current) return;
        opened.current = true;
        void refresh();
      }}
    >
      <View style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.title}>{t('gpsStatus')}</Text>
          <Text style={styles.subtitle}>Diagnóstico en tiempo real de telemetría y transmisión satelital</Text>
        </View>

        <View style={styles.metricsGrid}>
          {/* Foreground Permission */}
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>{t('gpsForeground')}</Text>
            <View style={[styles.statusBadge, isFgOk ? styles.badgeOk : styles.badgeError]}>
              <View style={[styles.dot, isFgOk ? styles.dotOk : styles.dotError]} />
              <Text style={[styles.statusText, isFgOk ? styles.textOk : styles.textError]}>
                {foreground}
              </Text>
            </View>
          </View>

          {/* Background Permission */}
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>{t('gpsBackground')}</Text>
            <View style={[styles.statusBadge, isBgOk ? styles.badgeOk : styles.badgeError]}>
              <View style={[styles.dot, isBgOk ? styles.dotOk : styles.dotError]} />
              <Text style={[styles.statusText, isBgOk ? styles.textOk : styles.textError]}>
                {background}
              </Text>
            </View>
          </View>

          {/* Queue Count */}
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>{t('gpsQueue')}</Text>
            <Text style={styles.metricBigNum}>{queue}</Text>
            <Text style={styles.metricHint}>{queue === 0 ? 'Sin paquetes pendientes' : 'Pendientes de envío'}</Text>
          </View>

          {/* Hardware ID */}
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>Dispositivo Traccar</Text>
            <Text style={styles.metricMono}>{id ? `ID: ${id}` : 'No asignado'}</Text>
            <Text style={styles.metricHint} numberOfLines={1}>{host || 'Servidor Traccar'}</Text>
          </View>
        </View>

        {/* Last Send Block */}
        <View style={styles.telemetryCard}>
          <Text style={styles.telemetryLabel}>{t('gpsLast')}</Text>
          <Text style={styles.telemetryValue}>{last}</Text>
        </View>

        <View style={styles.actions}>
          <Button label="Actualizar telemetría" variant="secondary" onPress={refresh} />
          <Button label={t('backToShift')} onPress={() => router.back()} />
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    backgroundColor: colors.paper,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    width: '100%',
    maxWidth: 640,
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 28,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  header: {
    gap: 4,
    marginBottom: 4,
  },
  title: {
    fontSize: type.title,
    fontWeight: '800',
    color: colors.ink,
  },
  subtitle: {
    fontSize: 14,
    color: colors.muted,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metricCard: {
    flex: 1,
    minWidth: 135,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    gap: 6,
  },
  metricLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.muted,
    textTransform: 'uppercase',
  },
  metricBigNum: {
    fontSize: 24,
    fontWeight: '900',
    color: colors.ink,
  },
  metricMono: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.ink,
  },
  metricHint: {
    fontSize: 11,
    color: colors.muted,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeOk: {
    backgroundColor: colors.routeLight,
  },
  badgeError: {
    backgroundColor: colors.busLight,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  dotOk: {
    backgroundColor: colors.route,
  },
  dotError: {
    backgroundColor: colors.bus,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '700',
  },
  textOk: {
    color: colors.route,
  },
  textError: {
    color: colors.bus,
  },
  telemetryCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    gap: 4,
  },
  telemetryLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.muted,
    textTransform: 'uppercase',
  },
  telemetryValue: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.ink,
  },
  actions: {
    gap: 10,
    marginTop: 4,
  },
});
