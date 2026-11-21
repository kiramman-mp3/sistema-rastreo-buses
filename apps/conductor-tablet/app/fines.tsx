import { useCallback, useEffect, useState } from 'react';
import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { NetworkError } from '../src/api/client';
import type { Fine } from '../src/api/types';
import { APPEAL_MAX, appealText, fineStatus, hoursToAppeal, money, sortFines } from '../src/fines/format';
import { getLang, t, tf, type Message } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSessionActions } from '../src/state/SessionContext';
import { Action, Field, Press, Screen, Txt } from '../src/ui/cabin';
import { showDialog } from '../src/ui/dialog';
import { hapticDone, hapticFail } from '../src/ui/haptics';
import { useLayout } from '../src/ui/layout';
import { Notice } from '../src/ui/Notice';
import { shape, space } from '../src/ui/theme';
import { useTheme } from '../src/ui/ThemeProvider';

const LOCALES: Record<string, string> = { es: 'es-EC', en: 'en-US', qu: 'es-EC' };

function when(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(LOCALES[getLang()], { dateStyle: 'medium', timeStyle: 'short' });
}

/**
 * The driver's confirmed fines: why each one was given, what the system checked, and a statement to send once.
 * Only reachable before a shift starts: nothing here may distract a driver who is driving.
 */
export default function FinesScreen() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const actions = useSessionActions();
  const [fines, setFines] = useState<Fine[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [openId, setOpenId] = useState<number | null>(null);

  // Every state change happens when the answer arrives, never while the effect runs.
  const fetchFines = useCallback(
    () =>
      actions
        .loadFines()
        .then((data) => {
          setError('');
          setFines(sortFines(data.fines));
        })
        .catch((err: unknown) => setError(err instanceof NetworkError ? t('network') : t('finesError')))
        .finally(() => setLoaded(true)),
    [actions],
  );

  useEffect(() => {
    fetchFines();
  }, [fetchFines]);

  const load = fetchFines;

  const replace = (fine: Fine) => setFines((list) => sortFines(list.map((f) => (f.id === fine.id ? fine : f))));
  const open = fines.find((fine) => fine.id === openId) ?? null;

  return (
    <Screen scroll onRefresh={load}>
      <View style={[styles.head, layout.largeText && styles.headStack]}>
        <Txt bold size="title">
          {open ? open.type : t('finesTitle')}
        </Txt>
        <Action
          label={t('finesBack')}
          onPress={() => (open ? setOpenId(null) : router.back())}
          kind="quiet"
        />
      </View>

      {error ? <Notice item={{ key: 'error', tone: 'danger', title: error, live: 'polite' }} /> : null}
      {loaded && !error && fines.length === 0 ? (
        <Notice item={{ key: 'empty', tone: 'ok', title: t('finesEmpty'), live: 'polite' }} />
      ) : null}

      {open ? (
        <FineDetail fine={open} onAppealed={replace} />
      ) : (
        <View style={{ gap: layout.gap }}>
          {fines.map((fine) => (
            <Press
              key={fine.id}
              onPress={() => setOpenId(fine.id)}
              accessibilityRole="button"
              accessibilityLabel={`${fine.type}. ${fine.headline}. ${money(fine.amount, fine.currency, LOCALES[getLang()])}`}
              style={[styles.card, { backgroundColor: palette.panel, borderColor: palette.edge, minHeight: layout.hit }]}
            >
              <View style={styles.cardTop}>
                <Txt bold size="data" lines={2}>
                  {fine.type}
                </Txt>
                <Txt bold size="data">
                  {money(fine.amount, fine.currency, LOCALES[getLang()])}
                </Txt>
              </View>
              <Txt size="body">{fine.headline}</Txt>
              <Txt size="small" dim>
                {[fine.number, when(fine.occurred_at), fine.vehicle, fine.route].filter(Boolean).join(' · ')}
              </Txt>
              <StatusLine fine={fine} />
            </Press>
          ))}
        </View>
      )}
    </Screen>
  );
}

function StatusLine({ fine }: { fine: Fine }) {
  const { palette } = useTheme();
  const status = fineStatus(fine);
  const hours = hoursToAppeal(fine);
  const color = status === 'accepted' ? palette.ok : status === 'appealed' ? palette.warn : palette.danger;
  return (
    <View style={styles.status}>
      <Txt bold size="small" color={color}>
        {t(`fineStatus_${status}` as Message)}
        {fine.simulated ? ` · ${t('fineSimulated')}` : ''}
      </Txt>
      {status === 'fined' ? (
        <Txt size="small" dim>
          {hours > 0 ? tf('fineAppealLeft', { h: hours }) : t('fineAppealClosed')}
        </Txt>
      ) : null}
    </View>
  );
}

function FineDetail({ fine, onAppealed }: { fine: Fine; onAppealed: (fine: Fine) => void }) {
  const { palette } = useTheme();
  const layout = useLayout();
  const actions = useSessionActions();
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<'sent' | 'failed' | 'network' | null>(null);

  function confirm() {
    const text = appealText(draft);
    if (!text || busy) return;
    showDialog(t('confirmAppeal'), t('confirmAppealBody'), [
      { text: t('cancel'), style: 'cancel' },
      { text: t('fineAppealSend'), onPress: () => send(text) },
    ]);
  }

  async function send(text: string) {
    setBusy(true);
    setResult(null);
    try {
      onAppealed(await actions.appealFine(fine.id, text));
      setDraft('');
      setResult('sent');
      hapticDone().catch(() => undefined);
    } catch (err) {
      setResult(err instanceof NetworkError ? 'network' : 'failed');
      hapticFail().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: layout.gap }}>
      <View style={[styles.card, { backgroundColor: palette.panel, borderColor: palette.edge }]}>
        <View style={styles.cardTop}>
          <Txt bold size="data">
            {fine.headline}
          </Txt>
          <Txt bold size="data">
            {money(fine.amount, fine.currency, LOCALES[getLang()])}
          </Txt>
        </View>
        <Txt size="small" dim>
          {[fine.number, when(fine.occurred_at), fine.vehicle, fine.route].filter(Boolean).join(' · ')}
        </Txt>
        <StatusLine fine={fine} />
      </View>

      <View style={styles.section}>
        <Txt bold size="small" color={palette.ink2}>
          {t('fineWhy')}
        </Txt>
        <Txt size="body">{fine.summary}</Txt>
      </View>

      {fine.checks.length ? (
        <View style={styles.section} accessibilityRole="list">
          <Txt bold size="small" color={palette.ink2}>
            {t('fineChecks')}
          </Txt>
          {fine.checks.map((check) => (
            <View key={check.label} style={styles.check} accessible accessibilityLabel={`${check.label}. ${check.detail}`}>
              {/* a word-like mark and a shape, never colour alone */}
              <Txt bold size="body" color={check.ok ? palette.ok : palette.danger}>
                {check.ok ? '✓' : '✗'}
              </Txt>
              <View style={styles.checkText}>
                <Txt bold size="body">
                  {check.label}
                </Txt>
                {check.detail ? (
                  <Txt size="small" dim>
                    {check.detail}
                  </Txt>
                ) : null}
              </View>
            </View>
          ))}
        </View>
      ) : null}

      {fine.appeal_text ? (
        <View style={styles.section}>
          <Txt bold size="small" color={palette.ink2}>
            {t('fineAppealWrite')}
          </Txt>
          <Txt size="body">{fine.appeal_text}</Txt>
        </View>
      ) : null}
      {fine.appeal_answer ? (
        <View style={styles.section}>
          <Txt bold size="small" color={palette.ink2}>
            {t('fineAnswer')}
          </Txt>
          <Txt size="body">{fine.appeal_answer}</Txt>
        </View>
      ) : null}

      {fine.can_appeal ? (
        <View style={styles.section}>
          <Txt bold size="small" color={palette.ink2}>
            {t('fineAppealWrite')}
          </Txt>
          <Field
            value={draft}
            onChangeText={setDraft}
            placeholder={t('fineAppealHint')}
            maxLength={APPEAL_MAX}
            multiline
            editable={!busy}
            style={[styles.input, { minHeight: layout.phone ? 112 : 160 }]}
          />
          <Txt size="small" dim>
            {draft.length} / {APPEAL_MAX}
          </Txt>
          <Action
            label={busy ? t('loading') : t('fineAppealSend')}
            onPress={confirm}
            kind="accent"
            disabled={busy || !appealText(draft)}
          />
        </View>
      ) : null}

      {result ? (
        <Notice
          item={{
            key: 'appeal',
            tone: result === 'sent' ? 'ok' : 'danger',
            title: result === 'sent' ? t('fineAppealSent') : result === 'network' ? t('network') : t('fineAppealFailed'),
            live: 'polite',
          }}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space[4],
  },
  headStack: {
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  card: {
    ...shape.control,
    borderWidth: 1,
    padding: space[5],
    gap: space[2],
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: space[4],
  },
  status: {
    gap: space[1],
  },
  section: {
    gap: space[2],
  },
  check: {
    flexDirection: 'row',
    gap: space[3],
    alignItems: 'flex-start',
  },
  checkText: {
    flexShrink: 1,
  },
  input: {
    paddingVertical: space[4],
    textAlignVertical: 'top',
  },
});
