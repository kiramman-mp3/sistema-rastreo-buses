/**
 * The colour of a route comes from the server (Odoo, set by the office), so the text on its chip cannot
 * be a fixed white: on the yellow or light blue of a line it would not be readable. The text takes
 * whichever of white or the dark ink has more contrast with the chip (WCAG 2 relative luminance).
 */
import { palettes } from './theme';

const LIGHT = palettes.day.onAccent;
const DARK = palettes.day.ink;

function channels(hex: string): [number, number, number] | null {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})([0-9a-f]{2})?$/i.exec(hex.trim());
  if (!match) return null;
  const digits = match[1].length === 3 ? match[1].replace(/./g, (c) => c + c) : match[1];
  return [0, 2, 4].map((i) => parseInt(digits.slice(i, i + 2), 16)) as [number, number, number];
}

/** WCAG relative luminance of a #RGB or #RRGGBB colour; null when it is not one (a name, rgb(), junk). */
export function luminance(hex: string): number | null {
  const rgb = channels(hex);
  if (!rgb) return null;
  const [r, g, b] = rgb.map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Contrast ratio between two colours, 1 to 21; null when either is not a hex colour. */
export function contrastRatio(a: string, b: string): number | null {
  const la = luminance(a);
  const lb = luminance(b);
  if (la === null || lb === null) return null;
  const [hi, lo] = la >= lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** The text colour for a chip of this colour: white or the dark ink, whichever reads better. */
export function readableOn(background: string): string {
  const withLight = contrastRatio(LIGHT, background);
  const withDark = contrastRatio(DARK, background);
  if (withLight === null || withDark === null) return LIGHT;
  return withDark > withLight ? DARK : LIGHT;
}
