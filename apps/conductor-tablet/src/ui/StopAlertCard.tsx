import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, Vibration, View } from 'react-native';
import { cockpitColors, cockpitHit } from './theme';

export type StopItem = {
  id: number;
  name: string;
  sequence?: number;
};

export type StopAlertCardProps = {
  immediateStop: StopItem | null;
  subsequentStops: StopItem[];
  distanceFormatted?: string;
  onConfirmArrival?: () => void;
  arrived?: boolean;
};

export const StopAlertCard = React.memo(function StopAlertCard({
  immediateStop,
  subsequentStops,
  distanceFormatted = 'En trayecto',
  onConfirmArrival,
  arrived = false,
}: StopAlertCardProps) {
  const [pressed, setPressed] = useState(false);

  function handlePress() {
    Vibration.vibrate(60);
    if (onConfirmArrival) {
      onConfirmArrival();
    }
  }

  return (
    <View style={styles.cardContainer}>
      {/* High-Impact Immediate Stop Section */}
      <View style={styles.immediateSection}>
        <View style={styles.tagRow}>
          <View style={styles.kickerTag}>
            <Text style={styles.kickerText}>PRÓXIMA PARADA</Text>
          </View>
          {distanceFormatted ? (
            <View style={styles.distancePill}>
              <Text style={styles.distanceText}>📍 {distanceFormatted}</Text>
            </View>
          ) : null}
        </View>

        <Text
          style={styles.stopNameHero}
          numberOfLines={2}
          adjustsFontSizeToFit
          accessibilityRole="header"
        >
          {immediateStop ? immediateStop.name : 'Fin del recorrido'}
        </Text>

        {immediateStop && onConfirmArrival ? (
          <Pressable
            onPress={handlePress}
            onPressIn={() => setPressed(true)}
            onPressOut={() => setPressed(false)}
            style={[
              styles.arrivalBtn,
              pressed && styles.arrivalBtnPressed,
              arrived && styles.arrivalBtnDone,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Confirmar arribo a parada"
          >
            <Text style={styles.arrivalBtnIcon}>{arrived ? '✓' : '🚏'}</Text>
            <Text style={styles.arrivalBtnText}>
              {arrived ? 'PARADA CONFIRMADA' : 'CONFIRMAR ARRIBO (TOQUE)'}
            </Text>
          </Pressable>
        ) : null}
      </View>

      {/* Subsequent 2 Stops Preview */}
      {subsequentStops.length > 0 ? (
        <View style={styles.subsequentSection}>
          <Text style={styles.subsequentHeader}>SIGUIENTES PARADAS:</Text>
          <View style={styles.subsequentList}>
            {subsequentStops.slice(0, 2).map((stop, idx) => (
              <View key={stop.id} style={styles.subsequentRow}>
                <View style={styles.subsequentBullet}>
                  <Text style={styles.bulletText}>{idx + 2}</Text>
                </View>
                <Text style={styles.subsequentName} numberOfLines={1}>
                  {stop.name}
                </Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
});

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: cockpitColors.surface,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: cockpitColors.surfaceBorder,
    overflow: 'hidden',
  },
  immediateSection: {
    padding: 18,
    gap: 10,
  },
  tagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  kickerTag: {
    backgroundColor: 'rgba(217, 119, 6, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(217, 119, 6, 0.4)',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 6,
  },
  kickerText: {
    color: '#F59E0B',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  distancePill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  distanceText: {
    color: '#34D399',
    fontSize: 14,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  stopNameHero: {
    color: cockpitColors.textBright,
    fontSize: 34,
    fontWeight: '900',
    letterSpacing: -0.5,
    lineHeight: 40,
    minHeight: 80,
  },
  arrivalBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: cockpitColors.brandUTA,
    minHeight: cockpitHit, // 72px ergonomic target
    borderRadius: 14,
    paddingHorizontal: 20,
    borderWidth: 1.5,
    borderColor: '#B91C1C',
  },
  arrivalBtnPressed: {
    transform: [{ scale: 0.97 }],
    backgroundColor: '#701A1E',
  },
  arrivalBtnDone: {
    backgroundColor: '#064E3B',
    borderColor: '#059669',
  },
  arrivalBtnIcon: {
    fontSize: 22,
    color: '#FFFFFF',
  },
  arrivalBtnText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  subsequentSection: {
    backgroundColor: 'rgba(0, 0, 0, 0.25)',
    borderTopWidth: 1,
    borderTopColor: cockpitColors.surfaceBorder,
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  subsequentHeader: {
    color: cockpitColors.textDim,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  subsequentList: {
    gap: 8,
  },
  subsequentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  subsequentBullet: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: cockpitColors.surfaceElevated,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: cockpitColors.surfaceBorder,
  },
  bulletText: {
    color: cockpitColors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  subsequentName: {
    flex: 1,
    color: cockpitColors.textMuted,
    fontSize: 16,
    fontWeight: '600',
  },
});
