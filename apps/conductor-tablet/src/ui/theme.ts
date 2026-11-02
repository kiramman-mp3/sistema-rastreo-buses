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
};

export const palettes: Record<'day' | 'night', Palette> = {
  day: {
    mode: 'day',
    ground: '#FFFFFF',
    panel: '#F1F3F2',
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

export const fonts = {
  text: 'Atkinson-Regular',
  bold: 'Atkinson-Bold',
};
