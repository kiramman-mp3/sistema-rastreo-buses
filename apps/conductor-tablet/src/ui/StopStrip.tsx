import { StyleSheet, View } from 'react-native';

import type { StopView } from '../shift/progress';
import { Txt } from './cabin';
import { useTheme } from './ThemeProvider';

/** The stops around the next one, laid flat: passed stops filled, the next one in signal yellow. */
export function stopWindow(stops: StopView[], before = 1, after = 4): StopView[] {
  const next = stops.findIndex((s) => s.status === 'next');
  if (next < 0) return stops.slice(-(before + after + 1));
  const from = Math.max(0, next - before);
  return stops.slice(from, from + before + after + 1);
}

export function StopStrip({ stops, color }: { stops: StopView[]; color: string }) {
  const { palette } = useTheme();
  const shown = stopWindow(stops);
  const line = palette.mode === 'night' ? palette.line : color;
  return (
    <View style={styles.strip} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {shown.map((stop, index) => {
        const next = stop.status === 'next';
        const passed = stop.status === 'arrived';
        return (
          <View key={stop.id} style={styles.cell}>
            <View style={styles.track}>
              <View style={[styles.bar, { backgroundColor: line }, index === 0 && styles.barStart, index === shown.length - 1 && styles.barEnd]} />
              <View
                style={[
                  styles.dot,
                  { borderColor: line, backgroundColor: passed ? line : palette.ground },
                  next && { width: 34, height: 34, borderRadius: 17, borderColor: palette.ink, backgroundColor: palette.signal },
                ]}
              />
            </View>
            <Txt size="small" bold={next} dim={!next} lines={2} style={styles.name}>
              {stop.name}
            </Txt>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  strip: {
    flexDirection: 'row',
  },
  cell: {
    flex: 1,
    alignItems: 'center',
    gap: 8,
  },
  track: {
    height: 34,
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bar: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 8,
  },
  barStart: {
    left: '50%',
  },
  barEnd: {
    right: '50%',
  },
  dot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 6,
  },
  name: {
    textAlign: 'center',
    paddingHorizontal: 4,
  },
});
