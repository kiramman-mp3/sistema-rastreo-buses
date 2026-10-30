import { classifyStops, clock } from './progress';

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
});
