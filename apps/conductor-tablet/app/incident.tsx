import { useState } from 'react';
import { router } from 'expo-router';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import type { IncidentKind } from '../src/api/types';
import { readLastSample, readLastSent } from '../src/gps/store';
import { t, type Message } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { fonts } from '../src/ui/theme';
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
    } catch {
      setResult('error');
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
              <Pressable
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
              </Pressable>
            );
          })}
        </View>

        <View style={styles.side}>
          <Txt size="small" dim>
            {t('incidentNote')}
          </Txt>
          <TextInput
            value={note}
            onChangeText={setNote}
            placeholder={t('incidentNoteHint')}
            placeholderTextColor={palette.ink2}
            maxLength={300}
            multiline
            style={[
              styles.input,
              {
                backgroundColor: palette.field,
                color: palette.ink,
                borderColor: palette.ink2,
                fontSize: layout.sizes.body,
                minHeight: layout.short ? 96 : 160,
              },
            ]}
          />
          <Txt size="small" dim>
            {note.length} / 300
          </Txt>

          {result ? (
            <View
              style={[styles.result, { borderColor: result === 'error' ? palette.danger : palette.ok }]}
              accessibilityLiveRegion="polite"
            >
              <Txt bold size="body" color={result === 'error' ? palette.danger : palette.ok}>
                {result === 'sent' ? t('sent') : result === 'queued' ? t('queued') : t('network')}
              </Txt>
            </View>
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
  headText: {
    flexShrink: 1,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  body: {
    flex: 1,
    flexDirection: 'row',
  },
  bodyStack: {
    flexDirection: 'column',
    flex: 0,
  },
  kinds: {
    flex: 1,
  },
  kind: {
    borderRadius: 8,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 18,
  },
  radio: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  side: {
    flex: 1,
    gap: 10,
  },
  input: {
    borderWidth: 2,
    borderRadius: 8,
    padding: 16,
    fontFamily: fonts.text,
    textAlignVertical: 'top',
  },
  result: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderLeftWidth: 8,
  },
  send: {
    marginTop: 'auto',
  },
});
