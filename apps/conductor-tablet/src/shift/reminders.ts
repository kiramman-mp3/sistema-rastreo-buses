import type { UpcomingTrip } from '../api/types';
import { t, tf } from '../i18n';

/** Minutes before a planned trip at which the driver gets the first reminder. */
export const LEAD_MIN = 10;
export const CHANNEL_ID = 'trip-reminders';
const PREFIX = 'trip-';

function clock(iso: string): string {
  const when = new Date(iso);
  return `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`;
}

export type Reminder = {
  /** Stable per trip and kind: the same trip is never reminded twice when the list is synced again. */
  id: string;
  kind: 'soon' | 'start';
  at: Date;
  trip: UpcomingTrip;
};

/** The reminders still ahead for these trips: LEAD_MIN minutes before the start, and at the start. */
export function planReminders(trips: UpcomingTrip[], now: Date, leadMin = LEAD_MIN): Reminder[] {
  const out: Reminder[] = [];
  for (const trip of trips) {
    const start = new Date(trip.planned_start);
    if (Number.isNaN(start.getTime())) continue;
    const soon = new Date(start.getTime() - leadMin * 60_000);
    if (soon > now) out.push({ id: `${PREFIX}${trip.id}-soon`, kind: 'soon', at: soon, trip });
    if (start > now) out.push({ id: `${PREFIX}${trip.id}-start`, kind: 'start', at: start, trip });
  }
  return out.sort((a, b) => a.at.getTime() - b.at.getTime());
}

export function reminderText(reminder: Reminder): { title: string; body: string } {
  const values = {
    route: reminder.trip.route_code || reminder.trip.route_name,
    bus: reminder.trip.vehicle_name,
    time: clock(reminder.trip.planned_start),
  };
  return reminder.kind === 'soon'
    ? { title: t('reminderSoonTitle'), body: tf('reminderSoonBody', values) }
    : { title: t('reminderStartTitle'), body: tf('reminderStartBody', values) };
}

/** What the session needs: the native side is behind this, so the session tests run without it. */
export type TripReminders = {
  sync(trips: UpcomingTrip[]): Promise<void>;
  clear(): Promise<void>;
};

type NotificationsModule = typeof import('expo-notifications');

/** Local notifications scheduled on the tablet: they ring without signal and with the app closed. */
export function createTripReminders(load: () => Promise<NotificationsModule> = () => import('expo-notifications')): TripReminders {
  let ready: Promise<NotificationsModule | null> | null = null;

  function setup() {
    ready ??= (async () => {
      try {
        const N = await load();
        N.setNotificationHandler({
          handleNotification: async () => ({
            shouldShowBanner: true,
            shouldShowList: true,
            shouldPlaySound: true,
            shouldSetBadge: false,
          }),
        });
        // Android 13 only asks for the permission once a channel exists.
        await N.setNotificationChannelAsync(CHANNEL_ID, {
          name: t('reminderChannel'),
          importance: N.AndroidImportance.HIGH,
        });
        const current = await N.getPermissionsAsync();
        if (!current.granted && current.canAskAgain) await N.requestPermissionsAsync();
        return N;
      } catch {
        // No notifications on this device (web, denied): the shift screen still works.
        ready = null;
        return null;
      }
    })();
    return ready;
  }

  async function ours(N: NotificationsModule) {
    const scheduled = await N.getAllScheduledNotificationsAsync();
    return scheduled.map((item) => item.identifier).filter((id) => id.startsWith(PREFIX));
  }

  return {
    async sync(trips) {
      const N = await setup();
      if (!N) return;
      try {
        // Start over each time: a trip moved, cancelled or given to another driver loses its reminders.
        await Promise.all((await ours(N)).map((id) => N.cancelScheduledNotificationAsync(id)));
        for (const reminder of planReminders(trips, new Date())) {
          await N.scheduleNotificationAsync({
            identifier: reminder.id,
            content: { ...reminderText(reminder), sound: true, data: { tripId: reminder.trip.id } },
            trigger: { type: N.SchedulableTriggerInputTypes.DATE, date: reminder.at, channelId: CHANNEL_ID },
          });
        }
      } catch {
        // A failed reminder must never break the sign-in.
      }
    },
    async clear() {
      const N = await setup();
      if (!N) return;
      try {
        await Promise.all((await ours(N)).map((id) => N.cancelScheduledNotificationAsync(id)));
      } catch {
        // Nothing else to do.
      }
    },
  };
}
