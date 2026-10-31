import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';

import type { RouteMap } from '../api/types';
import { t } from '../i18n';
import { buildMapHtml, type MapBus } from './html';
import { colors, type } from '../ui/theme';

type Props = {
  route: RouteMap | null;
  bus: MapBus;
  nextStopId: number | null;
};

export function RouteMapView({ route, bus, nextStopId }: Props) {
  if (!route) {
    return (
      <View style={styles.box} accessibilityLabel={t('map_label')}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.route} />
          <Text style={styles.loadingText}>{t('loadingMap')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.box} accessibilityLabel={t('map_label')}>
      <WebView
        originWhitelist={['*']}
        source={{
          html: buildMapHtml(route, bus, nextStopId),
          baseUrl: 'https://busesuta2340.eastus2.cloudapp.azure.com',
        }}
        style={styles.web}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        allowFileAccess={true}
        allowUniversalAccessFromFileURLs={true}
        mixedContentMode="always"
        scalesPageToFit={false}
        androidLayerType="hardware"
        setSupportMultipleWindows={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flex: 1,
    minHeight: 280,
    overflow: 'hidden',
    borderRadius: 16,
    backgroundColor: '#E2E8F0',
    borderWidth: 1,
    borderColor: colors.line,
  },
  web: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: type.body,
    color: colors.muted,
    fontWeight: '600',
  },
});

