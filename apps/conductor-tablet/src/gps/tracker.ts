import * as Battery from 'expo-battery';
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';

import { requestBatteryExemption, requestGpsPermissions } from './permissions';
import { ingestLocations } from './runtime';
import { gpsStore, locationQueue, writeLastSent } from './store';
import type { GpsController } from './types';

export const GPS_TASK = 'uta-bus-location';

async function batteryPercent(): Promise<number | null> {
  try {
    const level = await Battery.getBatteryLevelAsync();
    if (level < 0) return null;
    return Math.round(level * 100);
  } catch {
    return null;
  }
}

export const liveGps: GpsController = {
  async prepare() {
    await requestGpsPermissions();
    await requestBatteryExemption();
  },
  async start(uniqueId, url) {
    await gpsStore.set({ uniqueId, url });
    const running = await Location.hasStartedLocationUpdatesAsync(GPS_TASK);
    if (running) await Location.stopLocationUpdatesAsync(GPS_TASK);
    await Location.startLocationUpdatesAsync(GPS_TASK, {
      accuracy: Location.Accuracy.High,
      timeInterval: 10_000,
      distanceInterval: 0,
      deferredUpdatesInterval: 10_000,
      pausesUpdatesAutomatically: false,
      foregroundService: {
        notificationTitle: 'Buses UTA',
        notificationBody: 'Enviando la posición del bus',
        notificationColor: '#B91C1C',
        killServiceOnDestroy: false,
      },
    });
  },
  async stop() {
    const registered = await TaskManager.isTaskRegisteredAsync(GPS_TASK);
    if (registered) {
      try {
        await Location.stopLocationUpdatesAsync(GPS_TASK);
      } catch {
        // Already stopped after process death.
      }
    }
    await locationQueue.clear();
    await gpsStore.clear();
  },
};

export async function runLocationTask(locations: Location.LocationObject[]) {
  const creds = await gpsStore.get();
  if (!creds) return;
  await ingestLocations(locations, {
    queue: locationQueue,
    creds,
    battery: batteryPercent,
    onSent: writeLastSent,
  });
}
