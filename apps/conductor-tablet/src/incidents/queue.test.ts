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
});
