import * as Battery from 'expo-battery';
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';

import { requestBatteryExemption, requestGpsPermissions } from './permissions';
import { flushFixes, ingestLocations } from './runtime';
import { gpsStore, locationQueue, writeLastError, writeLastSample, writeLastSent } from './store';
import { t } from '../i18n';
import type { GpsController } from './types';

export const GPS_TASK = 'uta-bus-location';

let foregroundWatcher: Location.LocationSubscription | null = null;

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
    if (foregroundWatcher) {
      foregroundWatcher.remove();
      foregroundWatcher = null;
    }
    try {
      const running = await Location.hasStartedLocationUpdatesAsync(GPS_TASK);
      if (running) await Location.stopLocationUpdatesAsync(GPS_TASK);
      await Location.startLocationUpdatesAsync(GPS_TASK, {
        accuracy: Location.Accuracy.High,
        timeInterval: 10_000,
        distanceInterval: 0,
        deferredUpdatesInterval: 10_000,
        pausesUpdatesAutomatically: false,
        foregroundService: {
          notificationTitle: t('gpsServiceTitle'),
          notificationBody: t('gpsServiceBody'),
          notificationColor: '#B91C1C',
          killServiceOnDestroy: false,
        },
      });
    } catch {
      // In Expo Go on iOS or environments where background task manager is not supported,
      // fallback to foreground watchPositionAsync so positions are actively sent.
      try {
        foregroundWatcher = await Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.High,
            timeInterval: 10_000,
            distanceInterval: 0,
          },
          (location) => {
            void runLocationTask([location]);
          },
        );
      } catch {
        // Handled by permission snapshot & health view
      }
    }
  },
  async stop() {
    if (foregroundWatcher) {
      foregroundWatcher.remove();
      foregroundWatcher = null;
    }
    const registered = await TaskManager.isTaskRegisteredAsync(GPS_TASK);
    if (registered) {
      try {
        await Location.stopLocationUpdatesAsync(GPS_TASK);
      } catch {
        // Already stopped after process death.
      }
    }
    // Last chance for the points saved without signal; whatever does not go now is dropped.
    const creds = await gpsStore.get();
    await locationQueue.exclusive(async () => {
      if (creds) {
        try {
          await flushFixes(locationQueue, creds);
        } catch {
          // Ending the shift never waits on the network.
        }
      }
      await locationQueue.clear();
    });
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
    onSample: writeLastSample,
    onError: writeLastError,
  });
}
