import { useCallback, useEffect, useMemo, useRef } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

import type { RouteMap } from '../api/types';
import { t } from '../i18n';
import { useLang } from '../i18n/LangProvider';
import { buildMapHtml, mapUpdateScript, type MapBus } from './html';
import { Txt } from '../ui/cabin';
import { useTheme } from '../ui/ThemeProvider';

type Props = {
  route: RouteMap | null;
  bus: MapBus;
  nextStopId: number | null;
};

export function RouteMapView({ route, bus, nextStopId }: Props) {
  const { palette } = useTheme();
  const lang = useLang();
  const webView = useRef<WebView<object>>(null);
  // The page is built once per route (and language), without the bus: every GPS fix goes in through
  // the script below. A new `html` would reload the map and put the zoom back.
  const source = useMemo(
    () =>
      route
        ? {
            html: buildMapHtml(route, null, null, { stop: t('mapStop'), you: t('mapYou'), recenter: t('mapRecenter') }),
            baseUrl: 'https://busesuta2340.eastus2.cloudapp.azure.com',
          }
        : null,
    // t() reads the active language, so the page is rebuilt when it changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [route, lang],
  );
  const latest = useRef({ bus, nextStopId });

  const pushLatest = useCallback(() => {
    webView.current?.injectJavaScript(mapUpdateScript(latest.current.bus, latest.current.nextStopId));
  }, []);

  useEffect(() => {
    latest.current = { bus, nextStopId };
    webView.current?.injectJavaScript(mapUpdateScript(bus, nextStopId));
  }, [bus, nextStopId]);

  if (!route || !source) {
    return (
      <View style={[styles.box, { backgroundColor: palette.panel }]} accessibilityLabel={t('map_label')}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={palette.ink} />
          <Txt size="body" dim>
            {t('loadingMap')}
          </Txt>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.box} accessibilityLabel={t('map_label')}>
      <WebView
        originWhitelist={['*']}
        ref={webView}
        source={source}
        onLoadEnd={pushLatest}
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
    minHeight: 120,
    overflow: 'hidden',
    borderRadius: 8,
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
});

