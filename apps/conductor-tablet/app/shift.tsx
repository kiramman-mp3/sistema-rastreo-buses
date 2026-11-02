import { useCallback, useMemo, useState } from 'react';
import { Alert, AppState, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { ApiError, NetworkError } from '../src/api/client';
import { calculateDistanceMeters, useCockpitTelemetry } from '../src/gps/useCockpitTelemetry';
import { useGpsHealth } from '../src/gps/useGpsHealth';
import { alertLabel, t, tf, type Message } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { RouteMapView } from '../src/map/RouteMapView';
import { createMotionLock } from '../src/shift/motion';
import { classifyStops, sosPhase, type SosLocal } from '../src/shift/progress';
import { useSession, useSessionActions } from '../src/state/SessionContext';
import { Action, GpsBadge, Screen, SosButton, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { StopStrip } from '../src/ui/StopStrip';
import { useTheme } from '../src/ui/ThemeProvider';

const GPS_LABEL: Record<string, Message> = {
  sending: 'gpsSending',
  saving: 'gpsSaving',
  waiting: 'gpsWaiting',
  off: 'gpsOff',
};

function localTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const when = new Date(iso);
  return isNaN(when.getTime()) ? '' : `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`;
}

function distance(meters: number | null): string | null {
  if (meters === null) return null;
  return meters < 1000 ? `${meters} m` : `${(meters / 1000).toFixed(1)} km`;
}

export default function ShiftScreen() {
  useLang();
  const { palette, choice, setChoice } = useTheme();
  const layout = useLayout();
  const session = useSession();
  const actions = useSessionActions();
  const { shift, vehicles, routes, shiftState, routeMap } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);
  const gps = useGpsHealth();
  const [stale, setStale] = useState(false);
  const [sosLocal, setSosLocal] = useState<SosLocal>(null);

  // A small state machine kept across renders; it only reads the last GPS sample.
  const [lock] = useState(() => createMotionLock());
  const locked = useMemo(() => lock(gps.speedKmh, gps.sampleAt, gps.readAt), [lock, gps.speedKmh, gps.sampleAt, gps.readAt]);

  const stops = useMemo(
    () => classifyStops(shiftState?.stops ?? [], shiftState?.next_stop_id ?? null, shiftState?.direction),
    [shiftState?.stops, shiftState?.next_stop_id, shiftState?.direction],
  );
  const nextIndex = stops.findIndex((s) => s.status === 'next');
  const nextStop = nextIndex >= 0 ? stops[nextIndex] : null;
  const afterStop = nextIndex >= 0 ? stops[nextIndex + 1] ?? null : null;
  const left = nextIndex >= 0 ? stops.length - nextIndex : 0;

  const busFix = useMemo(
    () => (gps.lat !== null && gps.lon !== null ? { lat: gps.lat, lon: gps.lon } : null),
    [gps.lat, gps.lon],
  );
  const { currentTime } = useCockpitTelemetry(busFix, null);
  const nextCoords = routeMap?.stops.find((s) => s.id === nextStop?.id);
  const meters = busFix && nextCoords ? calculateDistanceMeters(busFix.lat, busFix.lon, nextCoords.lat, nextCoords.lon) : null;

  const alert = (shiftState?.alerts ?? []).find((a) => a.state === 'open') ?? null;

  const serverSos = shiftState?.sos ?? null;
  const phase = sosPhase(serverSos, sosLocal);
  let sosStatus: string | null = null;
  if (phase === 'seen') {
    sosStatus = tf('sosSeen', { by: serverSos?.seen_by ?? '', time: localTime(serverSos?.seen_at) });
  } else if (phase === 'sending') {
    sosStatus = t('sosSending');
  } else if (phase === 'queued') {
    sosStatus = t('sosQueued');
  } else if (phase === 'sent') {
    sosStatus = t('sosSent');
  }

  useFocusEffect(
    useCallback(() => {
      let live = true;
      activateKeepAwakeAsync().catch(() => undefined);
      async function tick() {
        if (!live || AppState.currentState !== 'active') return;
        try {
          await actions.pullState();
          if (!actions.snapshot.routeMap) await actions.loadRouteMap();
          if (live) setStale(false);
        } catch (error) {
          if (error instanceof ApiError && error.code === 'no_shift') {
            // The session already stopped the GPS.
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
        // on the web (previews) the lock may never have been granted, and it throws
        try {
          deactivateKeepAwake().catch(() => undefined);
        } catch {
          // nothing to release
        }
      };
    }, [actions]),
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
            .then((result) => {
              if (result === 'queued') Alert.alert(t('endQueued'));
              router.replace('/select');
            })
            .catch(() => Alert.alert(t('serverError')));
        },
      },
    ]);
  }

  async function fireSos() {
    const at = new Date().toISOString();
    setSosLocal({ status: 'sending', at });
    try {
      const result = await session.reportIncident({ kind: 'sos', note: '', lat: gps.lat, lon: gps.lon, reported_at: at });
      setSosLocal({ status: result === 'queued' ? 'queued' : 'sent', at });
      session.pullState().catch(() => undefined);
    } catch {
      // The server refused it (for example the shift was closed): say so, never "saved".
      setSosLocal(null);
      Alert.alert(t('serverError'));
    }
  }

  const color = route?.color || palette.line;
  const health = stale && gps.health === 'sending' ? 'saving' : gps.health;

  // Landscape puts the next stop beside the map; portrait stacks them (the map takes what is left).
  const side = layout.landscape;
  // A phone in portrait has no width for three buttons in a row: SOS on top, the other two below.
  const stackedActions = layout.phone && !layout.landscape;
  // A phone on its side has no height to spare: the map already shows the stops, so drop the strip.
  const showStrip = !layout.short;

  const problem = (
    <Action
      label={t('actionProblem')}
      sub={t('actionProblemSub')}
      onPress={() => router.push('/incident')}
      disabled={locked}
      style={stackedActions ? undefined : styles.actionWide}
    />
  );
  const sos = <SosButton onFire={fireSos} title={t('actionSos')} hint={t('actionSosSub')} holding={t('sosHolding')} />;
  const end = (
    <Action
      label={t('endShift')}
      onPress={confirmEnd}
      kind="quiet"
      disabled={locked}
      style={stackedActions ? undefined : styles.actionNarrow}
    />
  );

  return (
    <Screen>
      {/* Header: bus and line, real GPS state, time, day or night */}
      <View style={[styles.header, { backgroundColor: palette.panel }]}>
        <View style={styles.identity}>
          <View style={[styles.chip, { backgroundColor: color }]}>
            <Txt bold size="body" color="#FFFFFF">
              {route?.code ?? ''}
            </Txt>
          </View>
          <View style={styles.identityText}>
            <Txt bold size="body" lines={1}>
              {bus?.name ?? ''}
            </Txt>
            <Txt size="small" dim lines={1}>
              {route?.name ?? ''}
            </Txt>
          </View>
        </View>
        <View style={[styles.headerRight, { gap: layout.phone ? 12 : 24 }]}>
          <Pressable
            onPress={() => router.push('/gps')}
            disabled={locked}
            accessibilityRole="button"
            accessibilityHint={t('gpsOpen')}
            style={styles.gpsTap}
          >
            <GpsBadge health={health} label={tf(GPS_LABEL[health], { n: gps.queued })} />
          </Pressable>
          <Txt bold size="data">
            {currentTime}
          </Txt>
          <Pressable
            onPress={() => setChoice(palette.mode === 'day' ? 'night' : 'day')}
            onLongPress={() => setChoice('auto')}
            accessibilityRole="button"
            accessibilityLabel={palette.mode === 'day' ? t('modeNight') : t('modeDay')}
            style={[styles.mode, { borderColor: palette.ink2 }]}
          >
            <Txt bold size="small">
              {palette.mode === 'day' ? t('modeNight') : t('modeDay')}
            </Txt>
            {choice === 'auto' ? null : <View style={[styles.modeDot, { backgroundColor: palette.signal }]} />}
          </Pressable>
        </View>
      </View>

      <View style={[styles.body, side ? styles.bodySide : styles.bodyStack, { gap: layout.gap + 4 }]}>
        {/* Where the bus goes next; it scrolls if a notice makes it taller than its room */}
        <ScrollView
          style={side ? styles.left : [styles.top, { maxHeight: Math.round(layout.height * 0.4) }]}
          contentContainerStyle={styles.leftContent}
          showsVerticalScrollIndicator={false}
        >
          <Txt size="small" dim>
            {t('cabinNext')}
          </Txt>
          <Txt bold size="stop" lines={2} fit>
            {nextStop ? nextStop.name : t('noNextStop')}
          </Txt>
          {nextStop ? (
            <Txt size="body" dim>
              {[distance(meters), left > 1 ? tf('cabinStopsLeft', { n: left }) : t('cabinLastStop')]
                .filter(Boolean)
                .join(' · ')}
            </Txt>
          ) : null}
          {afterStop ? (
            <Txt size="body">
              {t('cabinAfter')}: {afterStop.name}
            </Txt>
          ) : null}

          {showStrip ? (
            <View style={styles.strip}>
              <StopStrip stops={stops} color={color} />
            </View>
          ) : null}

          {alert ? (
            <View style={[styles.notice, { borderColor: palette.danger }]} accessibilityLiveRegion="polite">
              <Txt bold size="body" color={palette.danger}>
                {alertLabel(alert.kind)}
              </Txt>
              {alert.detail ? <Txt size="small">{alert.detail}</Txt> : null}
            </View>
          ) : null}

          {sosStatus ? (
            <View
              style={[styles.notice, { borderColor: serverSos?.seen_at ? palette.ok : palette.danger }]}
              accessibilityLiveRegion="assertive"
            >
              <Txt bold size="body" color={serverSos?.seen_at ? palette.ok : palette.danger}>
                {sosStatus}
              </Txt>
            </View>
          ) : null}
        </ScrollView>

        {/* The map */}
        <View style={[styles.map, side ? styles.mapSide : styles.mapStack, { backgroundColor: palette.panel }]}>
          <RouteMapView route={routeMap} bus={busFix} nextStopId={nextStop?.id ?? null} />
        </View>
      </View>

      {/* Bottom: three actions; only SOS works while the bus moves */}
      {locked ? (
        <View style={[styles.lockNote, { backgroundColor: palette.signal }]} accessibilityLiveRegion="polite">
          <Txt bold size="body" color={palette.onSignal}>
            {t('lockedMoving')}
          </Txt>
        </View>
      ) : null}
      {stackedActions ? (
        <View style={[styles.actionsStack, { gap: layout.gap }]}>
          {sos}
          <View style={[styles.actionsPair, { gap: layout.gap }]}>
            <View style={styles.pairItem}>{problem}</View>
            <View style={styles.pairItem}>{end}</View>
          </View>
        </View>
      ) : (
        <View style={[styles.actions, { gap: layout.gap }]}>
          {problem}
          <View style={styles.actionWide}>{sos}</View>
          {end}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    columnGap: 16,
    rowGap: 8,
    borderRadius: 8,
  },
  identity: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flexShrink: 1,
  },
  identityText: {
    flexShrink: 1,
  },
  chip: {
    minWidth: 52,
    height: 44,
    paddingHorizontal: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    flexShrink: 1,
  },
  gpsTap: {
    minHeight: 48,
    justifyContent: 'center',
  },
  mode: {
    minHeight: 48,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 2,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  modeDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  body: {
    flex: 1,
  },
  bodySide: {
    flexDirection: 'row',
  },
  bodyStack: {
    flexDirection: 'column',
  },
  left: {
    flex: 4,
  },
  top: {
    flexGrow: 0,
    flexShrink: 0,
  },
  leftContent: {
    gap: 8,
  },
  strip: {
    marginTop: 12,
    marginBottom: 6,
  },
  notice: {
    marginTop: 6,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    borderLeftWidth: 8,
    borderWidth: 2,
    gap: 4,
  },
  map: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  mapSide: {
    flex: 6,
  },
  mapStack: {
    flex: 1,
    minHeight: 160,
  },
  lockNote: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  actions: {
    flexDirection: 'row',
  },
  actionsStack: {
    flexDirection: 'column',
  },
  actionsPair: {
    flexDirection: 'row',
  },
  pairItem: {
    flex: 1,
  },
  actionWide: {
    flex: 3,
  },
  actionNarrow: {
    flex: 2,
  },
});
