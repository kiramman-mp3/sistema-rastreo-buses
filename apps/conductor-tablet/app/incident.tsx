import { useState } from 'react';
import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import type { IncidentKind } from '../src/api/types';
import { readLastSent } from '../src/gps/store';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, hit, type } from '../src/ui/theme';

const KINDS: { key: IncidentKind; icon: string }[] = [
  { key: 'breakdown', icon: '🛠️' },
  { key: 'traffic', icon: '🚦' },
  { key: 'accident', icon: '💥' },
  { key: 'other', icon: '📝' },
];

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
  const [isSuccess, setIsSuccess] = useState(false);

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
      setIsSuccess(true);
      setMessage(t(result === 'queued' ? 'queued' : 'sent'));
      setNote('');
    } catch {
      setIsSuccess(false);
      setMessage(t('network'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.title}>{t('incident')}</Text>
          <Text style={styles.subtitle}>Notifica a la central de monitoreo de la UTA sobre cualquier novedad en la vía.</Text>
        </View>

        <Text style={styles.sectionLabel}>{t('field_kind')}</Text>
        <View style={styles.grid}>
          {KINDS.map((item) => {
            const isSelected = kind === item.key;
            return (
              <Pressable
                key={item.key}
                onPress={() => setKind(item.key)}
                style={[styles.chip, isSelected && styles.chipSelected]}
              >
                <Text style={styles.chipIcon}>{item.icon}</Text>
                <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                  {kindLabel(item.key)}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.textLabelRow}>
          <Text style={styles.sectionLabel}>{t('field_description')}</Text>
          <Text style={styles.charCounter}>{note.length} / 300</Text>
        </View>
        <TextInput
          value={note}
          onChangeText={setNote}
          placeholder="Escribe detalles del suceso (opcional)..."
          placeholderTextColor={colors.muted}
          maxLength={300}
          multiline
          style={styles.input}
        />

        {message ? (
          <View style={[styles.messageBox, isSuccess ? styles.messageSuccess : styles.messageError]}>
            <Text style={[styles.messageText, isSuccess ? styles.messageTextSuccess : styles.messageTextError]}>
              {message}
            </Text>
          </View>
        ) : null}

        <View style={styles.actions}>
          <Button
            label={busy ? t('loading') : t('submit')}
            onPress={submit}
            disabled={busy}
            style={styles.submitBtn}
          />
          <Button
            label={t('backToShift')}
            variant="secondary"
            onPress={() => router.back()}
          />
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    backgroundColor: colors.paper,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    width: '100%',
    maxWidth: 620,
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 28,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  header: {
    gap: 4,
    marginBottom: 4,
  },
  title: {
    fontSize: type.title,
    fontWeight: '800',
    color: colors.ink,
  },
  subtitle: {
    fontSize: 14,
    color: colors.muted,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.ink,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  textLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  charCounter: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  chip: {
    flex: 1,
    minWidth: 120,
    minHeight: hit,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.line,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
    backgroundColor: '#FAFAFA',
  },
  chipSelected: {
    borderColor: colors.route,
    backgroundColor: colors.routeLight,
  },
  chipIcon: {
    fontSize: 18,
  },
  chipText: {
    fontSize: type.body - 2,
    color: colors.ink,
    fontWeight: '600',
  },
  chipTextSelected: {
    color: colors.route,
    fontWeight: '800',
  },
  input: {
    minHeight: 110,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    padding: 14,
    fontSize: type.body - 1,
    backgroundColor: '#F8FAFC',
    color: colors.ink,
    textAlignVertical: 'top',
  },
  messageBox: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  messageSuccess: {
    backgroundColor: colors.routeLight,
    borderColor: colors.route,
  },
  messageError: {
    backgroundColor: colors.busLight,
    borderColor: colors.bus,
  },
  messageText: {
    fontSize: 14,
    fontWeight: '700',
  },
  messageTextSuccess: {
    color: colors.route,
  },
  messageTextError: {
    color: colors.bus,
  },
  actions: {
    gap: 10,
    marginTop: 8,
  },
  submitBtn: {
    minHeight: hit,
  },
});
