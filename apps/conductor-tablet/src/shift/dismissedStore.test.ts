import { memoryKv } from '../gps/queue';
import { loadDismissed, parseDismissed, saveDismissed } from './dismissedStore';

describe('closed notices', () => {
  test('nothing stored, nonsense stored: an empty list', () => {
    expect(parseDismissed(null)).toEqual([]);
    expect(parseDismissed('not json')).toEqual([]);
    expect(parseDismissed('{"a":1}')).toEqual([]);
    expect(parseDismissed('["alert-1", 2, null, "sos-5"]')).toEqual(['alert-1', 'sos-5']);
  });

  test('what was closed on a shift comes back for that shift only', async () => {
    const kv = memoryKv();
    await saveDismissed(7, ['alert-1', 'alert-2'], kv);
    expect(await loadDismissed(7, kv)).toEqual(['alert-1', 'alert-2']);
    expect(await loadDismissed(8, kv)).toEqual([]);
  });

  test('only the latest ones are kept', async () => {
    const kv = memoryKv();
    const many = Array.from({ length: 80 }, (_, i) => `alert-${i}`);
    await saveDismissed(1, many, kv);
    const back = await loadDismissed(1, kv);
    expect(back).toHaveLength(50);
    expect(back[back.length - 1]).toBe('alert-79');
  });

  test('a broken storage never throws', async () => {
    const broken = {
      getItem: async () => {
        throw new Error('disk');
      },
      setItem: async () => {
        throw new Error('disk');
      },
    };
    await expect(loadDismissed(1, broken)).resolves.toEqual([]);
    await expect(saveDismissed(1, ['a'], broken)).resolves.toBeUndefined();
  });
});
