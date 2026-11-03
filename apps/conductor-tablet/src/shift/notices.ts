/**
 * What the cabin says about the SOS and the open alerts, in the order a driver needs it: what still
 * needs attention first (an SOS nobody has seen, then the open alerts) and good news last (the office
 * saw the SOS). The screen has room for few, so the rest is counted, not hidden without a word.
 */
export type NoticeTone = 'danger' | 'ok' | 'warn';

export type NoticeItem = {
  key: string;
  tone: NoticeTone;
  title: string;
  detail?: string;
  /** How a screen reader announces it: the SOS answer interrupts, an alert waits its turn. */
  live: 'polite' | 'assertive';
};

type NoticeInput = {
  /** The SOS line already in the driver's language, or null when there is no SOS to talk about. */
  sos: { text: string; seen: boolean } | null;
  /** The open alerts, titled and detailed in the driver's language. */
  alerts: { id: number; title: string; detail: string }[];
};

const RANK: Record<NoticeTone, number> = { danger: 0, warn: 1, ok: 2 };

export function buildNotices({ sos, alerts }: NoticeInput): NoticeItem[] {
  const items: NoticeItem[] = [];
  if (sos) {
    items.push({ key: 'sos', tone: sos.seen ? 'ok' : 'danger', title: sos.text, live: 'assertive' });
  }
  for (const alert of alerts) {
    items.push({
      key: `alert-${alert.id}`,
      tone: 'danger',
      title: alert.title,
      detail: alert.detail || undefined,
      live: 'polite',
    });
  }
  // Array.sort is stable: inside a tone the order above (the SOS before the alerts) holds.
  return items.sort((a, b) => RANK[a.tone] - RANK[b.tone]);
}

/** The first `max` notices (at least one when there is any) and how many were left out. */
export function pickNotices(items: NoticeItem[], max: number): { shown: NoticeItem[]; hidden: number } {
  const room = Math.max(1, Math.floor(max));
  return { shown: items.slice(0, room), hidden: Math.max(0, items.length - room) };
}
