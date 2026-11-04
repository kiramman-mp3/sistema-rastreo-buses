import { stopWindow, type StopView } from './progress';

function stops(next: number, total = 7): StopView[] {
  return Array.from({ length: total }, (_, i) => ({
    id: i + 1,
    name: `P${i + 1}`,
    sequence: i,
    arrivedAt: null,
    plannedAt: null,
    delayMin: null,
    status: i < next ? 'arrived' : i === next ? 'next' : 'later',
  }));
}

describe('stop window', () => {
  test('shows the next stop and the three after it', () => {
    expect(stopWindow(stops(2)).map((s) => s.name)).toEqual(['P3', 'P4', 'P5', 'P6']);
  });

  test('near the end it shows what is left', () => {
    expect(stopWindow(stops(5)).map((s) => s.name)).toEqual(['P6', 'P7']);
  });

  test('when the route is done it shows the last stops', () => {
    expect(stopWindow(stops(7)).map((s) => s.name)).toEqual(['P4', 'P5', 'P6', 'P7']);
  });
});
