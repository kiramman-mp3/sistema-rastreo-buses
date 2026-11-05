import { useCallback, useMemo, useState } from 'react';
import { Animated, AppState, ScrollView, StyleSheet, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { ApiError, NetworkError } from '../src/api/client';
import { calculateDistanceMeters, useCockpitTelemetry } from '../src/gps/useCockpitTelemetry';
import { useGpsHealth } from '../src/gps/useGpsHealth';
import { alertLabel, t, tf, tp, type Message } from '../src/i18n';
import { formatDistance } from '../src/i18n/format';
import { useLang } from '../src/i18n/LangProvider';
import { RouteMapView } from '../src/map/RouteMapView';
import { useDismissed } from '../src/shift/useDismissed';
import { createMotionLock } from '../src/shift/motion';
import { buildNotices } from '../src/shift/notices';
import { classifyStops, sosPhase, type SosLocal } from '../src/shift/progress';
import { useSession, useSessionActions } from '../src/state/SessionContext';
import { Action, GpsBadge, Press, Screen, SosButton, Txt } from '../src/ui/cabin';
import { showDialog } from '../src/ui/dialog';
import { hapticCommit } from '../src/ui/haptics';
import { readableOn } from '../src/ui/contrast';
import { noticeCapacity, useLayout } from '../src/ui/layout';
import { NoticeList } from '../src/ui/Notice';
import { StopStrip } from '../src/ui/StopStrip';
import { useTheme } from '../src/ui/ThemeProvider';
import { useStopCue } from '../src/ui/useStopCue';
import { border, shape, space } from '../src/ui/theme';

const GPS_LABEL: Record<string, Message> = {
  sending: 'gpsSending',
  waiting: 'gpsWaiting',
  off: 'gpsOff',
};

/** What the GPS badge says; with points waiting to be sent it counts them in the right plural. */
function gpsLabel(health: string, queued: number): string {
  return health === 'saving' ? tp('gpsSaving', queued) : tf(GPS_LABEL[health], { n: queued });
}

function localTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const when = new Date(iso);
  return Number.isNaN(when.getTime()) ? '' : `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`;
}

function distance(meters: number | null): string | null {
  return meters === null ? null : formatDistance(meters);
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
  // What the driver closed on this shift: an alert read once should not stay in the way.
  const { dismissed, dismiss } = useDismissed(shift?.id);

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
  const stopCue = useStopCue(nextStop?.id ?? null);

  const busFix = useMemo(
    () => (gps.lat !== null && gps.lon !== null ? { lat: gps.lat, lon: gps.lon } : null),
    [gps.lat, gps.lon],
  );
  const { currentTime } = useCockpitTelemetry(busFix, null);
  const nextCoords = routeMap?.stops.find((s) => s.id === nextStop?.id);
  const meters = busFix && nextCoords ? calculateDistanceMeters(busFix.lat, busFix.lon, nextCoords.lat, nextCoords.lon) : null;

  // The planned time of the next stop and how late or early the bus is, when it has a scheduled trip.
  const dueText = nextStop?.plannedAt ? tf('cabinDue', { time: localTime(nextStop.plannedAt) }) : '';
  const lastDelay = [...stops].reverse().find((s) => s.status === 'arrived' && s.delayMin !== null)?.delayMin ?? null;
  const delayText =
    lastDelay === null ? '' : lastDelay > 0.5 ? tf('cabinLate', { n: Math.round(lastDelay) }) : t('cabinOnTime');
  const planText = [dueText, delayText].filter(Boolean).join(' · ');

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

  const notices = buildNotices({
    sos: sosStatus
      ? {
          text: sosStatus,
          seen: Boolean(serverSos?.seen_at),
          id: String(serverSos?.id ?? sosLocal?.at ?? 'local'),
          // only an SOS the office has can be closed; one still sending or saved must stay in sight
          delivered: phase === 'seen' || phase === 'sent',
        }
      : null,
    alerts: (shiftState?.alerts ?? [])
      .filter((a) => a.state === 'open')
      .map((a) => ({ id: a.id, title: alertLabel(a.kind), detail: a.detail })),
    dismissed,
  });

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
      tick().catch(() => undefined);
      const id = setInterval(() => {
        tick().catch(() => undefined);
      }, 12_000);
      return () => {
        live = false;
        clearInterval(id);
        // on the web (previews) the lock may never have been granted, and it throws
        deactivateKeepAwake().catch(() => undefined);
      };
    }, [actions]),
  );

  function confirmEnd() {
    showDialog(t('confirmEnd'), t('confirmEndBody'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('endShift'),
        style: 'destructive',
        onPress: () => {
          hapticCommit().catch(() => undefined);
          session
            .endShift()
            .then((result) => {
              if (result === 'queued') showDialog(t('endQueued'));
              router.replace('/select');
            })
            .catch(() => showDialog(t('serverError')));
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
      showDialog(t('serverError'));
    }
  }

  const color = route?.color || palette.line;
  const health = stale && gps.health === 'sending' ? 'saving' : gps.health;

  // Landscape puts the next stop beside the map; portrait stacks them (the map takes what is left).
  // With the system font at 130 % or more nothing fits one view: the whole page scrolls (header, notices,
  // next stop, a map of fixed height, then the buttons), stacked in either orientation.
  const pageScroll = layout.largeText;
  const side = layout.landscape && !pageScroll;
  // Three buttons in a row need about 520 dp: a narrower phone puts the SOS on its own row (one line, title and
  // hint together) and the other two below it. Either way they stay low and leave the map its room.
  const stackedActions = layout.compact && layout.width < 520;
  // A phone on its side has little height: smaller marks and one line per stop name, but every stop still shows.
  const compactStrip = (layout.short || layout.height < 700) && !pageScroll;
  const showStrip = true;
  // Notices on a phone are one tight line with their Close button, so the next stop and the map keep their room.
  const compactNotices = layout.compact && !pageScroll;
  // The SOS answer and the alerts never scroll away: they sit above what scrolls. A phone on its side
  // has room for one, and a shorter detail; the rest is counted.
  const noticeBlock = (
    <NoticeList
      items={notices}
      max={noticeCapacity(layout)}
      detailLines={layout.short && !pageScroll ? 1 : 2}
      compact={compactNotices}
      onDismiss={dismiss}
    />
  );

  const problem = (
    <Action
      label={t('actionProblem')}
      sub={layout.compact ? undefined : t('actionProblemSub')}
      onPress={() => router.push('/incident')}
      disabled={locked}
      style={stackedActions ? undefined : layout.compact ? styles.actionProblemPhone : styles.actionWide}
    />
  );
  const sos = (
    <SosButton
      onFire={fireSos}
      title={t('actionSos')}
      hint={t('actionSosSub')}
      holding={t('sosHolding')}
      inline={layout.short || stackedActions}
    />
  );
  const end = (
    <Action
      label={t('endShift')}
      onPress={confirmEnd}
      kind="quiet"
      disabled={locked}
      style={stackedActions ? undefined : layout.compact ? styles.actionPhone : styles.actionNarrow}
    />
  );

  const nextContent = (
    <>
      {/* A phone has no height for a line of its own for each fact: the label, the distance and the count share one. */}
      <Txt size="small" dim lines={1}>
        {layout.compact && nextStop
          ? [
              t('cabinNext'),
              distance(meters),
              left > 1 ? tf('cabinStopsLeft', { n: left }) : t('cabinLastStop'),
              // on a screen with little height the schedule shares the line, it does not take a new one
              layout.short ? planText : '',
            ]
              .filter(Boolean)
              .join(' · ')
          : t('cabinNext')}
      </Txt>
      <Animated.View style={stopCue}>
        <Txt bold size={layout.short ? (layout.height < 400 ? 'data' : 'title') : 'stop'} lines={layout.short ? 1 : 2} fit>
          {nextStop ? nextStop.name : t('noNextStop')}
        </Txt>
      </Animated.View>
      {planText && !layout.short ? (
        <Txt size="small" bold>
          {planText}
        </Txt>
      ) : null}
      {nextStop && !layout.compact ? (
        <Txt size="body" dim>
          {[distance(meters), left > 1 ? tf('cabinStopsLeft', { n: left }) : t('cabinLastStop')]
            .filter(Boolean)
            .join(' · ')}
        </Txt>
      ) : null}
      {afterStop && !(layout.compact && showStrip) ? (
        <Txt size="body">
          {t('cabinAfter')}: {afterStop.name}
        </Txt>
      ) : null}

      {showStrip ? (
        <View style={compactStrip ? styles.stripTight : styles.strip}>
          <StopStrip stops={stops} color={color} ahead={layout.largeText ? 1 : 3} compact={compactStrip} />
        </View>
      ) : null}
    </>
  );
  const nextBlock = pageScroll ? (
    <View style={styles.leftContent}>{nextContent}</View>
  ) : (
    <ScrollView
      style={side ? styles.leftScroll : [styles.top, { maxHeight: Math.round(layout.height * 0.44) }]}
      contentContainerStyle={styles.leftContent}
      showsVerticalScrollIndicator={false}
    >
      {nextContent}
    </ScrollView>
  );

  const modeButton = (
    <Press
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
    </Press>
  );
  // On a phone in portrait the header has two rows: bus and day/night on top, GPS and time below.
  const tallHeader = layout.phone && !layout.landscape;

  return (
    <Screen scroll={pageScroll}>
      {/* Header: bus and line, real GPS state, time, day or night */}
      <View style={[styles.header, layout.compact && styles.headerPhone, { backgroundColor: palette.panel }]}>
        <View style={[styles.identity, tallHeader && styles.identityTall, layout.short && styles.identityShort]}>
          <View style={[styles.chip, { backgroundColor: color }]}>
            <Txt bold size="body" color={readableOn(color)}>
              {route?.code ?? ''}
            </Txt>
          </View>
          <View style={styles.identityText}>
            <Txt bold size="body" lines={1}>
              {bus?.name ?? ''}
            </Txt>
            {/* On a phone on its side the line code already says which line it is: one row for the whole header. */}
            {layout.short && layout.width < 760 ? null : (
              <Txt size="small" dim lines={1}>
                {route?.name ?? ''}
              </Txt>
            )}
          </View>
        </View>
        {tallHeader ? modeButton : null}
        <View style={[styles.headerRight, tallHeader && styles.headerRightFull, { columnGap: layout.compact ? 8 : 24 }]}>
          <Press
            onPress={() => router.push('/gps')}
            disabled={locked}
            accessibilityRole="button"
            accessibilityHint={t('gpsOpen')}
            style={styles.gpsTap}
          >
            <GpsBadge health={health} label={gpsLabel(health, gps.queued)} />
          </Press>
          <Txt bold size="data">
            {currentTime}
          </Txt>
          {tallHeader ? null : modeButton}
        </View>
      </View>

      {side ? null : noticeBlock}

      <View
        style={[pageScroll ? null : styles.body, side ? styles.bodySide : styles.bodyStack, { gap: layout.gap + 4 }]}
      >
        {/* Where the bus goes next. Beside the map the notices are pinned above it; the rest scrolls. */}
        {side ? (
          <View style={[styles.left, layout.short && styles.leftShort]}>
            {noticeBlock}
            {nextBlock}
          </View>
        ) : (
          nextBlock
        )}

        {/* The map */}
        <View
          style={[
            styles.map,
            pageScroll ? styles.mapFixed : side ? (layout.short ? styles.mapSideShort : styles.mapSide) : styles.mapStack,
            // The stop strip comes before the map: on a screen with little height the map gives way first.
            !pageScroll && !side && layout.height < 700 && styles.mapStackLow,
            { backgroundColor: palette.panel },
          ]}
        >
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
          <View style={layout.compact ? styles.sosPhone : styles.actionWide}>{sos}</View>
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
    paddingHorizontal: space[4],
    paddingVertical: space[3],
    columnGap: space[4],
    rowGap: space[2],
    ...shape.control,
  },
  // On a phone every pixel counts: tighter sides so the GPS state and the clock fit one row of a 360 dp screen.
  headerPhone: {
    paddingHorizontal: space[3],
    paddingVertical: space[2],
  },
  identity: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[3],
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 220,
  },
  identityTall: {
    flexBasis: 140,
  },
  // A phone on its side: the bus takes only what it needs, so the GPS state, the clock and the button stay on its row.
  identityShort: {
    flexBasis: 100,
  },
  identityText: {
    flexShrink: 1,
  },
  chip: {
    minWidth: 52,
    minHeight: 44,
    paddingHorizontal: space[3],
    ...shape.control,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerRight: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 1,
    rowGap: space[1],
  },
  headerRightFull: {
    flexBasis: '100%',
    flexWrap: 'nowrap',
  },
  gpsTap: {
    minHeight: 48,
    justifyContent: 'center',
    flexShrink: 1,
  },
  mode: {
    minHeight: 48,
    paddingHorizontal: space[4],
    ...shape.control,
    borderWidth: border.thin,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[2],
  },
  modeDot: {
    width: 10,
    height: 10,
    borderRadius: border.round,
  },
  body: {
    flex: 1,
    minHeight: 0,
  },
  bodySide: {
    flexDirection: 'row',
  },
  bodyStack: {
    flexDirection: 'column',
  },
  left: {
    flexGrow: 4,
    flexShrink: 1,
    flexBasis: 0,
    gap: space[2],
  },
  leftShort: {
    flexGrow: 5,
    gap: space[1],
  },
  leftScroll: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 0,
  },
  top: {
    // Content height, but it gives way (and scrolls) before the map is squeezed out.
    flexGrow: 0,
    flexShrink: 1,
    flexBasis: 'auto',
  },
  leftContent: {
    gap: space[2],
  },
  strip: {
    marginTop: space[3],
    marginBottom: space[2],
  },
  // Little height: the strip sits right under the name, with no air below.
  stripTight: {
    marginTop: space[1],
  },
  map: {
    ...shape.control,
    overflow: 'hidden',
  },
  mapSide: {
    flex: 6,
  },
  mapSideShort: {
    flex: 5,
  },
  mapFixed: {
    height: 260,
  },
  mapStackLow: {
    minHeight: 64,
  },
  mapStack: {
    flexGrow: 1,
    flexShrink: 0,
    flexBasis: 0,
    minHeight: 96,
  },
  lockNote: {
    paddingHorizontal: space[4],
    paddingVertical: space[3],
    ...shape.control,
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
  // On a phone the three buttons share the row: the SOS a little wider, all of them at least 56 high.
  actionPhone: {
    flex: 1,
  },
  // "Avisar un problema" is the longest label: a little more room keeps it on one line, so the row stays low.
  actionProblemPhone: {
    flex: 1.2,
  },
  sosPhone: {
    flex: 1.3,
  },
});
