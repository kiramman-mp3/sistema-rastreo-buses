import { useCallback, useState } from 'react';
import { Alert, AppState, ScrollView, StyleSheet, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { ApiError, NetworkError } from '../src/api/client';
import { readLastSent } from '../src/gps/store';
import { alertLabel, t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { RouteMapView } from '../src/map/RouteMapView';
import { classifyStops, clock } from '../src/shift/progress';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, type } from '../src/ui/theme';

export default function ShiftScreen() {
  useLang();
  const session = useSession();
  const { shift, vehicles, routes, driver, shiftState, routeMap } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);
  const [stale, setStale] = useState(false);
  const [busFix, setBusFix] = useState<{ lat: number; lon: number } | null>(null);
  const stops = classifyStops(shiftState?.stops ?? [], shiftState?.next_stop_id ?? null);
  const alerts = shiftState?.alerts ?? [];

  useFocusEffect(
    useCallback(() => {
      let live = true;
      activateKeepAwakeAsync();
      async function tick() {
        if (!live || AppState.currentState !== 'active') return;
        try {
          await session.pullState();
          if (!session.snapshot.routeMap) await session.loadRouteMap();
          const last = await readLastSent();
          if (live && last) setBusFix({ lat: last.lat, lon: last.lon });
          if (live) setStale(false);
        } catch (error) {
          if (error instanceof ApiError && error.code === 'no_shift') {
            router.replace('/select');
            return;
          }
          if (error instanceof NetworkError && live) setStale(true);
        }
      }
      tick();
      const id = setInterval(tick, 15_000);
      return () => {
        live = false;
        clearInterval(id);
        deactivateKeepAwake();
      };
    }, [session]),
  );

  function confirmEnd() {
    Alert.alert(t('confirmEnd'), t('confirmEndBody'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('endShift'),
        style: 'destructive',
        onPress: () => {
          session.endShift().then(() => router.replace('/select')).catch(() => Alert.alert(t('network')));
        },
      },
    ]);
  }

  return (
    <View style={styles.page}>
      <ScrollView style={styles.side} contentContainerStyle={styles.sideInner}>
        <Text style={styles.title}>{t('onShift')}</Text>
        <Text style={styles.body}>{driver?.name}</Text>
        <Text style={styles.muted}>{t('bus')}: {bus?.name ?? shift?.vehicle_id} · {t('route')}: {route ? `${route.code} · ${route.name}` : shift?.route_id}</Text>
        {stale ? <Text style={styles.warn}>{t('update_error')}</Text> : null}
        <Text style={styles.section}>{t('stops')}</Text>
        {stops.map((stop) => (
          <Text
            key={stop.id}
            style={[styles.stop, stop.status === 'next' && styles.next, stop.status === 'arrived' && styles.done]}
          >
            {stop.status === 'arrived' ? '✓ ' : stop.status === 'next' ? '→ ' : '  '}
            {stop.name}
            {stop.status === 'arrived' ? `  ${clock(stop.arrivedAt)}` : ''}
            {stop.status === 'next' ? `  (${t('nextStop')})` : ''}
          </Text>
        ))}
        <Text style={styles.section}>{t('alerts')}</Text>
        {alerts.length === 0 ? <Text style={styles.muted}>{t('noAlerts')}</Text> : null}
        {alerts.map((alert) => (
          <Text key={alert.id} style={styles.alert}>
            {alertLabel(alert.kind)}{alert.state === 'open' ? '' : ' ·'}{alert.detail ? ` — ${alert.detail}` : ''}
          </Text>
        ))}
        <Button label={t('incident')} onPress={() => router.push('/incident')} />
        <Button label={t('gpsStatus')} onPress={() => router.push('/gps')} />
        <Button label={t('endShift')} onPress={confirmEnd} danger />
      </ScrollView>
      <RouteMapView route={routeMap} bus={busFix} nextStopId={shiftState?.next_stop_id ?? null} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, flexDirection: 'row', backgroundColor: colors.paper, gap: 12, padding: 16 },
  side: { flex: 1, maxWidth: 420 },
  sideInner: { gap: 10, paddingBottom: 24 },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700' },
  body: { fontSize: type.body, color: colors.ink },
  muted: { fontSize: type.body - 2, color: colors.muted },
  warn: { fontSize: type.body - 2, color: colors.bus },
  section: { fontSize: type.body, color: colors.ink, fontWeight: '700', marginTop: 8 },
  stop: { fontSize: type.body, color: colors.ink },
  next: { fontWeight: '700', color: colors.bus },
  done: { color: colors.muted },
  alert: { fontSize: type.body - 2, color: colors.bus },
});
