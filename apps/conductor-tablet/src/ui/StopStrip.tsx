import { StyleSheet, View } from 'react-native';

import { stopWindow, type StopView } from '../shift/progress';
import { Txt } from './cabin';
import { useTheme } from './ThemeProvider';
import { border, space } from './theme';

/** `ahead` is how many stops after the next one are drawn; with large text two cells are all that fit a name. */
export function StopStrip({ stops, color, ahead = 3 }: { stops: StopView[]; color: string; ahead?: number }) {
  const { palette } = useTheme();
  const shown = stopWindow(stops, 0, ahead);
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
                  next && { width: 34, height: 34, borderRadius: border.round, borderColor: palette.ink, backgroundColor: palette.signal },
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
    gap: space[2],
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
    borderRadius: border.round,
    borderWidth: 6,
  },
  name: {
    textAlign: 'center',
    paddingHorizontal: 2,
  },
});
