import { useMemo } from 'react';
import { useWindowDimensions } from 'react-native';

import { sizes, sizesPhone, space } from './theme';

/** Android's own "sw600dp" rule: a shortest side under 600 dp is a phone, anything else a tablet. */
export const PHONE_MAX_SHORT_SIDE = 600;
/** Two panes side by side need room: under this width they stack. */
export const TWO_PANE_MIN_WIDTH = 640;
/** Below this height the screen has no room for decoration (phones on their side). */
export const SHORT_HEIGHT = 480;
/** A portrait screen at least this tall (dp) can pin two notices and still show the next stop and the map. */
export const TALL_PORTRAIT_HEIGHT = 800;

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
  /** The system font size is 130 % or more: fixed-height layouts no longer fit and the page scrolls instead. */
  largeText: boolean;
  /** Text sizes for this screen class. */
  sizes: typeof sizes;
  /** Minimum height of every control. */
  hit: number;
  /** Outer padding of a screen. */
  gutter: number;
  /** Gap between blocks. */
  gap: number;
};

/**
 * From this system font scale the cabin screens stop trying to fit everything in one view. Android reports
 * a setting of 130 % as 1.2999999, so the comparison has a little room.
 */
export const LARGE_TEXT_SCALE = 1.3;
const SCALE_TOLERANCE = 0.01;

export function layoutFor(width: number, height: number, fontScale = 1): Layout {
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
    largeText: fontScale >= LARGE_TEXT_SCALE - SCALE_TOLERANCE,
    sizes: phone ? sizesPhone : sizes,
    // 72 dp is for gloved hands on a tablet; 56 dp is still far over Android's 48 dp minimum.
    hit: phone ? 56 : 72,
    gutter: phone ? (short ? space[3] : space[4]) : space[6],
    gap: phone ? (short ? space[2] : space[3]) : space[4],
  };
}

/**
 * How many notices (SOS answer, alerts) the shift screen pins above the next stop. The next stop must always
 * stay visible: a phone in portrait that is not tall has room for one, the rest is counted ("1 aviso más").
 * With large text the page scrolls and there is room for two.
 */
export function noticeCapacity(layout: Layout): number {
  if (layout.largeText) return 2;
  if (layout.short) return 1;
  if (!layout.landscape && layout.height < TALL_PORTRAIT_HEIGHT) return 1;
  return 2;
}

export function useLayout(): Layout {
  const { width, height, fontScale } = useWindowDimensions();
  return useMemo(() => layoutFor(width, height, fontScale), [width, height, fontScale]);
}
