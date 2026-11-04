import { StyleSheet, View } from 'react-native';

import { stopWindow, type StopView } from '../shift/progress';
import { Txt } from './cabin';
import { useTheme } from './ThemeProvider';
import { border, space } from './theme';

type StripProps = {
  stops: StopView[];
  color: string;
  /** How many stops after the next one are drawn; with large text two cells are all that fit a name. */
  ahead?: number;
  /** A phone on its side: smaller marks and one line per name, so the whole strip fits in little height. */
  compact?: boolean;
};

export function StopStrip({ stops, color, ahead = 3, compact = false }: StripProps) {
  const { palette } = useTheme();
  const shown = stopWindow(stops, 0, ahead);
  const line = palette.mode === 'night' ? palette.line : color;
  const track = compact ? 26 : 34;
  const dot = compact ? 16 : 24;
  const nextDot = compact ? 26 : 34;
  return (
    <View style={styles.strip} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {shown.map((stop, index) => {
        const next = stop.status === 'next';
        const passed = stop.status === 'arrived';
        return (
          <View key={stop.id} style={[styles.cell, compact && styles.cellCompact]}>
            <View style={[styles.track, { height: track }]}>
              <View
                style={[
                  styles.bar,
                  { backgroundColor: line, height: compact ? 6 : 8 },
                  index === 0 && styles.barStart,
                  index === shown.length - 1 && styles.barEnd,
                ]}
              />
              <View
                style={[
                  styles.dot,
                  { width: dot, height: dot, borderWidth: compact ? 4 : 6, borderColor: line, backgroundColor: passed ? line : palette.ground },
                  next && {
                    width: nextDot,
                    height: nextDot,
                    borderRadius: border.round,
                    borderColor: palette.ink,
                    backgroundColor: palette.signal,
                  },
                ]}
              />
            </View>
            <Txt size="small" bold={next} dim={!next} lines={compact ? 1 : 2} style={styles.name}>
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
  cellCompact: {
    gap: space[1],
  },
  track: {
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bar: {
    position: 'absolute',
    left: 0,
    right: 0,
  },
  barStart: {
    left: '50%',
  },
  barEnd: {
    right: '50%',
  },
  dot: {
    borderRadius: border.round,
  },
  name: {
    textAlign: 'center',
    paddingHorizontal: 2,
  },
});
