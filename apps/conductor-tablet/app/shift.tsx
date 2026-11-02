import { useCallback, useMemo, useState } from 'react';
import { Alert, AppState, Pressable, StyleSheet, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { ApiError, NetworkError } from '../src/api/client';
import { calculateDistanceMeters, useCockpitTelemetry } from '../src/gps/useCockpitTelemetry';
import { useGpsHealth } from '../src/gps/useGpsHealth';
import { alertLabel, t, tf, type Message } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { RouteMapView } from '../src/map/RouteMapView';
import { createMotionLock } from '../src/shift/motion';
import { classifyStops } from '../src/shift/progress';
import { useSession } from '../src/state/SessionContext';
import { Action, GpsBadge, SosButton, Txt } from '../src/ui/cabin';
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
  const session = useSession();
  const { shift, vehicles, routes, shiftState, routeMap } = session.snapshot;
  const bus = vehicles.find((item) => item.id === shift?.vehicle_id);
  const route = routes.find((item) => item.id === shift?.route_id);
  const gps = useGpsHealth();
  const [stale, setStale] = useState(false);
  const [sosLocal, setSosLocal] = useState<'sending' | 'queued' | 'sent' | null>(null);

  // A small state machine kept across renders; it only reads the last GPS sample.
  const [lock] = useState(() => createMotionLock());
  const locked = useMemo(() => lock(gps.speedKmh, gps.sampleAt, gps.readAt), [lock, gps.speedKmh, gps.sampleAt, gps.readAt]);

  const stops = useMemo(
    () => classifyStops(shiftState?.stops ?? [], shiftState?.next_stop_id ?? null),
    [shiftState?.stops, shiftState?.next_stop_id],
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
  let sosStatus: string | null = null;
  if (serverSos?.seen_at) {
    sosStatus = tf('sosSeen', { by: serverSos.seen_by ?? '', time: localTime(serverSos.seen_at) });
  } else if (sosLocal === 'sending') {
    sosStatus = t('sosSending');
  } else if (sosLocal === 'queued') {
    sosStatus = t('sosQueued');
  } else if (serverSos || sosLocal === 'sent') {
    sosStatus = t('sosSent');
  }

  useFocusEffect(
    useCallback(() => {
      let live = true;
      activateKeepAwakeAsync().catch(() => undefined);
      async function tick() {
        if (!live || AppState.currentState !== 'active') return;
        try {
          await session.pullState();
          if (!session.snapshot.routeMap) await session.loadRouteMap();
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

  async function fireSos() {
    setSosLocal('sending');
    try {
      const result = await session.reportIncident({ kind: 'sos', note: '', lat: gps.lat, lon: gps.lon });
      setSosLocal(result === 'queued' ? 'queued' : 'sent');
      session.pullState().catch(() => undefined);
    } catch {
      setSosLocal('queued');
    }
  }

  const color = route?.color || palette.line;
  const health = stale && gps.health === 'sending' ? 'saving' : gps.health;

  return (
    <View style={[styles.page, { backgroundColor: palette.ground }]}>
      {/* Header: bus and line, real GPS state, time, day or night */}
      <View style={[styles.header, { backgroundColor: palette.panel }]}>
        <View style={styles.identity}>
          <View style={[styles.chip, { backgroundColor: color }]}>
            <Txt bold size="body" color="#FFFFFF">
              {route?.code ?? ''}
            </Txt>
          </View>
          <View style={styles.identityText}>
            <Txt bold size="body">
              {bus?.name ?? ''}
            </Txt>
            <Txt size="small" dim lines={1}>
              {route?.name ?? ''}
            </Txt>
          </View>
        </View>
        <View style={styles.headerRight}>
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

      <View style={styles.body}>
        {/* Left: where the bus goes next */}
        <View style={styles.left}>
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

          <View style={styles.strip}>
            <StopStrip stops={stops} color={color} />
          </View>

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
        </View>

        {/* Right: the map */}
        <View style={[styles.map, { backgroundColor: palette.panel }]}>
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
      <View style={styles.actions}>
        <Action
          label={t('actionProblem')}
          sub={t('actionProblemSub')}
          onPress={() => router.push('/incident')}
          disabled={locked}
          style={styles.actionWide}
        />
        <View style={styles.actionWide}>
          <SosButton onFire={fireSos} title={t('actionSos')} hint={t('actionSosSub')} holding={t('sosHolding')} />
        </View>
        <Action label={t('endShift')} onPress={confirmEnd} kind="quiet" disabled={locked} style={styles.actionNarrow} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingVertical: 12,
    gap: 16,
  },
  identity: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    flexShrink: 1,
  },
  identityText: {
    flexShrink: 1,
  },
  chip: {
    minWidth: 56,
    height: 44,
    paddingHorizontal: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 24,
  },
  gpsTap: {
    minHeight: 48,
    justifyContent: 'center',
  },
  mode: {
    minHeight: 48,
    paddingHorizontal: 16,
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
    flexDirection: 'row',
    gap: 20,
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  left: {
    flex: 4,
    gap: 8,
  },
  strip: {
    marginTop: 18,
    marginBottom: 6,
  },
  notice: {
    marginTop: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    borderLeftWidth: 8,
    borderWidth: 2,
    gap: 4,
  },
  map: {
    flex: 6,
    borderRadius: 8,
    overflow: 'hidden',
  },
  lockNote: {
    marginHorizontal: 24,
    marginTop: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  actions: {
    flexDirection: 'row',
    gap: 16,
    padding: 24,
    paddingTop: 16,
  },
  actionWide: {
    flex: 3,
  },
  actionNarrow: {
    flex: 2,
  },
});
