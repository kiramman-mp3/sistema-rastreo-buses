import { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ApiError, AuthError, NetworkError } from '../src/api/client';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Txt } from '../src/ui/cabin';
import { LangSwitch } from '../src/ui/LangSwitch';
import { LineMark } from '../src/ui/LineMark';
import { fonts, sizes } from '../src/ui/theme';
import { useTheme } from '../src/ui/ThemeProvider';

export default function Login() {
  useLang();
  const { palette } = useTheme();
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
      router.replace(session.snapshot.shift ? '/shift' : '/select');
    } catch (err) {
      if (err instanceof Error && err.message === 'bad_odoo_url') setError(t('qrBad'));
      else if (err instanceof NetworkError) setError(t('network'));
      else if (err instanceof AuthError || (err instanceof ApiError && err.status === 401)) setError(t('badCredentials'));
      else setError(t('badCredentials'));
    } finally {
      setBusy(false);
    }
  }

  const field = [styles.input, { backgroundColor: palette.field, color: palette.ink, borderColor: palette.ink2 }];

  return (
    <View style={[styles.page, { backgroundColor: palette.ground }]}>
      <View style={styles.intro}>
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

      <View style={[styles.card, { backgroundColor: palette.panel }]}>
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
          kind="neutral"
          disabled={busy || !login || !password}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 48,
    paddingHorizontal: 56,
  },
  intro: {
    flex: 1,
    gap: 14,
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
    flex: 1,
    maxWidth: 560,
    padding: 28,
    borderRadius: 8,
    gap: 14,
  },
  or: {
    textAlign: 'center',
    marginVertical: 4,
  },
  input: {
    minHeight: 64,
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 18,
    fontSize: sizes.body,
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
