import { Platform } from 'react-native';
import * as Location from 'expo-location';
import * as IntentLauncher from 'expo-intent-launcher';

import { GpsPermissionError } from './types';

const PACKAGE = 'ec.edu.uta.buses.conductor';

export async function requestGpsPermissions() {
  const foreground = await Location.requestForegroundPermissionsAsync();
  if (foreground.status !== 'granted') throw new GpsPermissionError();
  const background = await Location.requestBackgroundPermissionsAsync();
  if (background.status !== 'granted') throw new GpsPermissionError();
}

export async function requestBatteryExemption() {
  if (Platform.OS !== 'android') return;
  try {
    await IntentLauncher.startActivityAsync('android.settings.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS', {
      data: `package:${PACKAGE}`,
    });
  } catch {
    // The driver can dismiss the system sheet; tracking still starts.
  }
}

export async function gpsPermissionSnapshot() {
  const foreground = await Location.getForegroundPermissionsAsync();
  const background = await Location.getBackgroundPermissionsAsync();
  return {
    foreground: foreground.status,
    background: background.status,
  };
}
