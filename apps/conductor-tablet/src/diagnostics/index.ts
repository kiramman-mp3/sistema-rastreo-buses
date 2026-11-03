import Constants from 'expo-constants';

import { gpsKv } from '../gps/store';
import { ErrorQueue } from './queue';

/** The one queue of the app: the global handler fills it and the session empties it. */
export const errorQueue = new ErrorQueue(gpsKv);

export const appVersion: string = Constants.expoConfig?.version ?? 'dev';
