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
import { shape, space } from './theme';
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
        { minHeight: hit + 8, backgroundColor: selected ? palette.ink : palette.panel, opacity: usable ? 1 : 0.45 },
      ]}
    >
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
  return (
    <Press
      onPress={() => onPick(route)}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      style={[styles.option, styles.routeOption, { minHeight: hit + 8, backgroundColor: selected ? palette.ink : palette.panel }]}
    >
      <View style={[styles.chip, { backgroundColor: chip }]}>
        <Txt bold size="body" color={readableOn(chip)}>
          {route.code}
        </Txt>
      </View>
      <Txt bold size="body" color={selected ? palette.ground : palette.ink} lines={2} style={styles.routeName}>
        {route.name}
      </Txt>
    </Press>
  );
});

const styles = StyleSheet.create({
  option: {
    ...shape.control,
    paddingHorizontal: space[5],
    paddingVertical: space[3],
    justifyContent: 'center',
  },
  routeOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[4],
  },
  chip: {
    minWidth: 56,
    minHeight: 44,
    paddingHorizontal: space[3],
    ...shape.control,
    alignItems: 'center',
    justifyContent: 'center',
  },
  routeName: {
    flex: 1,
  },
});
