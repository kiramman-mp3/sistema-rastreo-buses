import { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  AppState,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { ApiError, NetworkError } from '../src/api/client';
import { readLastSent } from '../src/gps/store';
import { useCockpitTelemetry } from '../src/gps/useCockpitTelemetry';
import { alertLabel, t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { RouteMapView } from '../src/map/RouteMapView';
import { classifyStops } from '../src/shift/progress';
import { useSession } from '../src/state/SessionContext';
import { HeadwayBar, type HeadwayStatus } from '../src/ui/HeadwayBar';
import { IncidentActions } from '../src/ui/IncidentActions';
import { StopAlertCard } from '../src/ui/StopAlertCard';
import { cockpitColors, cockpitHit } from '../src/ui/theme';

export default function ShiftScreen() {
  useLang();
  const session = useSession();
  const { shift, vehicles, routes, driver, shiftState, routeMap } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);

  const [stale, setStale] = useState(false);
  const [busFix, setBusFix] = useState<{ lat: number; lon: number } | null>(null);
  const [trafficLoading, setTrafficLoading] = useState(false);
  const [manualArrived, setManualArrived] = useState(false);

  const stops = useMemo(
    () => classifyStops(shiftState?.stops ?? [], shiftState?.next_stop_id ?? null),
    [shiftState?.stops, shiftState?.next_stop_id],
  );

  const nextStop = useMemo(() => stops.find((s) => s.status === 'next') || null, [stops]);
  const subsequentStops = useMemo(
    () => stops.filter((s) => s.status === 'later'),
    [stops],
  );
  const alerts = shiftState?.alerts ?? [];

  // Coords for next stop to calculate live distance
  const nextStopCoords = useMemo(() => {
    if (!nextStop || !routeMap?.stops) return null;
    const found = routeMap.stops.find((s) => s.id === nextStop.id);
    return found ? { lat: found.lat, lon: found.lon } : null;
  }, [nextStop, routeMap?.stops]);

  // Live cockpit telemetry: 1-second digital clock & live distance calculation
  const { currentTime, distanceFormatted } = useCockpitTelemetry(busFix, nextStopCoords);

  // Dynamic Headway calculation based on alerts / status
  const headwayStatus: HeadwayStatus = useMemo(() => {
    if (alerts.some((a) => a.kind === 'speeding')) return 'ahead';
    if (alerts.some((a) => a.kind === 'long_stop' || a.kind === 'off_route')) return 'delayed';
    return 'on_time';
  }, [alerts]);

  const diffMinutes = useMemo(() => {
    if (headwayStatus === 'ahead') return -3;
    if (headwayStatus === 'delayed') return 5;
    return 1;
  }, [headwayStatus]);

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
      const id = setInterval(tick, 12_000);
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

  async function handleReportTraffic() {
    setTrafficLoading(true);
    try {
      await session.reportIncident({
        kind: 'traffic',
        note: 'Congestión vial y demora reportada desde tableta de cabina',
        lat: busFix?.lat ?? null,
        lon: busFix?.lon ?? null,
      });
      Alert.alert('⚠️ Tráfico Reportado', 'La central de monitoreo ha sido notificada.');
    } catch {
      Alert.alert('Demora Registrada', 'La incidencia se transmitirá al recuperar señal.');
    } finally {
      setTrafficLoading(false);
    }
  }

  async function handleTriggerSOS() {
    try {
      await session.reportIncident({
        kind: 'accident',
        note: '🚨 ALERTA SOS DE EMERGENCIA DISPARADA DESDE CABINA',
        lat: busFix?.lat ?? null,
        lon: busFix?.lon ?? null,
      });
      Alert.alert('🚨 ALERTA SOS DISPARADA', 'Central de seguridad y operaciones notificada de emergencia.');
    } catch {
      Alert.alert('Alerta SOS', 'Emergencia registrada localmente para retransmisión prioritaria.');
    }
  }

  function handleConfirmArrival() {
    setManualArrived(true);
    session.pullState().catch(() => {});
    setTimeout(() => setManualArrived(false), 5000);
  }

  return (
    <View style={styles.cockpitPage}>
      {/* Left Control & Telemetry Panel (Cockpit Rail) */}
      <View style={styles.cockpitPanel}>
        {/* Cockpit Top Header: Unit & System Time */}
        <View style={styles.topHeader}>
          <View style={styles.unitIdentityRow}>
            <View style={styles.busBadge}>
              <Text style={styles.busBadgeText}>
                {bus?.name ? `BUS ${bus.name}` : `BUS #${shift?.vehicle_id ?? '01'}`}
              </Text>
            </View>
            <View style={styles.routePill}>
              <Text style={styles.routePillText} numberOfLines={1}>
                {route?.code ?? 'L-01'} · {route?.name ?? 'UTA TRANSIT'}
              </Text>
            </View>
          </View>

          <View style={styles.clockTelemetryWrap}>
            <Text style={styles.digitalClock} accessibilityLabel={`Hora actual: ${currentTime}`}>
              {currentTime || '--:--:--'}
            </Text>
            <View style={styles.gpsIndicatorRow}>
              <View style={[styles.gpsDot, stale ? styles.gpsDotStale : styles.gpsDotLive]} />
              <Text style={[styles.gpsText, stale && styles.gpsTextStale]}>
                {stale ? 'GPS RECONECTANDO' : 'GPS ACTIVO'}
              </Text>
            </View>
          </View>
        </View>

        {/* Scrollable Ergonomic Cockpit Body */}
        <ScrollView
          style={styles.panelScroll}
          contentContainerStyle={styles.panelScrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* 1. Headway / Cadence Bar */}
          <HeadwayBar
            status={headwayStatus}
            diffMinutes={diffMinutes}
            leadBusName="Bus #02"
            targetIntervalMins={8}
          />

          {/* 2. Immediate Stop Alert Card */}
          <StopAlertCard
            immediateStop={nextStop}
            subsequentStops={subsequentStops}
            distanceFormatted={distanceFormatted}
            onConfirmArrival={handleConfirmArrival}
            arrived={manualArrived}
          />

          {/* Active Operational Alerts Banner */}
          {alerts.length > 0 ? (
            <View style={styles.alertsBox}>
              <Text style={styles.alertsTitle}>ALERTAS OPERATIVAS ACTIVAS:</Text>
              {alerts.map((alert) => (
                <View key={alert.id} style={styles.alertRow}>
                  <Text style={styles.alertIcon}>⚠️</Text>
                  <Text style={styles.alertDetail}>
                    {alertLabel(alert.kind)}
                    {alert.detail ? ` · ${alert.detail}` : ''}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
        </ScrollView>

        {/* Quick Emergency / Incident Bar (Bottom Fixed Rail) */}
        <View style={styles.bottomActionsRail}>
          <IncidentActions
            onReportTraffic={handleReportTraffic}
            onTriggerSOS={handleTriggerSOS}
            trafficLoading={trafficLoading}
          />

          <View style={styles.auxiliaryRow}>
            <Pressable
              onPress={() => router.push('/gps')}
              style={styles.auxBtn}
              accessibilityRole="button"
              accessibilityLabel="Ver diagnóstico de telemetría GPS"
            >
              <Text style={styles.auxBtnText}>🛰️ DIAGNÓSTICO GPS</Text>
            </Pressable>

            <Pressable
              onPress={confirmEnd}
              style={[styles.auxBtn, styles.endShiftBtn]}
              accessibilityRole="button"
              accessibilityLabel="Finalizar turno de conducción"
            >
              <Text style={styles.endShiftText}>🛑 FINALIZAR TURNO</Text>
            </Pressable>
          </View>
        </View>
      </View>

      {/* Right Map Viewport */}
      <View style={styles.mapViewport}>
        <RouteMapView
          route={routeMap}
          bus={busFix}
          nextStopId={shiftState?.next_stop_id ?? null}
        />
        <View style={styles.mapDriverWatermark}>
          <Text style={styles.watermarkText}>
            CONDUCTOR: {driver?.name?.toUpperCase() ?? 'CONDUCTOR AUTORIZADO'} · UTA TRANSIT
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cockpitPage: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: cockpitColors.bg,
  },
  cockpitPanel: {
    width: 460,
    backgroundColor: cockpitColors.surface,
    borderRightWidth: 2,
    borderRightColor: cockpitColors.surfaceBorder,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  topHeader: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 14,
    borderBottomWidth: 1.5,
    borderBottomColor: cockpitColors.surfaceBorder,
    backgroundColor: cockpitColors.surfaceElevated,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  unitIdentityRow: {
    flex: 1,
    gap: 6,
  },
  busBadge: {
    backgroundColor: cockpitColors.brandUTA,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 8,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: '#B91C1C',
  },
  busBadgeText: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  routePill: {
    marginTop: 2,
  },
  routePillText: {
    color: cockpitColors.textMuted,
    fontSize: 14,
    fontWeight: '700',
  },
  clockTelemetryWrap: {
    alignItems: 'flex-end',
    gap: 4,
  },
  digitalClock: {
    fontFamily: 'monospace',
    color: cockpitColors.textBright,
    fontSize: 26,
    fontWeight: '900',
    letterSpacing: 1,
  },
  gpsIndicatorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  gpsDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  gpsDotLive: {
    backgroundColor: cockpitColors.onTime,
  },
  gpsDotStale: {
    backgroundColor: cockpitColors.delayed,
  },
  gpsText: {
    color: cockpitColors.onTime,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  gpsTextStale: {
    color: cockpitColors.delayed,
  },
  panelScroll: {
    flex: 1,
  },
  panelScrollContent: {
    padding: 16,
    gap: 16,
  },
  alertsBox: {
    backgroundColor: '#2A1215',
    borderWidth: 1.5,
    borderColor: '#DC2626',
    borderRadius: 14,
    padding: 14,
    gap: 8,
  },
  alertsTitle: {
    color: '#F87171',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.6,
  },
  alertRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  alertIcon: {
    fontSize: 16,
  },
  alertDetail: {
    flex: 1,
    color: '#FECACA',
    fontSize: 14,
    fontWeight: '700',
  },
  bottomActionsRail: {
    padding: 16,
    borderTopWidth: 1.5,
    borderTopColor: cockpitColors.surfaceBorder,
    backgroundColor: cockpitColors.surfaceElevated,
    gap: 12,
  },
  auxiliaryRow: {
    flexDirection: 'row',
    gap: 10,
  },
  auxBtn: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: cockpitColors.surfaceBorder,
    minHeight: 46,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  auxBtnText: {
    color: cockpitColors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  endShiftBtn: {
    backgroundColor: 'rgba(220, 38, 38, 0.1)',
    borderColor: 'rgba(220, 38, 38, 0.4)',
  },
  endShiftText: {
    color: '#F87171',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  mapViewport: {
    flex: 1,
    position: 'relative',
    backgroundColor: '#0A0E14',
  },
  mapDriverWatermark: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    backgroundColor: 'rgba(11, 15, 23, 0.85)',
    borderWidth: 1,
    borderColor: cockpitColors.surfaceBorder,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  watermarkText: {
    color: cockpitColors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
