/**
 * Buses UTA tokens for the tablet. Same names and values as addons/bus_tracking/static/src/css/brand.css;
 * contrast measured by qa/contraste.py. Day mode is for direct sun, night mode for the dark cabin.
 */
export type Palette = {
  mode: 'day' | 'night';
  ground: string;
  panel: string;
  field: string;
  ink: string;
  ink2: string;
  line: string;
  accent: string;
  onAccent: string;
  signal: string;
  onSignal: string;
  ok: string;
  warn: string;
  danger: string;
  onDanger: string;
  /** Hairline around cards that sit on the ground. */
  edge: string;
  /** Soft wash of the accent behind a selected or highlighted row. */
  tint: string;
};

export const palettes: Record<'day' | 'night', Palette> = {
  day: {
    mode: 'day',
    ground: '#F3F4F1',
    panel: '#FFFFFF',
    field: '#FFFFFF',
    ink: '#172025',
    ink2: '#3E4C51',
    line: '#7A1A22',
    accent: '#7A1A22',
    onAccent: '#FFFFFF',
    signal: '#FFC62B',
    onSignal: '#172025',
    ok: '#1D6B44',
    warn: '#7A5000',
    danger: '#A1221B',
    onDanger: '#FFFFFF',
    edge: '#DCE0DC',
    tint: '#F6E9EA',
  },
  night: {
    mode: 'night',
    ground: '#0E1316',
    panel: '#1A2226',
    field: '#1A2226',
    ink: '#F2F5F4',
    ink2: '#B9C4C2',
    line: '#C9545E',
    accent: '#FFC62B',
    onAccent: '#172025',
    signal: '#FFC62B',
    onSignal: '#172025',
    ok: '#5FD19A',
    warn: '#FFC62B',
    danger: '#FF8A80',
    onDanger: '#172025',
    edge: '#2B363B',
    tint: '#2A2420',
  },
};

/** Sizes: nothing the driver reads is smaller than `small`. */
export const sizes = {
  small: 20,
  body: 22,
  data: 32,
  title: 40,
  stop: 60,
};

/** Phones are held closer than a dashboard tablet: smaller steps, but still large and never under 16. */
export const sizesPhone: typeof sizes = {
  small: 16,
  body: 18,
  data: 24,
  title: 30,
  stop: 40,
};

/** Spacing on a 4 px grid, so nothing is placed by eye: space[2] is 8, space[4] is 16. */
export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 12: 48 } as const;

/** Lines around controls and marks. */
export const border = { thin: 2, mark: 3, round: 999 } as const;

/**
 * Two corners: controls and fields are rounder than the old 8, cards that group them rounder still, so the
 * nesting reads. `continuous` is the smooth corner of iOS and changes nothing on Android.
 */
export const shape = {
  control: { borderRadius: 14, borderCurve: 'continuous' },
  card: { borderRadius: 22, borderCurve: 'continuous' },
} as const;

/** One soft lift for cards on the ground. Night mode drops it: a shadow on near-black only muddies. */
export const lift = {
  shadowColor: '#172025',
  shadowOpacity: 0.08,
  shadowRadius: 18,
  shadowOffset: { width: 0, height: 6 },
  elevation: 3,
} as const;

export const fonts = {
  text: 'Atkinson-Regular',
  bold: 'Atkinson-Bold',
  /** Bricolage Grotesque for the big words only (titles, the next stop, the numbers): the voice of the brand. */
  display: 'Bricolage-Bold',
};
