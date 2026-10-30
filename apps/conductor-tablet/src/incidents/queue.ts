import type { IncidentDraft } from '../api/types';
import { memoryKv, type KeyValue } from '../gps/queue';

export const INCIDENT_KEY = 'uta.incident.queue';
const MAX_ITEMS = 20;

export { memoryKv };

export class IncidentQueue {
  constructor(private kv: KeyValue) {}

  async load(): Promise<IncidentDraft[]> {
    const raw = await this.kv.getItem(INCIDENT_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as IncidentDraft[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  async save(items: IncidentDraft[]) {
    await this.kv.setItem(INCIDENT_KEY, JSON.stringify(items.slice(-MAX_ITEMS)));
  }

  async push(draft: IncidentDraft) {
    const items = await this.load();
    items.push(draft);
    await this.save(items);
  }

  async size() {
    return (await this.load()).length;
  }

  async clear() {
    if (this.kv.removeItem) await this.kv.removeItem(INCIDENT_KEY);
    else await this.kv.setItem(INCIDENT_KEY, '[]');
  }
}

export async function flushIncidents(
  queue: IncidentQueue,
  send: (draft: IncidentDraft) => Promise<boolean>,
): Promise<number> {
  const items = await queue.load();
  let sent = 0;
  for (const item of items) {
    const ok = await send(item);
    if (!ok) break;
    sent += 1;
  }
  await queue.save(items.slice(sent));
  return sent;
}
