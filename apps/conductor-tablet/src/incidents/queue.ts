import type { IncidentDraft } from '../api/types';
import { Lock, memoryKv, withoutSent, type KeyValue } from '../gps/queue';

export const INCIDENT_KEY = 'uta.incident.queue';
const MAX_ITEMS = 20;

export { memoryKv };

/**
 * Incidents (an SOS among them) waiting for signal. Every write goes through one lock and a send removes only what
 * it sent, so an SOS added while another send is on its way is never overwritten.
 */
export class IncidentQueue {
  private lock = new Lock();
  private flight: Promise<number> | null = null;

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

  push(draft: IncidentDraft) {
    return this.lock.run(async () => {
      const items = await this.load();
      items.push(draft);
      await this.save(items);
    });
  }

  async size() {
    return (await this.load()).length;
  }

  clear() {
    return this.lock.run(async () => {
      if (this.kv.removeItem) await this.kv.removeItem(INCIDENT_KEY);
      else await this.kv.setItem(INCIDENT_KEY, '[]');
    });
  }

  /**
   * Send what is waiting, oldest first, stopping at the first one `send` wants to keep. One send at a time: a call
   * made while another runs gets its result, so the same incident never goes out twice.
   */
  flush(send: (draft: IncidentDraft) => Promise<boolean>): Promise<number> {
    if (this.flight) return this.flight;
    this.flight = (async () => {
      const items = await this.load();
      const sent: IncidentDraft[] = [];
      for (const item of items) {
        if (!(await send(item))) break;
        sent.push(item);
      }
      if (sent.length) await this.lock.run(async () => this.save(withoutSent(await this.load(), sent)));
      return sent.length;
    })().finally(() => {
      this.flight = null;
    });
    return this.flight;
  }
}

export async function flushIncidents(
  queue: IncidentQueue,
  send: (draft: IncidentDraft) => Promise<boolean>,
): Promise<number> {
  return queue.flush(send);
}
