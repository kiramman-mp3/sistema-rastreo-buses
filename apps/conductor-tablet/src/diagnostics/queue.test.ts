import { ErrorQueue, flushErrors, memoryKv } from './queue';
import type { ErrorReport } from './report';

function report(message: string): ErrorReport {
  return { message, app: '1.0.0', at: '2026-11-02T20:00:00.000Z' };
}

function make() {
  const kv = memoryKv();
  return { kv, queue: new ErrorQueue(kv) };
}

describe('error queue', () => {
  test('keeps reports in order and remembers the last one', async () => {
    const { queue } = make();
    await queue.push(report('a'));
    await queue.push(report('b'));
    expect((await queue.load()).map((r) => r.message)).toEqual(['a', 'b']);
    expect((await queue.last())?.message).toBe('b');
  });

  test('the same failure in a row is kept once (a crash loop does not fill it)', async () => {
    const { queue } = make();
    for (let i = 0; i < 5; i++) await queue.push(report('same'));
    expect(await queue.size()).toBe(1);
    await queue.push(report('other'));
    await queue.push(report('same'));
    expect(await queue.size()).toBe(3);
  });

  test('only the newest ten are kept', async () => {
    const { queue } = make();
    for (let i = 0; i < 15; i++) await queue.push(report('e' + i));
    const items = await queue.load();
    expect(items).toHaveLength(10);
    expect(items[0].message).toBe('e5');
  });

  test('damaged storage reads as empty, never throws', async () => {
    const { kv, queue } = make();
    await kv.setItem('uta.error.queue', '{not json');
    await kv.setItem('uta.error.last', '42');
    expect(await queue.load()).toEqual([]);
    expect(await queue.last()).toBeNull();
  });

  test('sending empties the queue but the last failure stays for the status screen', async () => {
    const { queue } = make();
    await queue.push(report('a'));
    await queue.push(report('b'));
    const sent = await flushErrors(queue, async () => true);
    expect(sent).toBe(2);
    expect(await queue.size()).toBe(0);
    expect((await queue.last())?.message).toBe('b');
  });

  test('without signal the rest waits, oldest first', async () => {
    const { queue } = make();
    for (const m of ['a', 'b', 'c']) await queue.push(report(m));
    const seen: string[] = [];
    const sent = await flushErrors(queue, async (r) => {
      seen.push(r.message);
      return r.message === 'a';
    });
    expect(sent).toBe(1);
    expect(seen).toEqual(['a', 'b']);
    expect((await queue.load()).map((r) => r.message)).toEqual(['b', 'c']);
  });
});
