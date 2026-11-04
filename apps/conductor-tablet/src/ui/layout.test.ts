import { layoutFor, noticeCapacity } from './layout';
import { sizes, sizesPhone } from './theme';

describe('layoutFor', () => {
  test('a phone in portrait stacks and uses the phone sizes', () => {
    const l = layoutFor(390, 844);
    expect(l.phone).toBe(true);
    expect(l.landscape).toBe(false);
    expect(l.wide).toBe(false);
    expect(l.sizes).toBe(sizesPhone);
    expect(l.hit).toBe(56);
  });

  test('a phone on its side has panes side by side but little height', () => {
    const l = layoutFor(844, 390);
    expect(l.phone).toBe(true);
    expect(l.landscape).toBe(true);
    expect(l.wide).toBe(true);
    expect(l.short).toBe(true);
    expect(l.gutter).toBe(12);
    expect(layoutFor(390, 844).gutter).toBe(16);
  });

  test('a tablet keeps the cabin sizes in both orientations', () => {
    for (const [w, h] of [
      [1280, 800],
      [800, 1280],
    ]) {
      const l = layoutFor(w, h);
      expect(l.phone).toBe(false);
      expect(l.sizes).toBe(sizes);
      expect(l.hit).toBe(72);
      expect(l.wide).toBe(w >= 640);
      expect(l.short).toBe(false);
    }
  });

  test('a tablet-class screen with little height gets the compact layout (foldable opened, split window)', () => {
    for (const [w, h] of [
      [791, 820], // Pixel Fold inner screen, portrait
      [820, 791], // and turned
    ]) {
      const l = layoutFor(w, h);
      expect(l.phone).toBe(false);
      expect(l.snug).toBe(true);
      expect(l.compact).toBe(true);
      expect(l.sizes).toBe(sizesPhone);
      expect(l.hit).toBe(56);
    }
    // a real tablet keeps the big cabin sizes: tall enough, or wide enough to put the panes side by side
    for (const [w, h] of [
      [820, 1180],
      [1180, 820],
      [1280, 800],
    ]) {
      expect(layoutFor(w, h).snug).toBe(false);
      expect(layoutFor(w, h).sizes).toBe(sizes);
    }
    expect(layoutFor(390, 844).compact).toBe(true); // a phone is compact too
  });

  test('the shortest side decides phone or tablet, not the orientation', () => {
    expect(layoutFor(599, 1000).phone).toBe(true);
    expect(layoutFor(1000, 599).phone).toBe(true);
    expect(layoutFor(600, 1000).phone).toBe(false);
  });

  test('a font scale of 130 % or more asks the screens to scroll', () => {
    expect(layoutFor(390, 844).largeText).toBe(false);
    expect(layoutFor(390, 844, 1.15).largeText).toBe(false);
    expect(layoutFor(390, 844, 1.3).largeText).toBe(true);
    expect(layoutFor(390, 844, 1.2999999523162842).largeText).toBe(true); // what Android reports for 130 %
    expect(layoutFor(1280, 800, 2).largeText).toBe(true);
  });

  test('pinned notices: one where the next stop would be pushed out, two where there is room', () => {
    expect(noticeCapacity(layoutFor(411, 731))).toBe(1); // a phone in portrait that is not tall
    expect(noticeCapacity(layoutFor(390, 844))).toBe(2);
    expect(noticeCapacity(layoutFor(844, 390))).toBe(1); // a phone on its side
    expect(noticeCapacity(layoutFor(1067, 600))).toBe(2); // a tablet on its side: the column scrolls
    expect(noticeCapacity(layoutFor(800, 1280))).toBe(2);
    expect(noticeCapacity(layoutFor(411, 731, 2))).toBe(2); // large text: the page scrolls
  });

  test('nothing the driver reads is smaller than 16 px', () => {
    expect(Math.min(...Object.values(sizesPhone))).toBeGreaterThanOrEqual(16);
    expect(Math.min(...Object.values(sizes))).toBeGreaterThanOrEqual(20);
  });
});
