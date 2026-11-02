import { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ApiError, AuthError, NetworkError } from '../src/api/client';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { LangSwitch } from '../src/ui/LangSwitch';
import { LineMark } from '../src/ui/LineMark';
import { fonts } from '../src/ui/theme';
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

  const field = [
    styles.input,
    {
      backgroundColor: palette.field,
      color: palette.ink,
      borderColor: palette.ink2,
      minHeight: layout.phone ? 52 : 64,
      fontSize: layout.sizes.body,
    },
  ];
  // Side by side when there is width; stacked (and centred) on a phone in portrait.
  const side = layout.wide;

  return (
    <Screen scroll style={[styles.page, side ? styles.pageSide : styles.pageStack, { gap: side ? 48 : layout.gap * 2 }]}>
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

      <View style={[styles.card, side ? styles.cardSide : styles.cardStack, { backgroundColor: palette.panel, padding: layout.phone ? 18 : 28 }]}>
        <Action label={t('scanDriverBadge')} onPress={() => router.push('/scan')} kind="accent" />
        <Txt size="small" dim style={styles.or}>
          {t('orManualLogin')}
        </Txt>
        <TextInput
          value={login}
          onChangeText={setLogin}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder={t('user')}
          placeholderTextColor={palette.ink2}
          accessibilityLabel={t('user')}
          style={field}
        />
        <TextInput
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder={t('password')}
          placeholderTextColor={palette.ink2}
          accessibilityLabel={t('password')}
          style={field}
        />
        {showServer ? (
          <View style={styles.server}>
            <Txt size="small" dim>
              {t('serverHint')}
            </Txt>
            <TextInput
              value={odooUrl}
              onChangeText={setOdooUrl}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder={t('odooUrl')}
              placeholderTextColor={palette.ink2}
              accessibilityLabel={t('odooUrl')}
              style={field}
            />
          </View>
        ) : null}
        {error ? (
          <View style={[styles.error, { borderColor: palette.danger }]} accessibilityLiveRegion="polite">
            <Txt bold size="body" color={palette.danger}>
              {error}
            </Txt>
          </View>
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
    gap: 14,
  },
  introStack: {
    flexGrow: 0,
    flexShrink: 0,
    flexBasis: 'auto',
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 24,
    alignSelf: 'flex-start',
  },
  langs: {
    marginTop: 20,
  },
  card: {
    borderRadius: 8,
    gap: 14,
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
    marginVertical: 4,
  },
  input: {
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 18,
    fontFamily: fonts.text,
  },
  server: {
    gap: 6,
  },
  error: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderLeftWidth: 8,
  },
});
