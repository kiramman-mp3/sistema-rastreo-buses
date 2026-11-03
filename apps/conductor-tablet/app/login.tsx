import { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { ApiError, AuthError, NetworkError } from '../src/api/client';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Field, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { LangSwitch } from '../src/ui/LangSwitch';
import { LineMark } from '../src/ui/LineMark';
import { Notice } from '../src/ui/Notice';
import { shape, space } from '../src/ui/theme';
import { useTheme } from '../src/ui/ThemeProvider';

export default function Login() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const session = useSession();
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [odooUrl, setOdooUrl] = useState(session.snapshot.odooUrl);
  // The server address is for technical support only: it opens with a long press on the mark.
  const [showServer, setShowServer] = useState(false);

  useFocusEffect(
    useCallback(() => {
      setOdooUrl(session.snapshot.odooUrl);
    }, [session.snapshot.odooUrl]),
  );

  async function submit() {
    setBusy(true);
    setError('');
    try {
      await session.setOdooUrl(odooUrl);
      await session.login(login.trim(), password);
      // `session.snapshot` here is the one of the last render: let the index route decide with the new one.
      router.replace('/');
    } catch (err) {
      if (err instanceof Error && err.message === 'bad_odoo_url') setError(t('qrBad'));
      else if (err instanceof NetworkError) setError(t('network'));
      else if (err instanceof AuthError || (err instanceof ApiError && err.status === 401)) setError(t('badCredentials'));
      else if (err instanceof ApiError && err.status === 429) setError(t('tooMany'));
      else setError(t('serverError'));
    } finally {
      setBusy(false);
    }
  }

  // Side by side when there is width; stacked (and centred) on a phone in portrait.
  const side = layout.wide;

  return (
    <Screen scroll style={[styles.page, side ? styles.pageSide : styles.pageStack, { gap: side ? space[12] : layout.gap * 2 }]}>
      <View style={[styles.intro, !side && styles.introStack]}>
        <Pressable onLongPress={() => setShowServer((v) => !v)} accessibilityLabel="Buses UTA" style={styles.brand}>
          <LineMark />
          <Txt bold size="data">
            Buses UTA
          </Txt>
        </Pressable>
        <Txt bold size="title">
          {t('loginTitle')}
        </Txt>
        <Txt size="body" dim>
          {t('loginHelp')}
        </Txt>
        <View style={styles.langs}>
          <LangSwitch />
        </View>
      </View>

      <View style={[styles.card, side ? styles.cardSide : styles.cardStack, { backgroundColor: palette.panel, padding: layout.phone ? space[4] : space[6] }]}>
        <Action label={t('scanDriverBadge')} onPress={() => router.push('/scan')} kind="accent" />
        <Txt size="small" dim style={styles.or}>
          {t('orManualLogin')}
        </Txt>
        <Field
          value={login}
          onChangeText={setLogin}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder={t('user')}
          accessibilityLabel={t('user')}
        />
        <Field
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder={t('password')}
          accessibilityLabel={t('password')}
        />
        {showServer ? (
          <View style={styles.server}>
            <Txt size="small" dim>
              {t('serverHint')}
            </Txt>
            <Field
              value={odooUrl}
              onChangeText={setOdooUrl}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder={t('odooUrl')}
                  accessibilityLabel={t('odooUrl')}
                />
          </View>
        ) : null}
        {error ? (
          <Notice item={{ key: 'error', tone: 'danger', title: error, live: 'polite' }} />
        ) : null}
        <Action
          label={busy ? t('loading') : t('login')}
          onPress={submit}
          kind="quiet"
          disabled={busy || !login || !password}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  page: {
    justifyContent: 'center',
  },
  pageSide: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  pageStack: {
    flexDirection: 'column',
  },
  intro: {
    flex: 1,
    gap: space[3],
  },
  introStack: {
    flexGrow: 0,
    flexShrink: 0,
    flexBasis: 'auto',
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[3],
    marginBottom: space[6],
    alignSelf: 'flex-start',
  },
  langs: {
    marginTop: space[5],
  },
  card: {
    ...shape.control,
    gap: space[3],
  },
  cardSide: {
    flex: 1,
    maxWidth: 560,
  },
  cardStack: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  or: {
    textAlign: 'center',
    marginVertical: space[1],
  },
  server: {
    gap: space[2],
  },
});
