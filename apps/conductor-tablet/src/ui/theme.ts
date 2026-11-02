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

export const colors = {
  paper: '#F1F5F9',
  card: '#FFFFFF',
  ink: '#0F172A',
  muted: '#64748B',
  route: '#0D684D',
  routeLight: '#ECFDF5',
  bus: '#DC2626',
  busLight: '#FEF2F2',
  line: '#CBD5E1',
  taken: '#94A3B8',
  highlight: '#2563EB',
  highlightLight: '#EFF6FF',
};

// High-contrast Cockpit Design System for Tablet in Driver Cabin
export const cockpitColors = {
  bg: '#0B0F17',              // Deep slate black anti-glare for night & high-contrast day
  surface: '#151D2A',         // Panel / Card background
  surfaceElevated: '#1E293B', // Top bar / Dialogs
  surfaceBorder: '#334155',   // Clean separator border
  borderActive: '#64748B',

  textBright: '#F8FAFC',      // WCAG AAA primary legible text (48px / 32px)
  textMuted: '#94A3B8',       // Secondary metrics and units
  textDim: '#64748B',         // Subtle captions

  // Headway & Status Traffic Signals
  onTime: '#10B981',          // Emerald
  onTimeBg: '#064E3B',
  onTimeBorder: '#059669',

  ahead: '#F59E0B',           // Amber
  aheadBg: '#78350F',
  aheadBorder: '#D97706',

  delayed: '#EF4444',         // Crimson Red
  delayedBg: '#7F1D1D',
  delayedBorder: '#DC2626',

  // Actions
  actionTraffic: '#D97706',   // Warning amber for congestion
  actionSos: '#DC2626',       // Emergency red
  actionSosHold: '#991B1B',

  brandUTA: '#8B1D24',        // Institutional crimson
};

export const type = {
  title: 26,
  body: 18,
  button: 18,
  cockpitDisplay: 38,
  cockpitHero: 32,
  cockpitSubtitle: 20,
};

export const hit = 52;
export const cockpitHit = 72; // Minimum 72px touch targets for driving ergonomics
