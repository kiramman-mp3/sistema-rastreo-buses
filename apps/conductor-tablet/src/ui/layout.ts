import { useMemo } from 'react';
import { useWindowDimensions } from 'react-native';

import { sizes, sizesPhone } from './theme';

/** Android's own "sw600dp" rule: a shortest side under 600 dp is a phone, anything else a tablet. */
export const PHONE_MAX_SHORT_SIDE = 600;
/** Two panes side by side need room: under this width they stack. */
export const TWO_PANE_MIN_WIDTH = 640;
/** Below this height the screen has no room for decoration (phones on their side). */
export const SHORT_HEIGHT = 480;

export type Layout = {
  width: number;
  height: number;
  landscape: boolean;
  /** Phone-sized screen, in either orientation. */
  phone: boolean;
  /** Wide enough for two panes side by side (forms, lists). */
  wide: boolean;
  /** Very little vertical room (a phone on its side): drop what is not essential. */
  short: boolean;
  /** Text sizes for this screen class. */
  sizes: typeof sizes;
  /** Minimum height of every control. */
  hit: number;
  /** Outer padding of a screen. */
  gutter: number;
  /** Gap between blocks. */
  gap: number;
};

export function layoutFor(width: number, height: number): Layout {
  const phone = Math.min(width, height) < PHONE_MAX_SHORT_SIDE;
  const landscape = width > height;
  const short = height < SHORT_HEIGHT;
  return {
    width,
    height,
    landscape,
    phone,
    wide: width >= TWO_PANE_MIN_WIDTH,
    short,
    sizes: phone ? sizesPhone : sizes,
    // 72 dp is for gloved hands on a tablet; 56 dp is still far over Android's 48 dp minimum.
    hit: phone ? 56 : 72,
    gutter: phone ? (short ? 12 : 16) : 24,
    gap: phone ? (short ? 8 : 12) : 16,
  };
}

export function useLayout(): Layout {
  const { width, height } = useWindowDimensions();
  return useMemo(() => layoutFor(width, height), [width, height]);
}
