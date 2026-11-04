import type { SosState, StopState } from '../api/types';

export type StopView = {
  id: number;
  name: string;
  sequence: number;
  arrivedAt: string | null;
  status: 'arrived' | 'next' | 'later';
};

export function classifyStops(
  stops: StopState[],
  nextStopId: number | null,
  direction: 'forward' | 'back' = 'forward',
): StopView[] {
  // On the way back the bus meets the stops in reverse order.
  const sign = direction === 'back' ? -1 : 1;
  const sorted = [...stops].sort((a, b) => sign * (a.sequence - b.sequence || a.id - b.id));
  const effectiveNextId = nextStopId ?? sorted.find((s) => !s.arrived_at)?.id ?? null;
  return sorted.map((stop) => ({
    id: stop.id,
    name: stop.name,
    sequence: stop.sequence,
    arrivedAt: stop.arrived_at,
    status: stop.arrived_at ? 'arrived' : stop.id === effectiveNextId ? 'next' : 'later',
  }));
}

export function clock(iso: string | null): string {
  if (!iso) return '';
  const match = iso.match(/T(\d{2}:\d{2})/);
  return match ? match[1] : iso;
}

/** Four stops fit at a readable size: the next one and the three after it (or the last ones). */
export function stopWindow(stops: StopView[], before = 0, after = 3): StopView[] {
  const next = stops.findIndex((s) => s.status === 'next');
  if (next < 0) return stops.slice(-(before + after + 1));
  const from = Math.max(0, next - before);
  return stops.slice(from, from + before + after + 1);
}

export type SosLocal = { status: 'sending' | 'queued' | 'sent'; at: string } | null;
export type SosPhase = 'seen' | 'sending' | 'queued' | 'sent' | null;

/**
 * What the cabin says about the SOS. The server wins once it has the SOS the driver pressed
 * (same or later report time); before that the tablet's own state is shown.
 */
export function sosPhase(server: SosState | null | undefined, local: SosLocal): SosPhase {
  const serverAt = Date.parse(server?.sent_at ?? '');
  const delivered = !!server && (!local || serverAt >= Date.parse(local.at) - 2000);
  if (delivered && server?.seen_at) return 'seen';
  if (local?.status === 'sending') return 'sending';
  if (delivered) return 'sent';
  return local?.status ?? null;
}
