import { createElement } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import type { RouteMap } from '../api/types';
import { t } from '../i18n';
import { Txt } from '../ui/cabin';
import { useTheme } from '../ui/ThemeProvider';
import { buildMapHtml, type MapBus } from './html';

type Props = {
  route: RouteMap | null;
  bus: MapBus;
  nextStopId: number | null;
};

/** Web build (previews and screenshots): the same Leaflet page as the tablet, in an iframe. */
export function RouteMapView({ route, bus, nextStopId }: Props) {
  const { palette } = useTheme();
  if (!route) {
    return (
      <View style={[styles.box, styles.center, { backgroundColor: palette.panel }]} accessibilityLabel={t('map_label')}>
        <ActivityIndicator size="large" color={palette.ink} />
        <Txt size="body" dim>
          {t('loadingMap')}
        </Txt>
      </View>
    );
  }
  return (
    <View style={styles.box} accessibilityLabel={t('map_label')}>
      {createElement('iframe', {
        title: t('map_label'),
        srcDoc: buildMapHtml(route, bus, nextStopId),
        style: { border: 0, width: '100%', height: '100%' },
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flex: 1,
    minHeight: 280,
    overflow: 'hidden',
    borderRadius: 8,
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
});
