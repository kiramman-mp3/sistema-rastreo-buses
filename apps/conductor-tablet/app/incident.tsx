import { useState } from 'react';
import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { IncidentKind } from '../src/api/types';
import { readLastSent } from '../src/gps/store';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, hit, type } from '../src/ui/theme';

const KINDS: IncidentKind[] = ['breakdown', 'traffic', 'accident', 'other'];

function kindLabel(kind: IncidentKind) {
  if (kind === 'breakdown') return t('kind_breakdown');
  if (kind === 'traffic') return t('kind_traffic');
  if (kind === 'accident') return t('kind_accident');
  return t('kind_other');
}

export default function IncidentScreen() {
  useLang();
  const session = useSession();
  const [kind, setKind] = useState<IncidentKind>('breakdown');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function submit() {
    setBusy(true);
    setMessage('');
    const last = await readLastSent();
    try {
      const result = await session.reportIncident({
        kind,
        note: note.slice(0, 300),
        lat: last?.lat ?? null,
        lon: last?.lon ?? null,
      });
      setMessage(t(result === 'queued' ? 'queued' : 'sent'));
    } catch {
      setMessage(t('network'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.page}>
      <Text style={styles.title}>{t('incident')}</Text>
      <Text style={styles.body}>{t('field_kind')}</Text>
      <View style={styles.row}>
        {KINDS.map((item) => (
          <Pressable
            key={item}
            onPress={() => setKind(item)}
            style={[styles.chip, kind === item && styles.on]}
          >
            <Text style={styles.chipText}>{kindLabel(item)}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.body}>{t('field_description')}</Text>
      <TextInput
        value={note}
        onChangeText={setNote}
        placeholder={t('note')}
        maxLength={300}
        multiline
        style={styles.input}
      />
      {message ? <Text style={styles.body}>{message}</Text> : null}
      <Button label={t('submit')} onPress={submit} disabled={busy} />
      <Button label={t('onShift')} onPress={() => router.back()} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper, padding: 28, gap: 12, maxWidth: 720, width: '100%', alignSelf: 'center' },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700' },
  body: { fontSize: type.body, color: colors.ink },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    minHeight: hit - 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.line,
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  on: { borderColor: colors.route, backgroundColor: '#E7F2EE' },
  chipText: { fontSize: type.body, color: colors.ink },
  input: {
    minHeight: 88,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 8,
    padding: 12,
    fontSize: type.body,
    backgroundColor: '#fff',
    textAlignVertical: 'top',
  },
});
