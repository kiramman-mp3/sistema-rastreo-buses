import { Pressable, Text, StyleSheet } from 'react-native';

import { colors, hit, type } from './theme';

type Props = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  danger?: boolean;
};

export function Button({ label, onPress, disabled, danger }: Props) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.btn, danger && styles.danger, disabled && styles.disabled]}
    >
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    minHeight: hit,
    backgroundColor: colors.route,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  danger: { backgroundColor: colors.bus },
  disabled: { backgroundColor: colors.taken },
  label: { color: '#fff', fontSize: type.button, fontWeight: '600' },
});
