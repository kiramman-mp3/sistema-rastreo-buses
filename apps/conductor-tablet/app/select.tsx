import { useState } from 'react';
import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiError, NetworkError } from '../src/api/client';
import { GpsPermissionError } from '../src/gps/types';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, hit, type } from '../src/ui/theme';

export default function Select() {
  useLang();
  const session = useSession();
  const { vehicles, routes } = session.snapshot;
  const [vehicleId, setVehicleId] = useState<number | null>(
    vehicles.find((bus) => bus.available)?.id ?? null,
  );
  const selectedBus = vehicles.find((bus) => bus.id === vehicleId);
  const [routeId, setRouteId] = useState<number | null>(selectedBus?.route_id ?? routes[0]?.id ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function start() {
    if (!vehicleId || !routeId) return;
    setBusy(true);
    setError('');
    try {
      await session.startShift(vehicleId, routeId);
      router.replace('/shift');
    } catch (err) {
      if (err instanceof NetworkError) setError(t('network'));
      else if (err instanceof GpsPermissionError) setError(t('gpsPermission'));
      else if (err instanceof ApiError && err.code === 'no_gps') setError(t('noGps'));
      else if (err instanceof ApiError && err.status === 409) setError(t('conflict'));
      else setError(t('conflict'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>{t('chooseBus')}</Text>
      <View style={styles.row}>
        {vehicles.map((bus) => (
          <Pressable
            key={bus.id}
            disabled={!bus.available}
            onPress={() => {
              setVehicleId(bus.id);
              if (bus.route_id) setRouteId(bus.route_id);
            }}
            style={[
              styles.chip,
              vehicleId === bus.id && styles.chipOn,
              !bus.available && styles.chipOff,
            ]}
          >
            <Text style={styles.chipText}>
              {bus.name}{bus.plate ? ` · ${bus.plate}` : ''}{bus.available ? '' : ` (${t('taken')})`}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.title}>{t('chooseRoute')}</Text>
      <View style={styles.row}>
        {routes.map((route) => (
          <Pressable
            key={route.id}
            onPress={() => setRouteId(route.id)}
            style={[styles.chip, routeId === route.id && styles.chipOn]}
          >
            <Text style={styles.chipText}>{route.code} · {route.name}</Text>
          </Pressable>
        ))}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button label={t('startShift')} onPress={start} disabled={busy || !vehicleId || !routeId} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 28, gap: 16, backgroundColor: colors.paper, flexGrow: 1 },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  chip: {
    minHeight: hit,
    paddingHorizontal: 18,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.line,
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  chipOn: { borderColor: colors.route, backgroundColor: '#E7F2EE' },
  chipOff: { opacity: 0.45 },
  chipText: { fontSize: type.body, color: colors.ink },
  error: { color: colors.bus, fontSize: type.body },
});
