/**
 * Building blocks of the cabin screens. Rules: nothing the driver reads is smaller than 20 px, every
 * control is at least 72 px tall, states carry a word and a shape, never colour alone, no emoji.
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import type { GpsHealth } from '../gps/health';
import { fonts, sizes } from './theme';
import { useTheme } from './ThemeProvider';

export const HIT = 72;

type TxtProps = {
  children: ReactNode;
  size?: keyof typeof sizes;
  bold?: boolean;
  dim?: boolean;
  color?: string;
  style?: StyleProp<TextStyle>;
  lines?: number;
  fit?: boolean;
};

export function Txt({ children, size = 'body', bold, dim, color, style, lines, fit }: TxtProps) {
  const { palette } = useTheme();
  return (
    <Text
      numberOfLines={lines}
      adjustsFontSizeToFit={fit}
      minimumFontScale={0.7}
      maxFontSizeMultiplier={1.3}
      style={[
        {
          color: color ?? (dim ? palette.ink2 : palette.ink),
          fontFamily: bold ? fonts.bold : fonts.text,
          fontWeight: bold ? '700' : '400',
          fontSize: sizes[size],
          lineHeight: Math.round(sizes[size] * (size === 'stop' || size === 'title' ? 1.05 : 1.3)),
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

type ActionProps = {
  label: string;
  sub?: string;
  onPress: () => void;
  kind?: 'accent' | 'neutral' | 'quiet';
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityHint?: string;
};

export function Action({ label, sub, onPress, kind = 'neutral', disabled, style, accessibilityHint }: ActionProps) {
  const { palette } = useTheme();
  const bg = kind === 'accent' ? palette.accent : kind === 'quiet' ? 'transparent' : palette.panel;
  const fg = kind === 'accent' ? palette.onAccent : palette.ink;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={sub ? `${label}. ${sub}` : label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [
        styles.action,
        { backgroundColor: bg, borderColor: kind === 'quiet' ? palette.ink2 : bg, opacity: disabled ? 0.35 : 1 },
        pressed && !disabled && { transform: [{ scale: 0.97 }] },
        style,
      ]}
    >
      <Txt bold size="body" color={fg}>
        {label}
      </Txt>
      {sub ? (
        <Txt size="small" color={fg} style={{ opacity: 0.85 }}>
          {sub}
        </Txt>
      ) : null}
    </Pressable>
  );
}

/** GPS state in words with a shape: filled dot sending, hollow dot waiting, square saving, cross off. */
export function GpsBadge({ health, label }: { health: GpsHealth; label: string }) {
  const { palette } = useTheme();
  const color =
    health === 'sending' ? palette.ok : health === 'saving' ? palette.warn : health === 'off' ? palette.danger : palette.ink2;
  return (
    <View style={styles.badge} accessibilityRole="text" accessibilityLabel={label}>
      <View
        style={[
          styles.badgeMark,
          health === 'sending' && { backgroundColor: color, borderRadius: 9 },
          health === 'waiting' && { borderWidth: 3, borderColor: color, borderRadius: 9 },
          health === 'saving' && { backgroundColor: color, borderRadius: 2 },
          health === 'off' && { backgroundColor: color, borderRadius: 2, transform: [{ rotate: '45deg' }] },
        ]}
      />
      <Txt bold size="small" color={color}>
        {label}
      </Txt>
    </View>
  );
}

type SosProps = {
  onFire: () => void;
  title: string;
  hint: string;
  holding: string;
  status?: string | null;
};

/** Press and hold 1.5 s: a bump of the road cannot send an SOS by accident. */
export function SosButton({ onFire, title, hint, holding, status }: SosProps) {
  const { palette } = useTheme();
  const [progress] = useState(() => new Animated.Value(0));
  const fill = useMemo(() => progress.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }), [progress]);
  const [pressing, setPressing] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduce).catch(() => undefined);
  }, []);

  function start() {
    setPressing(true);
    Animated.timing(progress, {
      toValue: 1,
      duration: reduce ? 0 : 1500,
      easing: Easing.linear,
      useNativeDriver: false,
    }).start();
    timer.current = setTimeout(() => {
      setPressing(false);
      progress.setValue(0);
      onFire();
    }, 1500);
  }

  function cancel() {
    setPressing(false);
    if (timer.current) clearTimeout(timer.current);
    progress.stopAnimation();
    progress.setValue(0);
  }

  return (
    <Pressable
      onPressIn={start}
      onPressOut={cancel}
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${hint}`}
      accessibilityActions={[{ name: 'activate', label: title }]}
      onAccessibilityAction={() => onFire()}
      style={[styles.action, styles.sos, { backgroundColor: palette.danger, borderColor: palette.danger }]}
    >
      <Animated.View
        style={[
          styles.sosFill,
          { backgroundColor: palette.onDanger, width: fill },
        ]}
      />
      <Txt bold size="data" color={palette.onDanger}>
        {title}
      </Txt>
      <Txt size="small" color={palette.onDanger}>
        {pressing ? holding : status ?? hint}
      </Txt>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  action: {
    minHeight: HIT,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 2,
    justifyContent: 'center',
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  badgeMark: {
    width: 18,
    height: 18,
  },
  sos: {
    overflow: 'hidden',
  },
  sosFill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    opacity: 0.25,
  },
});
