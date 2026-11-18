import { flushIncidents, IncidentQueue, memoryKv } from './queue';
import type { IncidentDraft } from '../api/types';

function draft(kind: IncidentDraft['kind'] = 'traffic'): IncidentDraft {
  return { kind, note: kind, lat: -1.24, lon: -78.62 };
}

describe('incident queue', () => {
  test('retries in order and keeps the rest after a network failure', async () => {
    const queue = new IncidentQueue(memoryKv());
    await queue.push(draft('breakdown'));
    await queue.push(draft('traffic'));
    await queue.push(draft('accident'));
    const seen: string[] = [];
    const sent = await flushIncidents(queue, async (item) => {
      seen.push(item.kind);
      return item.kind !== 'traffic';
    });
    expect(sent).toBe(1);
    expect(seen).toEqual(['breakdown', 'traffic']);
    expect((await queue.load()).map((item) => item.kind)).toEqual(['traffic', 'accident']);
  });

  test('clears the queue when every report is accepted', async () => {
    const queue = new IncidentQueue(memoryKv());
    await queue.push(draft('other'));
    await flushIncidents(queue, async () => true);
    expect(await queue.size()).toBe(0);
  });

  test('an sos added while a send is on its way is kept (DEF-052)', async () => {
    const queue = new IncidentQueue(memoryKv());
    await queue.push(draft('traffic'));
    let release!: () => void;
    const slow = new Promise<void>((resolve) => {
      release = resolve;
    });
    const flushing = flushIncidents(queue, async () => {
      await slow;
      return true;
    });
    await queue.push(draft('sos'));
    release();
    expect(await flushing).toBe(1);
    expect((await queue.load()).map((item) => item.kind)).toEqual(['sos']);
  });

  test('two flushes at once send each incident only once', async () => {
    const queue = new IncidentQueue(memoryKv());
    await queue.push(draft('sos'));
    await queue.push(draft('breakdown'));
    const seen: string[] = [];
    const send = async (item: IncidentDraft) => {
      await new Promise((resolve) => setTimeout(resolve, 5));
      seen.push(item.kind);
      return true;
    };
    const [first, second] = await Promise.all([flushIncidents(queue, send), flushIncidents(queue, send)]);
    expect(seen).toEqual(['sos', 'breakdown']);
    expect(first).toBe(2);
    expect(second).toBe(2);
    expect(await queue.size()).toBe(0);
  });

  test('pushes made at the same time are all kept', async () => {
    const queue = new IncidentQueue(memoryKv());
    await Promise.all([queue.push(draft('sos')), queue.push(draft('traffic')), queue.push(draft('other'))]);
    expect(await queue.size()).toBe(3);
  });
});
