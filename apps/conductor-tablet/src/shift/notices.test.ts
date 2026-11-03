import { buildNotices, pickNotices } from './notices';

const alerts = [
  { id: 1, title: 'Fuera de ruta', detail: 'A 300 m de su ruta' },
  { id: 2, title: 'Exceso de velocidad', detail: '' },
];

describe('cabin notices', () => {
  test('an SOS nobody has seen comes before any alert', () => {
    const items = buildNotices({ sos: { text: 'SOS enviado', seen: false }, alerts });
    expect(items.map((i) => i.key)).toEqual(['sos', 'alert-1', 'alert-2']);
    expect(items[0]).toMatchObject({ tone: 'danger', live: 'assertive' });
  });

  test('an SOS the office has seen is good news, not danger, and waits behind the open alerts', () => {
    const [only] = buildNotices({ sos: { text: 'Visto por Central', seen: true }, alerts: [] });
    expect(only.tone).toBe('ok');
    const items = buildNotices({ sos: { text: 'Visto por Central', seen: true }, alerts });
    expect(items.map((i) => i.key)).toEqual(['alert-1', 'alert-2', 'sos']);
  });

  test('an alert without detail has no detail line', () => {
    const items = buildNotices({ sos: null, alerts });
    expect(items[0].detail).toBe('A 300 m de su ruta');
    expect(items[1].detail).toBeUndefined();
    expect(items.every((i) => i.live === 'polite')).toBe(true);
  });

  test('nothing to say gives an empty list', () => {
    expect(buildNotices({ sos: null, alerts: [] })).toEqual([]);
    expect(pickNotices([], 2)).toEqual({ shown: [], hidden: 0 });
  });

  test('only the first notices are shown and the rest are counted', () => {
    const items = buildNotices({ sos: { text: 'SOS enviado', seen: false }, alerts });
    const picked = pickNotices(items, 2);
    expect(picked.shown.map((i) => i.key)).toEqual(['sos', 'alert-1']);
    expect(picked.hidden).toBe(1);
  });

  test('there is always room for at least one notice', () => {
    const items = buildNotices({ sos: null, alerts });
    expect(pickNotices(items, 0).shown).toHaveLength(1);
    expect(pickNotices(items, 0).hidden).toBe(1);
  });
});
