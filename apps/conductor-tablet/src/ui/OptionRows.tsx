/**
 * The rows of the bus and line lists. They are memoised on what they draw, so picking one bus redraws two
 * rows (the one that lost the mark and the one that got it), not the whole list.
 */
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';

import type { Route, Vehicle } from '../api/types';
import { t } from '../i18n';
import { Press, Txt } from './cabin';
import { readableOn } from './contrast';
import { border, lift, shape, space } from './theme';
import { useTheme } from './ThemeProvider';

type BusOptionProps = {
  bus: Vehicle;
  selected: boolean;
  /** Free and with a GPS device: only these can start a shift. */
  usable: boolean;
  hit: number;
  onPick: (bus: Vehicle) => void;
};

export const BusOption = memo(function BusOption({ bus, selected, usable, hit, onPick }: BusOptionProps) {
  const { palette } = useTheme();
  return (
    <Press
      disabled={!usable}
      onPress={() => onPick(bus)}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected, disabled: !usable }}
      style={[
        styles.option,
        styles.row,
        {
          minHeight: hit + 8,
          backgroundColor: selected ? palette.ink : palette.panel,
          borderColor: selected ? palette.ink : palette.edge,
          opacity: usable ? 1 : 0.45,
        },
        selected && palette.mode === 'day' && lift,
      ]}
    >
      <View style={styles.grow}>
        <Txt bold size="data" color={selected ? palette.ground : palette.ink}>
          {bus.name}
        </Txt>
        <Txt size="small" color={selected ? palette.ground : palette.ink2}>
          {!bus.available
            ? `${bus.plate} · ${t('busTaken')}`
            : bus.has_gps === false
              ? `${bus.plate} · ${t('busNoGps')}`
              : bus.plate}
        </Txt>
      </View>
      {usable ? <Pick on={selected} /> : null}
    </Press>
  );
});

type RouteOptionProps = {
  route: Route;
  selected: boolean;
  hit: number;
  onPick: (route: Route) => void;
};

export const RouteOption = memo(function RouteOption({ route, selected, hit, onPick }: RouteOptionProps) {
  const { palette } = useTheme();
  const chip = route.color || palette.accent;
  // Picked: the whole card takes the line's colour, so the choice reads from across the cab.
  const fill = selected ? chip : palette.panel;
  const ink = selected ? readableOn(chip) : palette.ink;
  return (
    <Press
      onPress={() => onPick(route)}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      style={[
        styles.option,
        styles.row,
        { minHeight: hit + 16, backgroundColor: fill, borderColor: selected ? chip : palette.edge },
        selected && palette.mode === 'day' && lift,
      ]}
    >
      <View style={[styles.chip, selected ? { backgroundColor: 'rgba(255,255,255,0.22)' } : { backgroundColor: chip }]}>
        <Txt bold size="body" color={selected ? ink : readableOn(chip)}>
          {route.code}
        </Txt>
      </View>
      <View style={styles.grow}>
        <Txt bold size="body" color={ink} lines={2}>
          {route.name}
        </Txt>
      </View>
      <Pick on={selected} light={selected} />
    </Press>
  );
});

/** The radio mark: a ring when free, a yellow stop with a dark core when picked (shape, not only colour). */
function Pick({ on, light }: { on: boolean; light?: boolean }) {
  const { palette } = useTheme();
  return (
    <View
      accessibilityElementsHidden
      style={[
        styles.pick,
        on
          ? { backgroundColor: palette.signal, borderColor: light ? '#FFFFFF' : palette.signal }
          : { borderColor: palette.mode === 'day' ? '#9AA5A3' : palette.ink2 },
      ]}
    >
      {on ? <View style={[styles.pickCore, { backgroundColor: palette.onSignal }]} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  option: {
    ...shape.control,
    borderWidth: 1,
    paddingHorizontal: space[5],
    paddingVertical: space[3],
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[4],
  },
  pick: {
    width: 28,
    height: 28,
    borderRadius: border.round,
    borderWidth: border.mark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickCore: {
    width: 10,
    height: 10,
    borderRadius: border.round,
  },
  chip: {
    minWidth: 56,
    minHeight: 44,
    paddingHorizontal: space[3],
    ...shape.control,
    alignItems: 'center',
    justifyContent: 'center',
  },
  grow: {
    flex: 1,
  },
});
