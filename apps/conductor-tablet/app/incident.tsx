import { useEffect, useRef, useState } from 'react';
import { router } from 'expo-router';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';

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

/** After a report is sent (or saved) the screen waits this long, so the answer is read, then goes back to the shift. */
const BACK_AFTER_MS = 1800;

export default function IncidentScreen() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const session = useSession();
  const [kind, setKind] = useState<IncidentKind | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<'sent' | 'queued' | 'error' | null>(null);
  const back = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (back.current) clearTimeout(back.current);
    },
    [],
  );

  // A report that went out (or is saved to go out) cannot be sent a second time from this screen: a double tap
  // or a nervous second press would have filed the same problem twice.
  const done = result === 'sent' || result === 'queued';

  async function submit() {
    if (!kind || busy || done) return;
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
      back.current = setTimeout(() => router.back(), BACK_AFTER_MS);
    } catch {
      setResult('error');
      hapticFail();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView style={[styles.frame, { gap: layout.gap }]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={[styles.head, layout.largeText && styles.headStack]}>
          <View style={styles.headText}>
            <Txt bold size="title" lines={layout.largeText ? undefined : 2}>
              {t('actionProblem')}
            </Txt>
          </View>
          <Action label={t('backToShift')} onPress={() => router.back()} kind="quiet" />
        </View>

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[styles.body, !layout.wide && styles.bodyStack, { gap: layout.gap + 8 }]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
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
                  disabled={done}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on, disabled: done }}
                  style={[
                    styles.kind,
                    { minHeight: layout.hit + (layout.short ? 0 : 8), backgroundColor: on ? palette.ink : palette.panel },
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
              editable={!done}
              style={[styles.input, { minHeight: layout.short ? 80 : layout.phone ? 112 : 160 }]}
            />
            <Txt size="small" dim>
              {note.length} / 300
            </Txt>
          </View>
        </ScrollView>

        {/* Pinned below the form: on a small screen the send button must never be the thing that scrolled away. */}
        <View style={{ gap: layout.gap }}>
          {result ? (
            <Notice
              item={{
                key: 'result',
                tone: result === 'error' ? 'danger' : result === 'queued' ? 'warn' : 'ok',
                title: result === 'sent' ? t('sent') : result === 'queued' ? t('queued') : t('network'),
                live: 'polite',
              }}
              compact={layout.short}
            />
          ) : !kind ? (
            <Txt size="small" dim>
              {t('incidentPick')}
            </Txt>
          ) : null}
          <Action
            label={busy ? t('loading') : t('incidentSend')}
            onPress={submit}
            kind="accent"
            disabled={busy || !kind || done}
          />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  frame: {
    flex: 1,
  },
  scroll: {
    flex: 1,
  },
  headText: {
    flexShrink: 1,
  },
  // With a large system font the title and its button no longer fit side by side: the button goes below.
  headStack: {
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space[4],
  },
  body: {
    flexDirection: 'row',
    flexGrow: 1,
  },
  bodyStack: {
    flexDirection: 'column',
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
});
