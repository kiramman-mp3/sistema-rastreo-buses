import { useState } from 'react';
import { router } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StyleSheet, View } from 'react-native';

import { parseDriverBadge } from '../src/config/odooUrl';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Txt } from '../src/ui/cabin';
import { useTheme } from '../src/ui/ThemeProvider';

export default function ScanScreen() {
  useLang();
  const session = useSession();
  const { palette } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function onScan({ data }: { data: string }) {
    if (busy) return;
    setBusy(true);
    setError('');

    const badge = parseDriverBadge(data);
    if (badge) {
      try {
        await session.loginWithBadge(badge.token, badge.odooUrl);
        router.replace(session.snapshot.shift ? '/shift' : '/select');
        return;
      } catch {
        setError(t('badgeError'));
        setBusy(false);
        return;
      }
    }

    try {
      await session.setOdooUrl(data);
      router.back();
    } catch {
      setError(t('qrBad'));
      setBusy(false);
    }
  }

  if (!permission?.granted) {
    return (
      <View style={[styles.page, { backgroundColor: palette.ground }]}>
        <Txt size="body">{t('cameraNeed')}</Txt>
        <Action label={t('scanQr')} onPress={() => requestPermission()} kind="accent" />
        <Action label={t('cancel')} onPress={() => router.back()} kind="quiet" />
      </View>
    );
  }

  return (
    <View style={styles.camera}>
      <CameraView
        style={StyleSheet.absoluteFill}
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
        onBarcodeScanned={busy ? undefined : onScan}
      />
      {busy ? (
        <Txt bold size="body" color="#FFFFFF" style={styles.info}>
          {t('badgeLoggingIn')}
        </Txt>
      ) : null}
      {error ? (
        <Txt bold size="body" color="#FFFFFF" style={styles.info}>
          {error}
        </Txt>
      ) : null}
      <View style={styles.bar}>
        <Action label={t('cancel')} onPress={() => router.back()} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, padding: 32, justifyContent: 'center', gap: 16 },
  camera: { flex: 1, backgroundColor: '#000' },
  info: { textAlign: 'center', marginTop: 24, backgroundColor: 'rgba(0,0,0,0.6)', padding: 12 },
  bar: { position: 'absolute', bottom: 24, left: 24, right: 24 },
});
