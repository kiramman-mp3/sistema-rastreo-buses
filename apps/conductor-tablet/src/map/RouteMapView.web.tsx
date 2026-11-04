import { createElement, useCallback, useEffect, useMemo, useRef } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import type { RouteMap } from '../api/types';
import { t } from '../i18n';
import { useLang } from '../i18n/LangProvider';
import { Txt } from '../ui/cabin';
import { useTheme } from '../ui/ThemeProvider';
import { buildMapHtml, type MapBus } from './html';

type BusMapWindow = Window & { busMap?: { update(state: { bus: MapBus; nextStopId: number | null }): void } };

type Props = {
  route: RouteMap | null;
  bus: MapBus;
  nextStopId: number | null;
};

/** Web build (previews and screenshots): the same Leaflet page as the tablet, in an iframe. */
export function RouteMapView({ route, bus, nextStopId }: Props) {
  const { palette } = useTheme();
  const lang = useLang();
  const frame = useRef<HTMLIFrameElement | null>(null);
  const html = useMemo(
    () => (route ? buildMapHtml(route, null, null, { stop: t('mapStop'), you: t('mapYou'), recenter: t('mapRecenter') }) : null),
    // t() reads the active language, so the page is rebuilt when it changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [route, lang],
  );
  const latest = useRef({ bus, nextStopId });

  // The same page as the tablet: it exposes `busMap.update`, so the iframe is never reloaded.
  const push = useCallback(() => {
    try {
      (frame.current?.contentWindow as BusMapWindow | null)?.busMap?.update(latest.current);
    } catch {
      // the page is still loading: onLoad pushes again
    }
  }, []);
  useEffect(() => {
    latest.current = { bus, nextStopId };
    push();
  }, [bus, nextStopId, push]);

  if (!route || !html) {
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
        ref: frame,
        srcDoc: html,
        onLoad: push,
        style: { border: 0, width: '100%', height: '100%' },
      })}
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
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
});
