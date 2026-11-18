import { createTripReminders, planReminders, reminderText } from './reminders';
import type { UpcomingTrip } from '../api/types';
import { setLang } from '../i18n';

const NOW = new Date('2026-11-18T12:00:00Z');

function trip(id: number, minutesFromNow: number): UpcomingTrip {
  return {
    id,
    planned_start: new Date(NOW.getTime() + minutesFromNow * 60_000).toISOString(),
    route_id: 1,
    route_code: 'L1',
    route_name: 'Línea Centro',
    vehicle_id: 3,
    vehicle_name: 'Bus 3',
  };
}

describe('planReminders', () => {
  it('reminds 10 minutes before and at the start, soonest first', () => {
    const plan = planReminders([trip(2, 120), trip(1, 30)], NOW);
    expect(plan.map((r) => r.id)).toEqual(['trip-1-soon', 'trip-1-start', 'trip-2-soon', 'trip-2-start']);
    expect(plan[0].at.getTime()).toBe(NOW.getTime() + 20 * 60_000);
  });

  it('skips the reminders already past', () => {
    expect(planReminders([trip(1, 5)], NOW).map((r) => r.kind)).toEqual(['start']);
    expect(planReminders([trip(1, -1)], NOW)).toEqual([]);
  });

  it('ignores a trip without a valid time', () => {
    expect(planReminders([{ ...trip(1, 30), planned_start: 'nope' }], NOW)).toEqual([]);
  });
});

describe('reminderText', () => {
  it('says what the driver asked for, in the language of the app', () => {
    setLang('es');
    const [soon, start] = planReminders([trip(1, 30)], NOW);
    expect(reminderText(soon).title).toBe('En 10 minutos tienes un recorrido');
    expect(reminderText(soon).body).toContain('Prepárate');
    expect(reminderText(start).title).toBe('Inicia tu recorrido programado');
    expect(reminderText(start).body).toContain('L1');
  });
});

describe('createTripReminders', () => {
  function fakeNotifications(existing: string[] = []) {
    const scheduled: { identifier: string }[] = existing.map((identifier) => ({ identifier }));
    const api = {
      setNotificationHandler: jest.fn(),
      setNotificationChannelAsync: jest.fn(async () => null),
      getPermissionsAsync: jest.fn(async () => ({ granted: true, canAskAgain: true })),
      requestPermissionsAsync: jest.fn(),
      AndroidImportance: { HIGH: 6 },
      SchedulableTriggerInputTypes: { DATE: 'date' },
      getAllScheduledNotificationsAsync: jest.fn(async () => scheduled.slice()),
      cancelScheduledNotificationAsync: jest.fn(async (id: string) => {
        scheduled.splice(scheduled.findIndex((s) => s.identifier === id), 1);
      }),
      scheduleNotificationAsync: jest.fn(async (request: { identifier: string }) => {
        scheduled.push({ identifier: request.identifier });
        return request.identifier;
      }),
    };
    return { api, scheduled };
  }

  it('replaces the reminders of this app and leaves the others alone', async () => {
    const { api, scheduled } = fakeNotifications(['trip-99-soon', 'other-app-thing']);
    const reminders = createTripReminders(async () => api as never);
    const soon = new Date(Date.now() + 60 * 60_000).toISOString();
    await reminders.sync([{ ...trip(1, 0), planned_start: soon }]);
    expect(scheduled.map((s) => s.identifier).sort()).toEqual(['other-app-thing', 'trip-1-soon', 'trip-1-start']);
    await reminders.clear();
    expect(scheduled.map((s) => s.identifier)).toEqual(['other-app-thing']);
  });

  it('never throws when the device has no notifications', async () => {
    const reminders = createTripReminders(async () => {
      throw new Error('not available');
    });
    await expect(reminders.sync([trip(1, 30)])).resolves.toBeUndefined();
    await expect(reminders.clear()).resolves.toBeUndefined();
  });
});
