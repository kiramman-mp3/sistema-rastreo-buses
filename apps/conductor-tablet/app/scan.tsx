import { useState } from 'react';
import { router } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StyleSheet, Text, View } from 'react-native';

import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Button } from '../src/ui/Button';
import { colors, type } from '../src/ui/theme';

export default function ScanScreen() {
  useLang();
  const session = useSession();
  const [permission, requestPermission] = useCameraPermissions();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function onScan({ data }: { data: string }) {
    if (busy) return;
    setBusy(true);
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
      <View style={styles.page}>
        <Text style={styles.body}>{t('cameraNeed')}</Text>
        <Button label={t('scanQr')} onPress={() => requestPermission()} />
        <Button label={t('cancel')} onPress={() => router.back()} />
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
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.bar}>
        <Button label={t('cancel')} onPress={() => router.back()} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper, padding: 32, justifyContent: 'center', gap: 16 },
  camera: { flex: 1, backgroundColor: '#000' },
  body: { fontSize: type.body, color: colors.ink },
  error: { color: '#fff', fontSize: type.body, textAlign: 'center', marginTop: 24 },
  bar: { position: 'absolute', bottom: 24, left: 24, right: 24 },
});
