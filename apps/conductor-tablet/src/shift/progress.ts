import type { StopState } from '../api/types';

export type StopView = {
  id: number;
  name: string;
  sequence: number;
  arrivedAt: string | null;
  status: 'arrived' | 'next' | 'later';
};

export function classifyStops(stops: StopState[], nextStopId: number | null): StopView[] {
  const sorted = [...stops].sort((a, b) => a.sequence - b.sequence || a.id - b.id);
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
