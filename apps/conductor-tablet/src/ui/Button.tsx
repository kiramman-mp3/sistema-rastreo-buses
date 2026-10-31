import { Pressable, Text, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';

import { colors, hit, type } from './theme';

type Props = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  danger?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'outline';
  style?: StyleProp<ViewStyle>;
};

export function Button({ label, onPress, disabled, danger, variant = 'primary', style }: Props) {
  const isDanger = danger || variant === 'danger';
  const isOutline = variant === 'outline';
  const isSecondary = variant === 'secondary';

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.btn,
        isSecondary && styles.secondary,
        isOutline && styles.outline,
        isDanger && styles.danger,
        disabled && styles.disabled,
        style,
      ]}
    >
      <Text
        style={[
          styles.label,
          isOutline && styles.outlineLabel,
          isSecondary && styles.secondaryLabel,
          disabled && styles.disabledLabel,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    minHeight: hit,
    backgroundColor: colors.route,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  secondary: {
    backgroundColor: '#E2E8F0',
  },
  secondaryLabel: {
    color: colors.ink,
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: colors.route,
  },
  outlineLabel: {
    color: colors.route,
  },
  danger: {
    backgroundColor: colors.bus,
  },
  disabled: {
    backgroundColor: '#CBD5E1',
    borderColor: '#CBD5E1',
  },
  disabledLabel: {
    color: '#64748B',
  },
  label: {
    color: '#fff',
    fontSize: type.button,
    fontWeight: '700',
  },
});

