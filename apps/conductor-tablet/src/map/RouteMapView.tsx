import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

import type { RouteMap } from '../api/types';
import { t } from '../i18n';
import { buildMapHtml, type MapBus } from './html';

type Props = {
  route: RouteMap | null;
  bus: MapBus;
  nextStopId: number | null;
};

export function RouteMapView({ route, bus, nextStopId }: Props) {
  if (!route) return <View style={styles.box} accessibilityLabel={t('map_label')} />;
  return (
    <View style={styles.box} accessibilityLabel={t('map_label')}>
      <WebView
        originWhitelist={['*']}
        source={{ html: buildMapHtml(route, bus, nextStopId) }}
        style={styles.web}
        javaScriptEnabled
        setSupportMultipleWindows={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  box: { flex: 1, minHeight: 220, overflow: 'hidden', borderRadius: 8, backgroundColor: '#d9d1c3' },
  web: { flex: 1, backgroundColor: 'transparent' },
});
