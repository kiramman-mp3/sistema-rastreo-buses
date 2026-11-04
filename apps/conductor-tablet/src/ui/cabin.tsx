/**
 * Building blocks of the cabin screens. Rules: nothing the driver reads is smaller than 20 px on a tablet (16 px on a phone), every
 * control is at least 72 px tall (56 px on a phone), states carry a word and a shape, never colour alone, no emoji.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  AccessibilityInfo,
  Animated,
  Easing,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  TextInput,
  type PressableProps,
  type StyleProp,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import type { GpsHealth } from '../gps/health';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { hapticCommit } from './haptics';
import { createHold, type Hold } from './hold';
import { useLayout } from './layout';
import { border, fonts, shape, sizes, space } from './theme';
import { useTheme } from './ThemeProvider';

/** Tablet control height; phones use `useLayout().hit`. */
export const HIT = 72;

type ScreenProps = {
  children: ReactNode;
  /** Let the content scroll (forms, lists that may not fit on a phone). */
  scroll?: boolean;
  style?: StyleProp<ViewStyle>;
};

/**
 * The frame of every cabin screen: ground colour, padding that keeps clear of notches, cut-outs and
 * the system bars in either orientation, and (when `scroll`) room for the keyboard.
 */
export function Screen({ children, scroll, style }: ScreenProps) {
  const { palette } = useTheme();
  const { gutter, gap } = useLayout();
  const insets = useSafeAreaInsets();
  const frame = {
    paddingTop: insets.top + gutter,
    paddingBottom: insets.bottom + gutter,
    paddingLeft: insets.left + gutter,
    paddingRight: insets.right + gutter,
    gap,
  };
  if (!scroll) {
    return <View style={[styles.screen, { backgroundColor: palette.ground }, frame, style]}>{children}</View>;
  }
  return (
    <KeyboardAvoidingView
      style={[styles.screen, { backgroundColor: palette.ground }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[styles.scrollContent, frame, style]}
        showsVerticalScrollIndicator={false}
      >
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

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

/**
 * How far the system font size may grow the text. Small and body text follows the setting up to 200 %
 * (people with low vision depend on it); the big numbers are already large and would break the layout.
 */
export const MAX_FONT_SCALE: Record<keyof typeof sizes, number> = { small: 2, body: 2, data: 1.6, title: 1.3, stop: 1.3 };

export function Txt({ children, size = 'body', bold, dim, color, style, lines, fit }: TxtProps) {
  const { palette } = useTheme();
  const px = useLayout().sizes[size];
  return (
    <Text
      numberOfLines={lines}
      adjustsFontSizeToFit={fit}
      minimumFontScale={0.7}
      maxFontSizeMultiplier={MAX_FONT_SCALE[size]}
      style={[
        {
          color: color ?? (dim ? palette.ink2 : palette.ink),
          fontFamily: bold ? fonts.bold : fonts.text,
          fontWeight: bold ? '700' : '400',
          fontSize: px,
          lineHeight: Math.round(px * (size === 'stop' || size === 'title' ? 1.05 : 1.3)),
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

/** A text field: same corners, border and size as the rest, and the same cap on the system font size. */
export function Field({ style, ...rest }: TextInputProps) {
  const { palette } = useTheme();
  const { sizes: text, phone } = useLayout();
  return (
    <TextInput
      placeholderTextColor={palette.ink2}
      maxFontSizeMultiplier={MAX_FONT_SCALE.body}
      {...rest}
      style={[
        {
          minHeight: phone ? 52 : 64,
          paddingHorizontal: space[4],
          borderWidth: border.thin,
          ...shape.control,
          fontFamily: fonts.text,
          fontSize: text.body,
          color: palette.ink,
          backgroundColor: palette.field,
          borderColor: palette.ink2,
        },
        style,
      ]}
    />
  );
}

type PressProps = Omit<PressableProps, 'style'> & { style?: StyleProp<ViewStyle> };

/**
 * A pressable row, chip or button that answers at once when the finger goes down: a small shrink, not
 * an animation (these are touched tens of times a day). `Action` does the same at 0.97 for big buttons.
 */
export function Press({ style, disabled, ...rest }: PressProps) {
  return (
    <Pressable
      {...rest}
      disabled={disabled}
      style={({ pressed }) => [style, pressed && !disabled && styles.pressedRow]}
    />
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
  const { hit, phone } = useLayout();
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
        { minHeight: hit, paddingHorizontal: phone ? 14 : 20 },
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
          health === 'sending' && { backgroundColor: color, borderRadius: border.round },
          health === 'waiting' && { borderWidth: border.mark, borderColor: color, borderRadius: border.round },
          health === 'saving' && { backgroundColor: color, borderRadius: 2 },
          health === 'off' && { backgroundColor: color, borderRadius: 2, transform: [{ rotate: '45deg' }] },
        ]}
      />
      <Txt bold size="small" color={color} lines={1}>
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
  /** Title and hint on one row: for screens with little height. */
  inline?: boolean;
};

const SOS_HOLD_MS = 1500;
/** The fill empties fast when the finger lifts: slow where the driver decides, quick where the system answers. */
const SOS_RELEASE_MS = 200;
const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

/**
 * Press and hold 1.5 s: a bump of the road cannot send an SOS by accident. The fill is a transform
 * (scaleX) run natively, so a busy JS thread (map, GPS) cannot make it stutter. With "reduce motion"
 * the fill appears at once as a state instead of travelling; the 1.5 s is still required.
 */
export function SosButton({ onFire, title, hint, holding, status, inline }: SosProps) {
  const { palette } = useTheme();
  const { hit } = useLayout();
  const [progress] = useState(() => new Animated.Value(0));
  const [pressing, setPressing] = useState(false);
  const [reduce, setReduce] = useState(false);
  const native = Platform.OS !== 'web';

  const fire = useRef(onFire);
  const hold = useRef<Hold | null>(null);
  useEffect(() => {
    fire.current = onFire;
  }, [onFire]);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduce).catch(() => undefined);
  }, []);

  useEffect(() => {
    const current = createHold(SOS_HOLD_MS, () => {
      setPressing(false);
      progress.setValue(0);
      hapticCommit();
      fire.current();
    });
    hold.current = current;
    return () => current.cancel();
  }, [progress]);

  function start() {
    setPressing(true);
    hold.current?.start();
    if (reduce) {
      progress.setValue(1);
      return;
    }
    Animated.timing(progress, {
      toValue: 1,
      duration: SOS_HOLD_MS,
      easing: Easing.linear,
      useNativeDriver: native,
    }).start();
  }

  function cancel() {
    const wasHolding = hold.current?.active ?? false;
    hold.current?.cancel();
    setPressing(false);
    progress.stopAnimation();
    if (!wasHolding) return; // it already fired: the fire reset the fill
    Animated.timing(progress, {
      toValue: 0,
      duration: reduce ? 0 : SOS_RELEASE_MS,
      easing: EASE_OUT,
      useNativeDriver: native,
    }).start();
  }

  return (
    <Pressable
      onPressIn={start}
      onPressOut={cancel}
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${hint}`}
      accessibilityActions={[{ name: 'activate', label: title }]}
      onAccessibilityAction={() => {
        hapticCommit();
        onFire();
      }}
      style={[
        styles.action,
        styles.sos,
        inline && styles.sosInline,
        { minHeight: hit, backgroundColor: palette.danger, borderColor: palette.danger },
      ]}
    >
      <Animated.View
        style={[
          styles.sosFill,
          { backgroundColor: palette.onDanger, opacity: reduce ? 0.18 : 0.25, transform: [{ scaleX: progress }] },
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
  screen: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  pressedRow: {
    transform: [{ scale: 0.98 }],
    opacity: 0.9,
  },
  action: {
    minHeight: HIT,
    paddingHorizontal: space[5],
    paddingVertical: space[3],
    ...shape.control,
    borderWidth: border.thin,
    justifyContent: 'center',
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[2],
    flexShrink: 1,
  },
  badgeMark: {
    width: 18,
    height: 18,
  },
  sos: {
    overflow: 'hidden',
  },
  sosInline: {
    paddingVertical: space[1],
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    columnGap: space[3],
  },
  sosFill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    right: 0,
    // grows from the left edge: scaleX alone would grow from the middle
    transformOrigin: 'left',
  },
});
