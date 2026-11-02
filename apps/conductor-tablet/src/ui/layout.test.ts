import { layoutFor } from './layout';
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

  test('the shortest side decides phone or tablet, not the orientation', () => {
    expect(layoutFor(599, 1000).phone).toBe(true);
    expect(layoutFor(1000, 599).phone).toBe(true);
    expect(layoutFor(600, 1000).phone).toBe(false);
  });

  test('nothing the driver reads is smaller than 16 px', () => {
    expect(Math.min(...Object.values(sizesPhone))).toBeGreaterThanOrEqual(16);
    expect(Math.min(...Object.values(sizes))).toBeGreaterThanOrEqual(20);
  });
});
