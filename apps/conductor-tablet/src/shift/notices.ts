/**
 * What the cabin says about the SOS and the open alerts, in the order a driver needs it: what still
 * needs attention first (an SOS nobody has seen, then the open alerts) and good news last (the office
 * saw the SOS). The screen has room for few, so the rest is counted, not hidden without a word.
 * The driver can close an alert once read; it only goes from this screen, the office still sees it.
 */
export type NoticeTone = 'danger' | 'ok' | 'warn';

export type NoticeItem = {
  key: string;
  /** What the driver closed: the alert or the SOS itself, so a new one with another id shows again. */
  dismissKey?: string;
  /** False while the message still tells something that has not happened yet (the SOS is not delivered). */
  dismissible?: boolean;
  tone: NoticeTone;
  title: string;
  detail?: string;
  /** How a screen reader announces it: the SOS answer interrupts, an alert waits its turn. */
  live: 'polite' | 'assertive';
};

type NoticeInput = {
  /** The SOS line already in the driver's language, or null when there is no SOS to talk about. */
  sos: { text: string; seen: boolean; id: string; delivered: boolean } | null;
  /** The open alerts, titled and detailed in the driver's language. */
  alerts: { id: number; title: string; detail: string }[];
  /** What the driver already closed (`dismissKey`s). Closing hides it here only. */
  dismissed?: ReadonlySet<string>;
};

const RANK: Record<NoticeTone, number> = { danger: 0, warn: 1, ok: 2 };

export function buildNotices({ sos, alerts, dismissed }: NoticeInput): NoticeItem[] {
  const items: NoticeItem[] = [];
  if (sos) {
    items.push({
      key: 'sos',
      dismissKey: `sos-${sos.id}`,
      // Only once the office has it: an SOS that is "sending" or "saved" must stay in sight.
      dismissible: sos.delivered,
      tone: sos.seen ? 'ok' : 'danger',
      title: sos.text,
      live: 'assertive',
    });
  }
  for (const alert of alerts) {
    items.push({
      key: `alert-${alert.id}`,
      dismissKey: `alert-${alert.id}`,
      dismissible: true,
      tone: 'danger',
      title: alert.title,
      detail: alert.detail || undefined,
      live: 'polite',
    });
  }
  // Array.sort is stable: inside a tone the order above (the SOS before the alerts) holds.
  return items
    .filter((item) => !(item.dismissible && item.dismissKey && dismissed?.has(item.dismissKey)))
    .sort((a, b) => RANK[a.tone] - RANK[b.tone]);
}

/** The first `max` notices (at least one when there is any) and how many were left out. */
export function pickNotices(items: NoticeItem[], max: number): { shown: NoticeItem[]; hidden: number } {
  const room = Math.max(1, Math.floor(max));
  return { shown: items.slice(0, room), hidden: Math.max(0, items.length - room) };
}
