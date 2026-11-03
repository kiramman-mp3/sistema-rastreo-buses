import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';

import { ApiError, NetworkError } from '../src/api/client';
import { GpsPermissionError } from '../src/gps/types';
import { t, tf } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession, useSessionActions } from '../src/state/SessionContext';
import { Action, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { Notice } from '../src/ui/Notice';
import { useTheme } from '../src/ui/ThemeProvider';

export default function Select() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const session = useSession();
  const actions = useSessionActions();
  const { vehicles, routes, driver } = session.snapshot;

  const usable = (bus: (typeof vehicles)[number]) => bus.available && bus.has_gps !== false;
  const [pickedVehicle, setVehicleId] = useState<number | null>(null);
  const [pickedRoute, setRouteId] = useState<number | null>(null);
  // Derived, not stored: the list can arrive after the screen opened (started without signal).
  const vehicleId = vehicles.some((bus) => bus.id === pickedVehicle) ? pickedVehicle : (vehicles.find(usable)?.id ?? null);
  const selectedBus = vehicles.find((bus) => bus.id === vehicleId);
  const routeId = routes.some((route) => route.id === pickedRoute)
    ? pickedRoute
    : (selectedBus?.route_id ?? routes[0]?.id ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const offline = session.snapshot.offline;

  // A driver who already has an open shift belongs on the shift screen.
  useEffect(() => {
    if (session.snapshot.shift) router.replace('/shift');
  }, [session.snapshot.shift]);

  // Opened without signal: keep asking until the server answers, then go to the shift if there is one.
  useEffect(() => {
    if (!offline) return undefined;
    const id = setInterval(() => {
      actions
        .refreshMe()
        .then(() => {
          if (actions.snapshot.shift) router.replace('/shift');
        })
        .catch(() => undefined);
    }, 10_000);
    return () => clearInterval(id);
  }, [offline, actions]);

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
      else if (err instanceof ApiError && err.code === 'no_gps_url') setError(t('noGpsUrl'));
      else if (err instanceof ApiError && err.code === 'conflict') setError(t('conflict'));
      else setError(t('serverError'));
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    Alert.alert(t('confirmSignOut'), t('confirmSignOutBody'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('signOut'),
        style: 'destructive',
        onPress: () => {
          session.logout().finally(() => router.replace('/'));
        },
      },
    ]);
  }

  return (
    <Screen>
      <View style={styles.head}>
        <View style={styles.headText}>
          <Txt size="body" dim>
            {tf('selectHello', { name: driver?.name ?? '' })}
          </Txt>
          <Txt bold size="title">
            {t('selectTitle')}
          </Txt>
        </View>
        <Action label={t('signOut')} onPress={signOut} kind="quiet" />
      </View>

      {offline ? (
        <View style={[styles.note, { backgroundColor: palette.signal }]} accessibilityLiveRegion="polite">
          <Txt bold size="body" color={palette.onSignal}>
            {t('offlineRetry')}
          </Txt>
        </View>
      ) : null}

      <View style={[styles.columns, !layout.wide && styles.columnsStack, { gap: layout.gap }]}>
        <View style={styles.column}>
          <Txt size="small" dim>
            {t('chooseBus')}
          </Txt>
          <ScrollView contentContainerStyle={styles.list}>
            {vehicles.map((bus) => {
              const on = vehicleId === bus.id;
              return (
                <Pressable
                  key={bus.id}
                  disabled={!usable(bus)}
                  onPress={() => {
                    setVehicleId(bus.id);
                    if (bus.route_id) setRouteId(bus.route_id);
                  }}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on, disabled: !usable(bus) }}
                  style={[
                    styles.option,
                    { minHeight: layout.hit + 8, backgroundColor: on ? palette.ink : palette.panel, opacity: usable(bus) ? 1 : 0.45 },
                  ]}
                >
                  <Txt bold size="data" color={on ? palette.ground : palette.ink}>
                    {bus.name}
                  </Txt>
                  <Txt size="small" color={on ? palette.ground : palette.ink2}>
                    {!bus.available
                      ? `${bus.plate} · ${t('busTaken')}`
                      : bus.has_gps === false
                        ? `${bus.plate} · ${t('busNoGps')}`
                        : bus.plate}
                  </Txt>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        <View style={styles.column}>
          <Txt size="small" dim>
            {t('chooseRoute')}
          </Txt>
          <ScrollView contentContainerStyle={styles.list}>
            {routes.map((route) => {
              const on = routeId === route.id;
              return (
                <Pressable
                  key={route.id}
                  onPress={() => setRouteId(route.id)}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on }}
                  style={[styles.option, styles.routeOption, { minHeight: layout.hit + 8, backgroundColor: on ? palette.ink : palette.panel }]}
                >
                  <View style={[styles.chip, { backgroundColor: route.color || palette.accent }]}>
                    <Txt bold size="body" color="#FFFFFF">
                      {route.code}
                    </Txt>
                  </View>
                  <Txt bold size="body" color={on ? palette.ground : palette.ink} lines={2} style={styles.routeName}>
                    {route.name}
                  </Txt>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      </View>

      {error ? (
        <Notice item={{ key: 'error', tone: 'danger', title: error, live: 'polite' }} />
      ) : null}

      <Action
        label={busy ? t('loading') : t('startShift')}
        sub={selectedBus && routeId ? `${selectedBus.name} · ${routes.find((r) => r.id === routeId)?.code ?? ''}` : undefined}
        onPress={start}
        kind="accent"
        disabled={busy || !vehicleId || !routeId}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  headText: {
    flexShrink: 1,
  },
  head: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 16,
  },
  note: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
  },
  columns: {
    flex: 1,
    flexDirection: 'row',
  },
  columnsStack: {
    flexDirection: 'column',
  },
  column: {
    flex: 1,
    gap: 8,
  },
  list: {
    gap: 10,
    paddingBottom: 8,
  },
  option: {
    borderRadius: 8,
    paddingHorizontal: 20,
    paddingVertical: 10,
    justifyContent: 'center',
  },
  routeOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  chip: {
    minWidth: 56,
    height: 44,
    paddingHorizontal: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  routeName: {
    flex: 1,
  },
});
