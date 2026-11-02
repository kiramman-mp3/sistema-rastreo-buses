import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { cockpitColors } from './theme';

export type HeadwayStatus = 'on_time' | 'ahead' | 'delayed';

export type HeadwayBarProps = {
  status?: HeadwayStatus;
  diffMinutes?: number;
  leadBusName?: string;
  targetIntervalMins?: number;
};

export const HeadwayBar = React.memo(function HeadwayBar({
  status = 'on_time',
  diffMinutes = 1,
  leadBusName = 'Bus #02',
  targetIntervalMins = 8,
}: HeadwayBarProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.timing(pulseAnim, {
        toValue: 1.03,
        duration: 180,
        useNativeDriver: true,
      }),
      Animated.spring(pulseAnim, {
        toValue: 1,
        friction: 5,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();
  }, [status, diffMinutes, pulseAnim]);

  const config = {
    on_time: {
      bg: cockpitColors.onTimeBg,
      border: cockpitColors.onTimeBorder,
      text: '#A7F3D0',
      badge: '✓',
      label: 'A TIEMPO',
      deltaText: diffMinutes >= 0 ? `+${diffMinutes} MIN` : `${diffMinutes} MIN`,
      hint: `Intervalo óptimo de ${targetIntervalMins} min con ${leadBusName}`,
    },
    ahead: {
      bg: cockpitColors.aheadBg,
      border: cockpitColors.aheadBorder,
      text: '#FDE68A',
      badge: '⏳',
      label: 'ADELANTADO · BAJA EL PASO',
      deltaText: `${diffMinutes} MIN`,
      hint: `Estás muy cerca de ${leadBusName} (intervalo menor a ${targetIntervalMins} min)`,
    },
    delayed: {
      bg: cockpitColors.delayedBg,
      border: cockpitColors.delayedBorder,
      text: '#FECACA',
      badge: '⚡',
      label: 'RETRASADO · AGILIZA EL PASO',
      deltaText: diffMinutes > 0 ? `+${diffMinutes} MIN` : `${diffMinutes} MIN`,
      hint: `Separación excesiva con ${leadBusName} (+${Math.abs(diffMinutes)} min de demora)`,
    },
  }[status];

  return (
    <Animated.View
      style={[
        styles.container,
        {
          backgroundColor: config.bg,
          borderColor: config.border,
          transform: [{ scale: pulseAnim }],
        },
      ]}
      accessibilityRole="summary"
      accessibilityLabel={`Cadencia: ${config.label}, ${config.deltaText}`}
    >
      <View style={styles.badgeWrap}>
        <Text style={styles.badgeText}>{config.badge}</Text>
      </View>

      <View style={styles.contentWrap}>
        <View style={styles.titleRow}>
          <Text style={[styles.statusTitle, { color: config.text }]}>
            {config.label}
          </Text>
          <View style={styles.deltaPill}>
            <Text style={styles.deltaText}>{config.deltaText}</Text>
          </View>
        </View>
        <Text style={styles.hintText} numberOfLines={1}>
          {config.hint}
        </Text>
      </View>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 16,
    borderWidth: 2,
    minHeight: 74,
    gap: 14,
  },
  badgeWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    fontSize: 24,
  },
  contentWrap: {
    flex: 1,
    justifyContent: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  statusTitle: {
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  deltaPill: {
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  deltaText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  hintText: {
    color: cockpitColors.textMuted,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 2,
  },
});
