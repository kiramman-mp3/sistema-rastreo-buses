import { getLang } from './index';

/** The locale for numbers: Ecuador for Spanish (comma decimals) and the Kichwa draft, plain English for English. */
function locale(): string {
  return getLang() === 'en' ? 'en' : 'es-EC';
}

function format(value: number, maximumFractionDigits: number): string {
  try {
    return new Intl.NumberFormat(locale(), { maximumFractionDigits }).format(value);
  } catch {
    return value.toFixed(maximumFractionDigits);
  }
}

/**
 * A distance for the cabin: whole metres under a kilometre, then kilometres with one decimal and,
 * from 100 km, none (a decimal of a long distance is noise). The unit stays attached to the number.
 */
export function formatDistance(meters: number): string {
  if (!Number.isFinite(meters) || meters < 0) return '';
  if (meters < 1000) return `${format(Math.round(meters), 0)} m`;
  const km = meters / 1000;
  return `${format(km, km >= 100 ? 0 : 1)} km`;
}
