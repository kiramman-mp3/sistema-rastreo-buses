import { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { ApiError, AuthError, NetworkError } from '../src/api/client';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { LangSwitch } from '../src/ui/LangSwitch';
import { colors, hit, type } from '../src/ui/theme';

export default function Login() {
  useLang();
  const session = useSession();
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [odooUrl, setOdooUrl] = useState(session.snapshot.odooUrl);

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
      else if (err instanceof AuthError || (err instanceof ApiError && err.status === 401)) {
        setError(t('badCredentials'));
      } else if (err instanceof NetworkError) {
        setError(t('network'));
      } else {
        setError(t('badCredentials'));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.page}>
      <Text style={styles.title}>{t('login')}</Text>
      <Button label={t('scanDriverBadge')} onPress={() => router.push('/scan')} />
      <View style={styles.divider}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>{t('orManualLogin')}</Text>
        <View style={styles.dividerLine} />
      </View>
      <TextInput
        value={login}
        onChangeText={setLogin}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder={t('user')}
        style={styles.input}
      />
      <TextInput
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder={t('password')}
        style={styles.input}
      />
      <TextInput
        value={odooUrl}
        onChangeText={setOdooUrl}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder={t('odooUrl')}
        style={[styles.input, styles.inputSecondary]}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button label={t('login')} onPress={submit} disabled={busy || !login || !password} />
      <LangSwitch />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper, padding: 32, justifyContent: 'center', gap: 16, maxWidth: 560, alignSelf: 'center', width: '100%' },
  title: { fontSize: type.title, color: colors.ink, fontWeight: '700', marginBottom: 8 },
  divider: { flexDirection: 'row', alignItems: 'center', marginVertical: 4, gap: 12 },
  dividerLine: { flex: 1, height: 1, backgroundColor: colors.line },
  dividerText: { fontSize: type.body - 2, color: colors.muted, fontWeight: '500' },
  input: {
    minHeight: hit,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: type.body,
    backgroundColor: '#fff',
    color: colors.ink,
  },
  inputSecondary: { fontSize: type.body - 2, color: colors.muted },
  error: { color: colors.bus, fontSize: type.body },
  hint: { fontSize: type.body - 2, color: colors.muted },
});
