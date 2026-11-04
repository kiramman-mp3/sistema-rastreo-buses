import { GPS_INTERVAL_MS } from './interval';
import type { Fix } from './osmand';

export type KeyValue = {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem?(key: string): Promise<void>;
};

export const QUEUE_KEY = 'uta.gps.queue';
export const MAX_QUEUE_AGE_MS = 2 * 60 * 60 * 1000;
/** Two hours at one fix per interval, the same span as the maximum age. */
export const MAX_QUEUE_ITEMS = MAX_QUEUE_AGE_MS / GPS_INTERVAL_MS;

export function memoryKv(initial: Record<string, string> = {}): KeyValue {
  const data = { ...initial };
  return {
    getItem: async (key) => data[key] ?? null,
    setItem: async (key, value) => {
      data[key] = value;
    },
    removeItem: async (key) => {
      delete data[key];
    },
  };
}

export class LocationQueue {
  private chain: Promise<unknown> = Promise.resolve();

  constructor(
    private kv: KeyValue,
    private now: () => number = Date.now,
    private maxItems = MAX_QUEUE_ITEMS,
    private maxAgeMs = MAX_QUEUE_AGE_MS,
  ) {}

  prune(items: Fix[]): Fix[] {
    const cutoff = this.now() - this.maxAgeMs;
    const fresh = items.filter((item) => item.timestampMs >= cutoff);
    return fresh.length > this.maxItems ? fresh.slice(fresh.length - this.maxItems) : fresh;
  }

  async load(): Promise<Fix[]> {
    const raw = await this.kv.getItem(QUEUE_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as Fix[];
      if (!Array.isArray(parsed)) return [];
      return this.prune(parsed);
    } catch {
      return [];
    }
  }

  async save(items: Fix[]) {
    await this.kv.setItem(QUEUE_KEY, JSON.stringify(this.prune(items)));
  }

  async push(fix: Fix) {
    await this.pushMany([fix]);
  }

  async pushMany(fixes: Fix[]) {
    const items = await this.load();
    items.push(...fixes);
    await this.save(items);
  }

  /** Run `task` alone: every other exclusive task on this queue waits for it to finish. */
  exclusive<T>(task: () => Promise<T>): Promise<T> {
    const run = this.chain.then(task, task);
    this.chain = run.catch(() => undefined);
    return run;
  }

  async size() {
    return (await this.load()).length;
  }

  async clear() {
    if (this.kv.removeItem) await this.kv.removeItem(QUEUE_KEY);
    else await this.kv.setItem(QUEUE_KEY, '[]');
  }
}

export async function flushQueue(
  queue: LocationQueue,
  send: (fix: Fix) => Promise<boolean>,
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
