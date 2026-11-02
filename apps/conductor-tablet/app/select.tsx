import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { router } from 'expo-router';

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
  const { vehicles, routes, driver } = session.snapshot;

  const [vehicleId, setVehicleId] = useState<number | null>(
    vehicles.find((bus) => bus.available)?.id ?? null,
  );
  const selectedBus = vehicles.find((bus) => bus.id === vehicleId);
  const [routeId, setRouteId] = useState<number | null>(selectedBus?.route_id ?? routes[0]?.id ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const selectedRoute = routes.find((r) => r.id === routeId);
  const offline = session.snapshot.offline;

  // Opened without signal: keep asking until the server answers, then go to the shift if there is one.
  useEffect(() => {
    if (!offline) return undefined;
    const id = setInterval(() => {
      session
        .refreshMe()
        .then(() => {
          if (session.snapshot.shift) router.replace('/shift');
        })
        .catch(() => undefined);
    }, 10_000);
    return () => clearInterval(id);
  }, [offline, session]);

  async function executeStart() {
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

  function handleStartShift() {
    if (!vehicleId || !routeId) return;
    Alert.alert(
      t('confirmStartShift'),
      `${t('bus')}: ${selectedBus?.name ?? vehicleId}${selectedBus?.plate ? ` (${selectedBus.plate})` : ''}\n${t('route')}: ${selectedRoute ? `${selectedRoute.code} · ${selectedRoute.name}` : routeId}\n\n${t('confirmStartBody')}`,
      [
        { text: t('cancel'), style: 'cancel' },
        {
          text: t('startShift'),
          onPress: executeStart,
        },
      ],
    );
  }

  function handleSignOut() {
    Alert.alert(t('confirmSignOut'), t('confirmSignOutBody'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('signOut'),
        style: 'destructive',
        onPress: async () => {
          await session.logout();
          router.replace('/');
        },
      },
    ]);
  }

  const driverInitial = (driver?.name || 'C').charAt(0).toUpperCase();

  return (
    <ScrollView contentContainerStyle={styles.page}>
      {/* Driver Header Card */}
      <View style={styles.headerCard}>
        <View style={styles.driverInfo}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{driverInitial}</Text>
          </View>
          <View style={styles.driverMeta}>
            <Text style={styles.driverName}>{driver?.name ?? t('driverLabel')}</Text>
            <View style={styles.badgeRow}>
              <View style={styles.driverBadge}>
                <Text style={styles.driverBadgeText}>{t('driverLabel')}</Text>
              </View>
              {driver?.id ? <Text style={styles.driverLogin}>ID: #{driver.id}</Text> : null}
            </View>
          </View>
        </View>
        <Button
          label={t('signOut')}
          variant="outline"
          onPress={handleSignOut}
          style={styles.signOutBtn}
        />
      </View>

      {offline ? (
        <View style={styles.offlineBanner} accessibilityLiveRegion="polite">
          <Text style={styles.offlineText}>{t('offlineRetry')}</Text>
        </View>
      ) : null}

      {/* Choose Bus Section */}
      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{t('availableBuses')}</Text>
          <Text style={styles.sectionSubtitle}>
            {selectedBus ? `${selectedBus.name}${selectedBus.plate ? ` (${selectedBus.plate})` : ''}` : ''}
          </Text>
        </View>
        <View style={styles.grid}>
          {vehicles.map((bus) => {
            const isSelected = vehicleId === bus.id;
            const isAvailable = bus.available;
            return (
              <Pressable
                key={bus.id}
                disabled={!isAvailable}
                onPress={() => {
                  setVehicleId(bus.id);
                  if (bus.route_id) setRouteId(bus.route_id);
                }}
                style={[
                  styles.optionCard,
                  isSelected && styles.optionCardSelected,
                  !isAvailable && styles.optionCardDisabled,
                ]}
              >
                <View style={styles.optionHeader}>
                  <Text style={[styles.optionTitle, isSelected && styles.optionTitleSelected]}>
                    🚌 {bus.name}
                  </Text>
                  {isSelected ? (
                    <View style={styles.checkBadge}>
                      <Text style={styles.checkText}>✓</Text>
                    </View>
                  ) : null}
                </View>
                <View style={styles.optionFooter}>
                  {bus.plate ? (
                    <View style={styles.plateBadge}>
                      <Text style={styles.plateText}>{bus.plate}</Text>
                    </View>
                  ) : null}
                  {!isAvailable ? (
                    <View style={styles.takenBadge}>
                      <Text style={styles.takenText}>{t('taken')}</Text>
                    </View>
                  ) : null}
                </View>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* Choose Route Section */}
      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{t('availableRoutes')}</Text>
          <Text style={styles.sectionSubtitle}>
            {selectedRoute ? `${selectedRoute.code} · ${selectedRoute.name}` : ''}
          </Text>
        </View>
        <View style={styles.grid}>
          {routes.map((route) => {
            const isSelected = routeId === route.id;
            return (
              <Pressable
                key={route.id}
                onPress={() => setRouteId(route.id)}
                style={[styles.optionCard, isSelected && styles.optionCardSelected]}
              >
                <View style={styles.optionHeader}>
                  <View style={[styles.routeCodeBadge, isSelected && styles.routeCodeBadgeSelected]}>
                    <Text style={[styles.routeCodeText, isSelected && styles.routeCodeTextSelected]}>
                      {route.code}
                    </Text>
                  </View>
                  {isSelected ? (
                    <View style={styles.checkBadge}>
                      <Text style={styles.checkText}>✓</Text>
                    </View>
                  ) : null}
                </View>
                <Text style={[styles.routeName, isSelected && styles.routeNameSelected]} numberOfLines={2}>
                  {route.name}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* Error display */}
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* Bottom Start Shift Button */}
      <View style={styles.actionContainer}>
        <Button
          label={busy ? t('loading') : t('startShift')}
          onPress={handleStartShift}
          disabled={busy || !vehicleId || !routeId}
          style={styles.startBtn}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  offlineBanner: {
    backgroundColor: '#FFF4CC',
    borderColor: '#8A6A00',
    borderWidth: 2,
    borderRadius: 12,
    padding: 16,
  },
  offlineText: {
    color: '#3D2E00',
    fontSize: 20,
    fontWeight: '700',
  },
  page: {
    padding: 24,
    gap: 20,
    backgroundColor: colors.paper,
    flexGrow: 1,
  },
  headerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.card,
    borderRadius: 14,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.line,
  },
  driverInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    flex: 1,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.routeLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.route,
  },
  avatarText: {
    fontSize: 22,
    fontWeight: '800',
    color: colors.route,
  },
  driverMeta: {
    gap: 4,
  },
  driverName: {
    fontSize: type.title - 4,
    fontWeight: '800',
    color: colors.ink,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  driverBadge: {
    backgroundColor: colors.routeLight,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  driverBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.route,
  },
  driverLogin: {
    fontSize: 13,
    color: colors.muted,
  },
  signOutBtn: {
    minHeight: hit - 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  sectionCard: {
    backgroundColor: colors.card,
    borderRadius: 14,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 14,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  sectionTitle: {
    fontSize: type.title - 6,
    fontWeight: '800',
    color: colors.ink,
  },
  sectionSubtitle: {
    fontSize: type.body - 3,
    color: colors.muted,
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  optionCard: {
    minWidth: 180,
    flex: 1,
    backgroundColor: '#FAFAFA',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.line,
    padding: 16,
    gap: 10,
    minHeight: 90,
  },
  optionCardSelected: {
    borderColor: colors.route,
    backgroundColor: colors.routeLight,
  },
  optionCardDisabled: {
    opacity: 0.45,
    backgroundColor: '#F1F5F9',
  },
  optionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  optionTitle: {
    fontSize: type.body,
    fontWeight: '700',
    color: colors.ink,
  },
  optionTitleSelected: {
    color: colors.route,
  },
  optionFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  plateBadge: {
    backgroundColor: '#E2E8F0',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  plateText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.ink,
    letterSpacing: 0.5,
  },
  takenBadge: {
    backgroundColor: colors.busLight,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  takenText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.bus,
  },
  checkBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.route,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkText: {
    color: '#FFF',
    fontWeight: '800',
    fontSize: 14,
  },
  routeCodeBadge: {
    backgroundColor: '#E2E8F0',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  routeCodeBadgeSelected: {
    backgroundColor: colors.route,
  },
  routeCodeText: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.ink,
  },
  routeCodeTextSelected: {
    color: '#FFF',
  },
  routeName: {
    fontSize: type.body - 1,
    color: colors.ink,
    fontWeight: '600',
  },
  routeNameSelected: {
    color: colors.route,
    fontWeight: '700',
  },
  errorBox: {
    backgroundColor: colors.busLight,
    borderColor: colors.bus,
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
  },
  errorText: {
    color: colors.bus,
    fontSize: type.body - 2,
    fontWeight: '600',
  },
  actionContainer: {
    paddingVertical: 8,
  },
  startBtn: {
    minHeight: 56,
  },
});
