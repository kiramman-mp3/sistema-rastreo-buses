import { Fragment, useCallback, useEffect, useState, type ReactElement, type ReactNode } from 'react';
import { Alert, FlatList, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';

import { ApiError, NetworkError } from '../src/api/client';
import type { Route, Vehicle } from '../src/api/types';
import { GpsPermissionError } from '../src/gps/types';
import { t, tf } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession, useSessionActions } from '../src/state/SessionContext';
import { Action, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { Notice } from '../src/ui/Notice';
import { BusOption, RouteOption } from '../src/ui/OptionRows';
import { useTheme } from '../src/ui/ThemeProvider';
import { shape, space } from '../src/ui/theme';

type OptionListProps<T> = {
  items: T[];
  flow: boolean;
  extraData: unknown;
  empty: ReactNode;
  renderRow: (item: T) => ReactElement;
};

/**
 * A virtualised list: only the rows on screen are mounted. With a large system font the whole page scrolls
 * instead, so the rows are drawn in a plain view (the page's scroll view owns the gesture).
 */
function OptionList<T extends { id: number }>({ items, flow, extraData, empty, renderRow }: OptionListProps<T>) {
  if (flow) {
    return (
      <View style={styles.list}>
        {empty}
        {items.map((item) => (
          <Fragment key={item.id}>{renderRow(item)}</Fragment>
        ))}
      </View>
    );
  }
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => renderRow(item)}
      extraData={extraData}
      ListHeaderComponent={<>{empty}</>}
      contentContainerStyle={styles.list}
    />
  );
}

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

  // Stable, so the memoised rows only redraw when their own mark changes.
  const pickBus = useCallback((bus: Vehicle) => {
    setVehicleId(bus.id);
    if (bus.route_id) setRouteId(bus.route_id);
  }, []);
  const pickRoute = useCallback((route: Route) => setRouteId(route.id), []);

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
          (!layout.wide || layout.largeText) && styles.columnsStack,
          layout.largeText && styles.unfilled,
          { gap: layout.gap },
        ]}
      >
        <View style={[styles.column, layout.largeText && styles.unfilled]}>
          <Txt size="small" dim>
            {t('chooseBus')}
          </Txt>
          <OptionList
            items={vehicles}
            flow={layout.largeText}
            extraData={vehicleId}
            empty={
              vehicles.length === 0 ? (
                <Notice item={{ key: 'no-buses', tone: 'warn', title: t('noBuses'), live: 'polite' }} />
              ) : null
            }
            renderRow={(bus) => (
              <BusOption bus={bus} selected={vehicleId === bus.id} usable={usable(bus)} hit={layout.hit} onPick={pickBus} />
            )}
          />
        </View>

        <View style={[styles.column, layout.largeText && styles.unfilled]}>
          <Txt size="small" dim>
            {t('chooseRoute')}
          </Txt>
          <OptionList
            items={routes}
            flow={layout.largeText}
            extraData={routeId}
            empty={
              routes.length === 0 ? (
                <Notice item={{ key: 'no-routes', tone: 'warn', title: t('noRoutes'), live: 'polite' }} />
              ) : null
            }
            renderRow={(route) => (
              <RouteOption route={route} selected={routeId === route.id} hit={layout.hit} onPick={pickRoute} />
            )}
          />
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
});
