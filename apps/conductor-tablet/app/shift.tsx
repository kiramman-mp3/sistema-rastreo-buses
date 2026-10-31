import { useCallback, useState } from 'react';
import { Alert, AppState, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
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
import { colors, hit, type } from '../src/ui/theme';

export default function ShiftScreen() {
  useLang();
  const session = useSession();
  const { shift, vehicles, routes, driver, shiftState, routeMap } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);

  const [stale, setStale] = useState(false);
  const [busFix, setBusFix] = useState<{ lat: number; lon: number } | null>(null);

  const stops = classifyStops(shiftState?.stops ?? [], shiftState?.next_stop_id ?? null);
  const nextStop = stops.find((s) => s.status === 'next');
  const arrivedStopsCount = stops.filter((s) => s.status === 'arrived').length;
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
          session
            .endShift()
            .then(() => router.replace('/select'))
            .catch(() => Alert.alert(t('network')));
        },
      },
    ]);
  }

  function handleSignOut() {
    Alert.alert(t('confirmSignOut'), t('confirmSignOutShiftBody'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('signOut'),
        style: 'destructive',
        onPress: async () => {
          try {
            await session.endShift();
          } catch {
            // End shift on server or fallback locally
          }
          await session.logout();
          router.replace('/');
        },
      },
    ]);
  }

  return (
    <View style={styles.page}>
      {/* Side Control Panel */}
      <View style={styles.sidePanel}>
        {/* Top Header Card */}
        <View style={styles.headerCard}>
          <View style={styles.headerDriver}>
            <View style={styles.driverAvatar}>
              <Text style={styles.driverAvatarText}>
                {(driver?.name || 'C').charAt(0).toUpperCase()}
              </Text>
            </View>
            <View style={styles.headerMeta}>
              <Text style={styles.headerDriverName} numberOfLines={1}>
                {driver?.name ?? t('driverLabel')}
              </Text>
              <View style={styles.headerTags}>
                <View style={styles.busTag}>
                  <Text style={styles.busTagText}>🚌 {bus?.name ?? shift?.vehicle_id}</Text>
                </View>
                {bus?.plate ? <Text style={styles.plateText}>{bus.plate}</Text> : null}
              </View>
            </View>
          </View>
          <Pressable onPress={handleSignOut} style={styles.signOutBtn}>
            <Text style={styles.signOutText}>{t('signOut')}</Text>
          </Pressable>
        </View>

        {/* Route Banner */}
        <View style={styles.routeBanner}>
          <View style={styles.routePill}>
            <Text style={styles.routePillText}>{route?.code ?? 'RUTA'}</Text>
          </View>
          <Text style={styles.routeTitle} numberOfLines={1}>
            {route?.name ?? `${t('route')} ${shift?.route_id ?? ''}`}
          </Text>
        </View>

        {/* Hero Next Stop Card */}
        <View style={styles.heroCard}>
          <View style={styles.heroHeader}>
            <Text style={styles.heroTag}>{t('nextStopHero')}</Text>
            {stops.length > 0 ? (
              <Text style={styles.heroProgress}>
                {arrivedStopsCount} / {stops.length} {t('stops').toLowerCase()}
              </Text>
            ) : null}
          </View>
          <Text style={styles.heroStopName} numberOfLines={2}>
            {nextStop ? nextStop.name : t('noNextStop')}
          </Text>
          {nextStop ? (
            <View style={styles.heroFooter}>
              <View style={styles.liveIndicator}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>GPS Transmitiendo</Text>
              </View>
            </View>
          ) : null}
        </View>

        {stale ? (
          <View style={styles.warnBanner}>
            <Text style={styles.warnText}>⚠️ {t('update_error')}</Text>
          </View>
        ) : null}

        {/* Stops Scroll Section */}
        <ScrollView style={styles.scrollSection} contentContainerStyle={styles.scrollInner}>
          <Text style={styles.sectionHeading}>{t('stops')}</Text>
          {stops.length === 0 ? (
            <Text style={styles.emptyText}>{t('noStopsAvailable')}</Text>
          ) : (
            <View style={styles.stopsList}>
              {stops.map((stop, index) => {
                const isArrived = stop.status === 'arrived';
                const isNext = stop.status === 'next';
                return (
                  <View
                    key={stop.id}
                    style={[
                      styles.stopRow,
                      isNext && styles.stopRowNext,
                      isArrived && styles.stopRowArrived,
                    ]}
                  >
                    <View
                      style={[
                        styles.stopBadge,
                        isNext && styles.stopBadgeNext,
                        isArrived && styles.stopBadgeArrived,
                      ]}
                    >
                      {isArrived ? (
                        <Text style={styles.stopBadgeTextArrived}>✓</Text>
                      ) : isNext ? (
                        <Text style={styles.stopBadgeTextNext}>➔</Text>
                      ) : (
                        <Text style={styles.stopBadgeTextLater}>{index + 1}</Text>
                      )}
                    </View>
                    <View style={styles.stopInfo}>
                      <Text
                        style={[
                          styles.stopName,
                          isNext && styles.stopNameNext,
                          isArrived && styles.stopNameArrived,
                        ]}
                        numberOfLines={1}
                      >
                        {stop.name}
                      </Text>
                      {isArrived && stop.arrivedAt ? (
                        <Text style={styles.stopTime}>Llegó: {clock(stop.arrivedAt)}</Text>
                      ) : null}
                      {isNext ? (
                        <Text style={styles.stopNextSub}>{t('nextStop')}</Text>
                      ) : null}
                    </View>
                  </View>
                );
              })}
            </View>
          )}

          {/* Alerts section */}
          {alerts.length > 0 ? (
            <View style={styles.alertsContainer}>
              <Text style={styles.sectionHeading}>{t('alerts')}</Text>
              {alerts.map((alert) => (
                <View key={alert.id} style={styles.alertCard}>
                  <Text style={styles.alertIcon}>⚠️</Text>
                  <Text style={styles.alertText}>
                    {alertLabel(alert.kind)}
                    {alert.detail ? ` — ${alert.detail}` : ''}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
        </ScrollView>

        {/* Action Buttons Footer */}
        <View style={styles.footerActions}>
          <View style={styles.secondaryBtnRow}>
            <Button
              label={t('incident')}
              variant="secondary"
              onPress={() => router.push('/incident')}
              style={styles.halfBtn}
            />
            <Button
              label={t('gpsStatus')}
              variant="secondary"
              onPress={() => router.push('/gps')}
              style={styles.halfBtn}
            />
          </View>
          <Button
            label={t('endShift')}
            variant="danger"
            onPress={confirmEnd}
            style={styles.endBtn}
          />
        </View>
      </View>

      {/* Map View */}
      <View style={styles.mapContainer}>
        <RouteMapView
          route={routeMap}
          bus={busFix}
          nextStopId={shiftState?.next_stop_id ?? null}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: colors.paper,
  },
  sidePanel: {
    width: 380,
    backgroundColor: '#FFFFFF',
    borderRightWidth: 1,
    borderRightColor: colors.line,
    padding: 16,
    gap: 12,
  },
  headerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  headerDriver: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flex: 1,
  },
  driverAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.routeLight,
    borderWidth: 2,
    borderColor: colors.route,
    alignItems: 'center',
    justifyContent: 'center',
  },
  driverAvatarText: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.route,
  },
  headerMeta: {
    flex: 1,
    gap: 2,
  },
  headerDriverName: {
    fontSize: type.body,
    fontWeight: '800',
    color: colors.ink,
  },
  headerTags: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  busTag: {
    backgroundColor: '#F1F5F9',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  busTagText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.ink,
  },
  plateText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.muted,
  },
  signOutBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.bus,
    backgroundColor: colors.busLight,
  },
  signOutText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.bus,
  },
  routeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.paper,
    padding: 10,
    borderRadius: 10,
  },
  routePill: {
    backgroundColor: colors.route,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  routePillText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '800',
  },
  routeTitle: {
    fontSize: type.body - 1,
    fontWeight: '700',
    color: colors.ink,
    flex: 1,
  },
  heroCard: {
    backgroundColor: colors.route,
    borderRadius: 12,
    padding: 16,
    gap: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  heroHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  heroTag: {
    fontSize: 11,
    fontWeight: '900',
    color: '#A7F3D0',
    letterSpacing: 1.2,
  },
  heroProgress: {
    fontSize: 12,
    color: '#E6FFFA',
    fontWeight: '600',
  },
  heroStopName: {
    fontSize: 22,
    fontWeight: '900',
    color: '#FFFFFF',
    lineHeight: 28,
  },
  heroFooter: {
    marginTop: 4,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#34D399',
  },
  liveText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#D1FAE5',
  },
  warnBanner: {
    backgroundColor: colors.busLight,
    padding: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.bus,
  },
  warnText: {
    fontSize: 12,
    color: colors.bus,
    fontWeight: '700',
  },
  scrollSection: {
    flex: 1,
  },
  scrollInner: {
    gap: 8,
    paddingBottom: 12,
  },
  sectionHeading: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.muted,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginTop: 4,
  },
  emptyText: {
    fontSize: 13,
    color: colors.muted,
    fontStyle: 'italic',
    paddingVertical: 8,
  },
  stopsList: {
    gap: 6,
  },
  stopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#FAFAFA',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  stopRowNext: {
    backgroundColor: colors.routeLight,
    borderColor: colors.route,
    borderWidth: 2,
  },
  stopRowArrived: {
    backgroundColor: '#F8FAFC',
    opacity: 0.65,
  },
  stopBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: '#E2E8F0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopBadgeNext: {
    backgroundColor: colors.route,
  },
  stopBadgeArrived: {
    backgroundColor: '#10B981',
  },
  stopBadgeTextLater: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.muted,
  },
  stopBadgeTextNext: {
    fontSize: 13,
    fontWeight: '800',
    color: '#FFF',
  },
  stopBadgeTextArrived: {
    fontSize: 13,
    fontWeight: '800',
    color: '#FFF',
  },
  stopInfo: {
    flex: 1,
  },
  stopName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.ink,
  },
  stopNameNext: {
    fontWeight: '800',
    color: colors.route,
    fontSize: 15,
  },
  stopNameArrived: {
    color: colors.muted,
    textDecorationLine: 'line-through',
  },
  stopTime: {
    fontSize: 11,
    color: colors.muted,
  },
  stopNextSub: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.route,
  },
  alertsContainer: {
    gap: 6,
    marginTop: 8,
  },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.busLight,
    padding: 8,
    borderRadius: 6,
  },
  alertIcon: {
    fontSize: 14,
  },
  alertText: {
    fontSize: 12,
    color: colors.bus,
    fontWeight: '700',
    flex: 1,
  },
  footerActions: {
    gap: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  secondaryBtnRow: {
    flexDirection: 'row',
    gap: 8,
  },
  halfBtn: {
    flex: 1,
    minHeight: 44,
  },
  endBtn: {
    minHeight: 48,
  },
  mapContainer: {
    flex: 1,
    backgroundColor: colors.paper,
  },
});
