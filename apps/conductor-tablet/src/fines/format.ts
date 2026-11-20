import type { Fine } from '../api/types';

/** The longest statement a driver may send; the server refuses anything longer. */
export const APPEAL_MAX = 1000;

/** The statement as it is sent, or null when there is nothing to send. */
export function appealText(raw: string): string | null {
  const text = raw.trim();
  if (!text || text.length > APPEAL_MAX) return null;
  return text;
}

export type FineStatus = 'fined' | 'appealed' | 'rejected' | 'accepted';

/** Where the fine stands for the driver: confirmed, appealed and waiting, or the appeal answered. */
export function fineStatus(fine: Fine): FineStatus {
  if (fine.appeal_result === 'accepted') return 'accepted';
  if (fine.appeal_result === 'rejected') return 'rejected';
  if (fine.state === 'appealed') return 'appealed';
  return 'fined';
}

/** Whole hours left to appeal (0 when the time is over or there is none). */
export function hoursToAppeal(fine: Fine, now: number = Date.now()): number {
  if (!fine.can_appeal || !fine.appeal_deadline) return 0;
  const left = Date.parse(fine.appeal_deadline) - now;
  return Number.isNaN(left) || left <= 0 ? 0 : Math.ceil(left / 3600000);
}

/** "$25.00" in the language of the app. */
export function money(amount: number, currency: string, locale?: string): string {
  const value = Number.isFinite(amount) ? amount : 0;
  return `${currency}${value.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** The fines still to be answered first, then the newest. */
export function sortFines(fines: Fine[]): Fine[] {
  return [...fines].sort((a, b) => {
    if (a.can_appeal !== b.can_appeal) return a.can_appeal ? -1 : 1;
    return (Date.parse(b.occurred_at ?? '') || 0) - (Date.parse(a.occurred_at ?? '') || 0);
  });
}
