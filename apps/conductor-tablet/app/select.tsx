import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';

import { ApiError, NetworkError } from '../src/api/client';
import { GpsPermissionError } from '../src/gps/types';
import { t, tf } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession, useSessionActions } from '../src/state/SessionContext';
import { Action, Press, Screen, Txt } from '../src/ui/cabin';
import { readableOn } from '../src/ui/contrast';
import { useLayout } from '../src/ui/layout';
import { Notice } from '../src/ui/Notice';
import { useTheme } from '../src/ui/ThemeProvider';
import { shape, space } from '../src/ui/theme';

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

  // With a large system font the page scrolls as a whole; otherwise each list scrolls on its own.
  const renderList = (children: ReactNode) =>
    layout.largeText ? (
      <View style={styles.list}>{children}</View>
    ) : (
      <ScrollView contentContainerStyle={styles.list}>{children}</ScrollView>
    );

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

  const content = (
    <>
      <View style={[styles.head, layout.largeText && styles.headStack]}>
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

      <View
        style={[
          styles.columns,
          !layout.wide && styles.columnsStack,
          layout.largeText && styles.unfilled,
          { gap: layout.gap },
        ]}
      >
        <View style={[styles.column, layout.largeText && styles.unfilled]}>
          <Txt size="small" dim>
            {t('chooseBus')}
          </Txt>
          {renderList(
            <>
            {vehicles.length === 0 ? (
              <Notice item={{ key: 'no-buses', tone: 'warn', title: t('noBuses'), live: 'polite' }} />
            ) : null}
            {vehicles.map((bus) => {
              const on = vehicleId === bus.id;
              return (
                <Press
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
                </Press>
              );
            })}
            </>,
          )}
        </View>

        <View style={[styles.column, layout.largeText && styles.unfilled]}>
          <Txt size="small" dim>
            {t('chooseRoute')}
          </Txt>
          {renderList(
            <>
            {routes.length === 0 ? (
              <Notice item={{ key: 'no-routes', tone: 'warn', title: t('noRoutes'), live: 'polite' }} />
            ) : null}
            {routes.map((route) => {
              const on = routeId === route.id;
              return (
                <Press
                  key={route.id}
                  onPress={() => setRouteId(route.id)}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on }}
                  style={[styles.option, styles.routeOption, { minHeight: layout.hit + 8, backgroundColor: on ? palette.ink : palette.panel }]}
                >
                  <View style={[styles.chip, { backgroundColor: route.color || palette.accent }]}>
                    <Txt bold size="body" color={readableOn(route.color || palette.accent)}>
                      {route.code}
                    </Txt>
                  </View>
                  <Txt bold size="body" color={on ? palette.ground : palette.ink} lines={2} style={styles.routeName}>
                    {route.name}
                  </Txt>
                </Press>
              );
            })}
            </>,
          )}
        </View>
      </View>

      {vehicles.length > 0 && !vehicles.some(usable) && !offline ? (
        <Notice item={{ key: 'all-taken', tone: 'warn', title: t('allBusesTaken'), live: 'polite' }} />
      ) : null}

      {error ? (
        <Notice item={{ key: 'error', tone: 'danger', title: error, live: 'polite' }} />
      ) : null}
    </>
  );
  // The main action stays at the bottom in either case; with a large font only the content above it scrolls.
  const startButton = (
    <Action
      label={busy ? t('loading') : t('startShift')}
      sub={selectedBus && routeId ? `${selectedBus.name} · ${routes.find((r) => r.id === routeId)?.code ?? ''}` : undefined}
      onPress={start}
      kind="accent"
      disabled={busy || !vehicleId || !routeId}
    />
  );

  return (
    <Screen>
      {layout.largeText ? (
        <ScrollView
          style={styles.flowScroll}
          contentContainerStyle={{ gap: layout.gap }}
          showsVerticalScrollIndicator={false}
        >
          {content}
        </ScrollView>
      ) : (
        content
      )}
      {startButton}
    </Screen>
  );
}

const styles = StyleSheet.create({
  headText: {
    flexShrink: 1,
  },
  // With a large system font the title and its button no longer fit side by side: the button goes below.
  // Large system font: the page scrolls as a whole, so nothing here may claim the leftover height.
  flowScroll: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 0,
  },
  unfilled: {
    flexGrow: 0,
    flexShrink: 0,
    flexBasis: 'auto',
  },
  headStack: {
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  head: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: space[4],
  },
  note: {
    paddingHorizontal: space[4],
    paddingVertical: space[3],
    ...shape.control,
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
    gap: space[2],
  },
  list: {
    gap: space[2],
    paddingBottom: space[2],
  },
  option: {
    ...shape.control,
    paddingHorizontal: space[5],
    paddingVertical: space[3],
    justifyContent: 'center',
  },
  routeOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[4],
  },
  chip: {
    minWidth: 56,
    minHeight: 44,
    paddingHorizontal: space[3],
    ...shape.control,
    alignItems: 'center',
    justifyContent: 'center',
  },
  routeName: {
    flex: 1,
  },
});
