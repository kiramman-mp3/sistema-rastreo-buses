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
