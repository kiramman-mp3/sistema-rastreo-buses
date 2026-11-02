import { classifyStops, clock, sosPhase } from './progress';

const stops = [
  { id: 3, name: 'Terminal', sequence: 30, arrived_at: null },
  { id: 1, name: 'Hospital', sequence: 10, arrived_at: '2026-10-30T15:04:00Z' },
  { id: 2, name: 'Mercado', sequence: 20, arrived_at: null },
];

describe('stop progress', () => {
  test('marks arrived stops and highlights the next one in route order', () => {
    const view = classifyStops(stops, 2);
    expect(view.map((stop) => stop.name)).toEqual(['Hospital', 'Mercado', 'Terminal']);
    expect(view[0].status).toBe('arrived');
    expect(view[0].arrivedAt).toBe('2026-10-30T15:04:00Z');
    expect(view[1].status).toBe('next');
    expect(view[2].status).toBe('later');
  });

  test('has no next stop when the route is finished', () => {
    const done = stops.map((stop) => ({ ...stop, arrived_at: '2026-10-30T16:00:00Z' }));
    expect(classifyStops(done, null).every((stop) => stop.status === 'arrived')).toBe(true);
  });

  test('shows the UTC clock from the arrival stamp', () => {
    expect(clock('2026-10-30T15:04:00Z')).toBe('15:04');
  });

  test('walks the stops backwards on the way back', () => {
    const view = classifyStops(stops, 2, 'back');
    expect(view.map((stop) => stop.name)).toEqual(['Terminal', 'Mercado', 'Hospital']);
    expect(view[1].status).toBe('next');
  });
});

describe('sos phase', () => {
  const at = '2026-10-30T15:00:00.000Z';
  const delivered = { id: 1, sent_at: '2026-10-30T15:00:00Z', seen_at: null, seen_by: null };

  test('the server wins once it has the sos the driver pressed', () => {
    expect(sosPhase(delivered, { status: 'queued', at })).toBe('sent');
    expect(sosPhase({ ...delivered, seen_at: '2026-10-30T15:02:00Z', seen_by: 'Ana' }, { status: 'queued', at })).toBe('seen');
  });

  test('an older sos on the server does not hide a new one still queued', () => {
    const older = { ...delivered, sent_at: '2026-10-30T14:00:00Z', seen_at: '2026-10-30T14:01:00Z' };
    expect(sosPhase(older, { status: 'queued', at })).toBe('queued');
  });

  test('without a local press the server state is shown', () => {
    expect(sosPhase(delivered, null)).toBe('sent');
    expect(sosPhase(null, null)).toBeNull();
    expect(sosPhase(null, { status: 'sending', at })).toBe('sending');
  });
});
