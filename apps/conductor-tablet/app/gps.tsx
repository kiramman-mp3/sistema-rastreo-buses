import { useCallback, useEffect, useState } from 'react';
import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { gpsPermissionSnapshot } from '../src/gps/permissions';
import { locationQueue, readLastError, readLastSent } from '../src/gps/store';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Screen, Txt } from '../src/ui/cabin';
import { useTheme } from '../src/ui/ThemeProvider';
import { shape, space } from '../src/ui/theme';

type Facts = { foreground: boolean; background: boolean; queue: number; last: string; error: string | null };

function stamp(at: number, lat: number, lon: number) {
  return `${new Date(at).toLocaleTimeString()} · ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

async function loadFacts(): Promise<Facts> {
  const [permissions, queue, sent, failed] = await Promise.all([
    gpsPermissionSnapshot(),
    locationQueue.size(),
    readLastSent(),
    readLastError(),
  ]);
  // Only a failure newer than the last good send still explains anything.
  const error =
    failed && (!sent || failed.at > sent.at) ? `${new Date(failed.at).toLocaleTimeString()} · ${failed.error}` : null;
  return {
    foreground: permissions.foreground === 'granted',
    background: permissions.background === 'granted',
    queue,
    last: sent ? stamp(sent.at, sent.lat, sent.lon) : t('gpsNone'),
    error,
  };
}

export default function GpsScreen() {
  useLang();
  const { palette } = useTheme();
  const session = useSession();
  const [facts, setFacts] = useState<Facts | null>(null);

  const refresh = useCallback(() => loadFacts().then(setFacts), []);

  useEffect(() => {
    let live = true;
    loadFacts()
      .then((next) => {
        if (live) setFacts(next);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  const rows: [string, string, boolean | null][] = facts
    ? [
        [t('gpsForeground'), facts.foreground ? t('granted') : t('denied'), facts.foreground],
        [t('gpsBackground'), facts.background ? t('granted') : t('denied'), facts.background],
        [t('gpsQueue'), String(facts.queue), facts.queue === 0],
        [t('gpsLast'), facts.last, null],
        [t('gpsDevice'), session.snapshot.gps?.uniqueId ?? '-', null],
        ...(facts.error ? [[t('gpsLastError'), facts.error, false] as [string, string, boolean]] : []),
      ]
    : [];

  return (
    <Screen scroll>
      <View style={styles.head}>
        <View style={styles.headText}>
          <Txt bold size="title">
            {t('gpsStatus')}
          </Txt>
        </View>
        <View style={styles.headActions}>
          <Action label={t('gpsRefresh')} onPress={() => refresh().catch(() => undefined)} />
          <Action label={t('backToShift')} onPress={() => router.back()} kind="accent" />
        </View>
      </View>
      <View style={styles.rows}>
        {rows.map(([label, value, ok]) => (
          <View key={label} style={[styles.row, { backgroundColor: palette.panel }]}>
            <Txt size="body" dim style={styles.label}>
              {label}
            </Txt>
            <Txt bold size="body" color={ok === null ? palette.ink : ok ? palette.ok : palette.danger} style={styles.value}>
              {value}
            </Txt>
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: space[3] },
  headText: { flexShrink: 1 },
  headActions: { flexDirection: 'row', flexWrap: 'wrap', gap: space[3] },
  label: { flexShrink: 0 },
  value: { flexShrink: 1, textAlign: 'right' },
  rows: { gap: space[2] },
  row: {
    minHeight: 64,
    paddingVertical: space[2],
    ...shape.control,
    paddingHorizontal: space[5],
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space[4],
  },
});
