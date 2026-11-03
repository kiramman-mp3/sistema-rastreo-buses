import { memoryKv, type KeyValue } from '../gps/queue';
import type { ErrorReport } from './report';

export const ERROR_KEY = 'uta.error.queue';
export const LAST_ERROR_KEY = 'uta.error.last';
const MAX_ITEMS = 10;

export { memoryKv };

/**
 * Failures waiting to reach the office. Without signal they stay here (a few, the newest) and go out later;
 * the same failure twice in a row is kept once, so a crash loop cannot fill the tablet or the log.
 */
export class ErrorQueue {
  constructor(private kv: KeyValue) {}

  async load(): Promise<ErrorReport[]> {
    const raw = await this.kv.getItem(ERROR_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as ErrorReport[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  async save(items: ErrorReport[]) {
    await this.kv.setItem(ERROR_KEY, JSON.stringify(items.slice(-MAX_ITEMS)));
  }

  async push(report: ErrorReport) {
    const items = await this.load();
    if (items[items.length - 1]?.message !== report.message) items.push(report);
    await this.save(items);
    // Kept after it is sent too: the GPS status screen shows the last failure of the app.
    await this.kv.setItem(LAST_ERROR_KEY, JSON.stringify(report));
  }

  /** The last failure this tablet had, sent or not; null when there never was one. */
  async last(): Promise<ErrorReport | null> {
    const raw = await this.kv.getItem(LAST_ERROR_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as ErrorReport;
      return parsed && typeof parsed.message === 'string' ? parsed : null;
    } catch {
      return null;
    }
  }

  async size() {
    return (await this.load()).length;
  }
}

/**
 * Send what is waiting, oldest first. `send` answers true when the report is done with (sent, or refused for
 * good) and false to keep it for later (no signal, server error).
 */
export async function flushErrors(queue: ErrorQueue, send: (report: ErrorReport) => Promise<boolean>): Promise<number> {
  const items = await queue.load();
  let sent = 0;
  for (const item of items) {
    if (!(await send(item))) break;
    sent += 1;
  }
  if (sent > 0) await queue.save(items.slice(sent));
  return sent;
}
