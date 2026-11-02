import React, { useRef, useState } from 'react';
import {
  Animated,
  Pressable,
  StyleSheet,
  Text,
  Vibration,
  View,
} from 'react-native';
import { cockpitColors, cockpitHit } from './theme';

export type IncidentActionsProps = {
  onReportTraffic: () => void;
  onTriggerSOS: () => void;
  trafficLoading?: boolean;
};

export const IncidentActions = React.memo(function IncidentActions({
  onReportTraffic,
  onTriggerSOS,
  trafficLoading = false,
}: IncidentActionsProps) {
  const [trafficPressed, setTrafficPressed] = useState(false);
  const [sosHolding, setSosHolding] = useState(false);
  const [sosFired, setSosFired] = useState(false);

  const holdAnim = useRef(new Animated.Value(0)).current;
  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleTrafficPress() {
    Vibration.vibrate(60);
    onReportTraffic();
  }

  function handleSosPressIn() {
    if (sosFired) return;
    setSosHolding(true);
    Vibration.vibrate(40);

    Animated.timing(holdAnim, {
      toValue: 1,
      duration: 1500, // 1.5s hold requirement
      useNativeDriver: false,
    }).start(({ finished }) => {
      if (finished) {
        setSosFired(true);
        Vibration.vibrate([0, 100, 60, 250]);
        onTriggerSOS();
      }
    });
  }

  function handleSosPressOut() {
    if (!sosFired) {
      setSosHolding(false);
      holdAnim.stopAnimation();
      holdAnim.setValue(0);
      if (holdTimerRef.current) {
        clearTimeout(holdTimerRef.current);
      }
    }
  }

  const fillWidth = holdAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={styles.container}>
      {/* Button 1: Quick 1-Tap Traffic / Congestion Report */}
      <Pressable
        onPress={handleTrafficPress}
        onPressIn={() => setTrafficPressed(true)}
        onPressOut={() => setTrafficPressed(false)}
        style={[
          styles.actionBtn,
          styles.trafficBtn,
          trafficPressed && styles.btnActive,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Reportar demora por congestión o tráfico vial"
      >
        <Text style={styles.iconTraffic}>⚠️</Text>
        <View style={styles.btnTextWrap}>
          <Text style={styles.btnTitleTraffic}>
            {trafficLoading ? 'ENVIANDO...' : 'REPORTAR TRÁFICO'}
          </Text>
          <Text style={styles.btnSub}>Demora en ruta (1 toque)</Text>
        </View>
      </Pressable>

      {/* Button 2: Hold 1.5s SOS Emergency Button */}
      <Pressable
        onPressIn={handleSosPressIn}
        onPressOut={handleSosPressOut}
        style={[
          styles.actionBtn,
          styles.sosBtn,
          sosHolding && styles.btnActive,
          sosFired && styles.sosFiredBtn,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Botón de emergencia SOS. Mantén presionado un segundo y medio para activar."
      >
        {/* Animated Hold Fill Bar */}
        <Animated.View style={[styles.sosFillBar, { width: fillWidth }]} />

        <View style={styles.sosContentRow}>
          <Text style={styles.iconSos}>🚨</Text>
          <View style={styles.btnTextWrap}>
            <Text style={styles.btnTitleSos}>
              {sosFired
                ? '¡ALERTA SOS ENVIADA!'
                : sosHolding
                ? 'MANTÉN PRESIONADO...'
                : 'ALERTA / SOS'}
            </Text>
            <Text style={styles.btnSubSos}>
              {sosFired ? 'Central notificada' : 'Mantén presionado 1.5s'}
            </Text>
          </View>
        </View>
      </Pressable>
    </View>
  );
});

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    gap: 12,
  },
  actionBtn: {
    flex: 1,
    minHeight: cockpitHit, // 72px ergonomic touch target
    borderRadius: 16,
    borderWidth: 2,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    gap: 12,
    overflow: 'hidden',
    position: 'relative',
  },
  btnActive: {
    transform: [{ scale: 0.97 }],
  },
  btnTextWrap: {
    flex: 1,
    justifyContent: 'center',
  },
  trafficBtn: {
    backgroundColor: '#261C08',
    borderColor: cockpitColors.actionTraffic,
  },
  iconTraffic: {
    fontSize: 26,
  },
  btnTitleTraffic: {
    color: '#FBBF24',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  btnSub: {
    color: cockpitColors.textMuted,
    fontSize: 12,
    fontWeight: '600',
    marginTop: 1,
  },
  sosBtn: {
    backgroundColor: '#2D0F14',
    borderColor: cockpitColors.actionSos,
  },
  sosFiredBtn: {
    backgroundColor: '#7F1D1D',
    borderColor: '#EF4444',
  },
  sosFillBar: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(220, 38, 38, 0.65)',
  },
  sosContentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
    zIndex: 2,
  },
  iconSos: {
    fontSize: 26,
  },
  btnTitleSos: {
    color: '#FECACA',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  btnSubSos: {
    color: '#FCA5A5',
    fontSize: 12,
    fontWeight: '700',
    marginTop: 1,
  },
});
