import * as TaskManager from 'expo-task-manager';
import type * as Location from 'expo-location';

import { GPS_TASK, runLocationTask } from './tracker';

TaskManager.defineTask(GPS_TASK, async ({ data, error }) => {
  if (error || !data) return;
  const { locations } = data as { locations?: Location.LocationObject[] };
  if (!locations?.length) return;
  await runLocationTask(locations);
});
