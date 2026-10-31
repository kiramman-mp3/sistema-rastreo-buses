import { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

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
  const [showServerConfig, setShowServerConfig] = useState(false);

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
      {/* Header Emblem */}
      <View style={styles.brandHeader}>
        <View style={styles.brandIcon}>
          <Text style={styles.brandIconText}>🚌</Text>
        </View>
        <Text style={styles.brandTitle}>Buses UTA</Text>
        <Text style={styles.brandSub}>Universidad Técnica de Ambato · Terminal Chofer</Text>
      </View>

      {/* Main Login Card */}
      <View style={styles.card}>
        <Button
          label={t('scanDriverBadge')}
          onPress={() => router.push('/scan')}
          style={styles.scanBtn}
        />

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
          placeholderTextColor={colors.muted}
          style={styles.input}
        />
        <TextInput
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder={t('password')}
          placeholderTextColor={colors.muted}
          style={styles.input}
        />

        {/* Expandable Server Config for Technical Setup */}
        <Pressable
          onPress={() => setShowServerConfig(!showServerConfig)}
          style={styles.serverToggle}
        >
          <Text style={styles.serverToggleText}>
            {showServerConfig ? '▼ Ocultar servidor' : '⚙️ Servidor: ' + (odooUrl || 'Por defecto')}
          </Text>
        </Pressable>

        {showServerConfig ? (
          <TextInput
            value={odooUrl}
            onChangeText={setOdooUrl}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder={t('odooUrl')}
            placeholderTextColor={colors.muted}
            style={[styles.input, styles.inputSecondary]}
          />
        ) : null}

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <Button
          label={busy ? t('loading') : t('login')}
          onPress={submit}
          disabled={busy || !login || !password}
          style={styles.loginBtn}
        />
      </View>

      <LangSwitch />
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: colors.paper,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  brandHeader: {
    alignItems: 'center',
    gap: 4,
    marginBottom: 8,
  },
  brandIcon: {
    width: 56,
    height: 56,
    borderRadius: 16,
    backgroundColor: colors.route,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  brandIconText: {
    fontSize: 28,
  },
  brandTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: colors.ink,
    letterSpacing: -0.5,
  },
  brandSub: {
    fontSize: 13,
    color: colors.muted,
    fontWeight: '600',
  },
  card: {
    width: '100%',
    maxWidth: 480,
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  scanBtn: {
    minHeight: hit + 4,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 4,
    gap: 12,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.line,
  },
  dividerText: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    minHeight: hit,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    paddingHorizontal: 16,
    fontSize: type.body - 1,
    backgroundColor: '#F8FAFC',
    color: colors.ink,
  },
  inputSecondary: {
    fontSize: 13,
    color: colors.muted,
    backgroundColor: '#F1F5F9',
  },
  serverToggle: {
    paddingVertical: 4,
  },
  serverToggleText: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: '600',
  },
  errorBox: {
    backgroundColor: colors.busLight,
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.bus,
  },
  errorText: {
    color: colors.bus,
    fontSize: 13,
    fontWeight: '600',
  },
  loginBtn: {
    minHeight: hit,
  },
});
