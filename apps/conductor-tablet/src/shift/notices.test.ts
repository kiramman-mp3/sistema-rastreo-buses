import { buildNotices, pickNotices } from './notices';

const alerts = [
  { id: 1, title: 'Fuera de ruta', detail: 'A 300 m de su ruta' },
  { id: 2, title: 'Exceso de velocidad', detail: '' },
];
const unseen = { text: 'SOS enviado', seen: false, id: '9', delivered: true };
const seen = { text: 'Visto por Central', seen: true, id: '9', delivered: true };

describe('cabin notices', () => {
  test('an SOS nobody has seen comes before any alert', () => {
    const items = buildNotices({ sos: unseen, alerts });
    expect(items.map((i) => i.key)).toEqual(['sos', 'alert-1', 'alert-2']);
    expect(items[0]).toMatchObject({ tone: 'danger', live: 'assertive' });
  });

  test('an SOS the office has seen is good news, not danger, and waits behind the open alerts', () => {
    const [only] = buildNotices({ sos: seen, alerts: [] });
    expect(only.tone).toBe('ok');
    const items = buildNotices({ sos: seen, alerts });
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
    const items = buildNotices({ sos: unseen, alerts });
    const picked = pickNotices(items, 2);
    expect(picked.shown.map((i) => i.key)).toEqual(['sos', 'alert-1']);
    expect(picked.hidden).toBe(1);
  });

  test('there is always room for at least one notice', () => {
    const items = buildNotices({ sos: null, alerts });
    expect(pickNotices(items, 0).shown).toHaveLength(1);
    expect(pickNotices(items, 0).hidden).toBe(1);
  });

  test('a closed alert is gone, a new alert with another id shows', () => {
    const closed = new Set(['alert-1']);
    expect(buildNotices({ sos: null, alerts, dismissed: closed }).map((i) => i.key)).toEqual(['alert-2']);
    const later = [...alerts, { id: 3, title: 'Parada larga', detail: '' }];
    expect(buildNotices({ sos: null, alerts: later, dismissed: closed }).map((i) => i.key)).toEqual([
      'alert-2',
      'alert-3',
    ]);
  });

  test('every alert can be closed', () => {
    const items = buildNotices({ sos: null, alerts });
    expect(items.every((i) => i.dismissible && i.dismissKey?.startsWith('alert-'))).toBe(true);
  });

  test('an SOS can be closed only once the office has it', () => {
    const waiting = { text: 'Enviando SOS…', seen: false, id: 'local', delivered: false };
    // closing is refused while it is not delivered: the notice stays even if it was marked closed
    const [pending] = buildNotices({ sos: waiting, alerts: [], dismissed: new Set(['sos-local']) });
    expect(pending.dismissible).toBe(false);
    expect(buildNotices({ sos: unseen, alerts: [] })[0].dismissible).toBe(true);
    expect(buildNotices({ sos: unseen, alerts: [], dismissed: new Set(['sos-9']) })).toEqual([]);
    // a second SOS has another id and shows again
    expect(buildNotices({ sos: { ...unseen, id: '10' }, alerts: [], dismissed: new Set(['sos-9']) })).toHaveLength(1);
  });
});
