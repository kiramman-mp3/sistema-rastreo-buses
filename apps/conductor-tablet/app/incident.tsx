import { useState } from 'react';
import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import type { IncidentKind } from '../src/api/types';
import { readLastSample, readLastSent } from '../src/gps/store';
import { t, type Message } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Field, Press, Screen, Txt } from '../src/ui/cabin';
import { hapticDone, hapticFail } from '../src/ui/haptics';
import { useLayout } from '../src/ui/layout';
import { Notice } from '../src/ui/Notice';
import { border, shape, space } from '../src/ui/theme';
import { useTheme } from '../src/ui/ThemeProvider';

const KINDS: { key: IncidentKind; label: Message }[] = [
  { key: 'traffic', label: 'kind_traffic' },
  { key: 'breakdown', label: 'kind_breakdown' },
  { key: 'accident', label: 'kind_accident' },
  { key: 'other', label: 'kind_other' },
];

export default function IncidentScreen() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const session = useSession();
  const [kind, setKind] = useState<IncidentKind | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<'sent' | 'queued' | 'error' | null>(null);

  async function submit() {
    if (!kind) return;
    setBusy(true);
    setResult(null);
    const where = (await readLastSample()) ?? (await readLastSent());
    try {
      const outcome = await session.reportIncident({
        kind,
        note: note.trim().slice(0, 300),
        lat: where?.lat ?? null,
        lon: where?.lon ?? null,
      });
      setResult(outcome);
      setNote('');
      hapticDone();
    } catch {
      setResult('error');
      hapticFail();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen scroll>
      <View style={styles.head}>
        <View style={styles.headText}>
          <Txt bold size="title">
            {t('actionProblem')}
          </Txt>
        </View>
        <Action label={t('backToShift')} onPress={() => router.back()} kind="quiet" />
      </View>

      <View style={[styles.body, !layout.wide && styles.bodyStack, { gap: layout.gap + 8 }]}>
        <View style={[styles.kinds, { gap: layout.gap }]} accessibilityRole="radiogroup" accessibilityLabel={t('incidentWhat')}>
          <Txt size="small" dim>
            {t('incidentWhat')}
          </Txt>
          {KINDS.map((item) => {
            const on = kind === item.key;
            return (
              <Press
                key={item.key}
                onPress={() => {
                  setKind(item.key);
                  setResult(null);
                }}
                accessibilityRole="radio"
                accessibilityState={{ checked: on }}
                style={[
                  styles.kind,
                  { minHeight: layout.hit + 8, backgroundColor: on ? palette.ink : palette.panel },
                ]}
              >
                <View style={[styles.radio, { borderColor: on ? palette.signal : palette.ink2 }]}>
                  {on ? <View style={[styles.radioDot, { backgroundColor: palette.signal }]} /> : null}
                </View>
                <Txt bold size="data" color={on ? palette.ground : palette.ink}>
                  {t(item.label)}
                </Txt>
              </Press>
            );
          })}
        </View>

        <View style={styles.side}>
          <Txt size="small" dim>
            {t('incidentNote')}
          </Txt>
          <Field
            value={note}
            onChangeText={setNote}
            placeholder={t('incidentNoteHint')}
            maxLength={300}
            multiline
            style={[styles.input, { minHeight: layout.short ? 96 : 160 }]}
          />
          <Txt size="small" dim>
            {note.length} / 300
          </Txt>

          {result ? (
            <Notice
              item={{
                key: 'result',
                tone: result === 'error' ? 'danger' : result === 'queued' ? 'warn' : 'ok',
                title: result === 'sent' ? t('sent') : result === 'queued' ? t('queued') : t('network'),
                live: 'polite',
              }}
            />
          ) : null}

          <Action
            label={busy ? t('loading') : t('incidentSend')}
            onPress={submit}
            kind="accent"
            disabled={busy || !kind}
            style={layout.wide ? styles.send : undefined}
          />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  // The title keeps room to be read: when a big font leaves less than this, the button drops to the next line.
  headText: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 200,
  },
  head: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space[4],
  },
  body: {
    flex: 1,
    flexDirection: 'row',
  },
  bodyStack: {
    flexDirection: 'column',
    flexGrow: 0,
    flexShrink: 0,
    flexBasis: 'auto',
  },
  kinds: {
    flex: 1,
  },
  kind: {
    ...shape.control,
    paddingHorizontal: space[5],
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[4],
  },
  radio: {
    width: 30,
    height: 30,
    borderRadius: border.round,
    borderWidth: border.mark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: {
    width: 14,
    height: 14,
    borderRadius: border.round,
  },
  side: {
    flex: 1,
    gap: space[2],
  },
  input: {
    paddingVertical: space[4],
    textAlignVertical: 'top',
  },
  send: {
    marginTop: 'auto',
  },
});
