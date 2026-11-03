import { contrastRatio, luminance, readableOn } from './contrast';

const INK = '#172025';
const WHITE = '#FFFFFF';

describe('route chip contrast', () => {
  test('black and white are 21:1 apart', () => {
    expect(contrastRatio('#000000', '#FFFFFF')).toBeCloseTo(21, 5);
    expect(luminance('#FFFFFF')).toBeCloseTo(1, 5);
  });

  test('the light blue of the Quero line takes dark text, which is the one that passes 4.5:1', () => {
    expect(readableOn('#3388FF')).toBe(INK);
    expect(contrastRatio(INK, '#3388FF')).toBeGreaterThan(4.5);
    expect(contrastRatio(WHITE, '#3388FF')).toBeLessThan(4.5);
  });

  test('yellow and white chips take dark text; the brand maroon and dark blues take white', () => {
    expect(readableOn('#FFC62B')).toBe(INK);
    expect(readableOn('#FFFFFF')).toBe(INK);
    expect(readableOn('#7A1A22')).toBe(WHITE);
    expect(readableOn('#3D4F8A')).toBe(WHITE);
    expect(readableOn('#1E5560')).toBe(WHITE);
  });

  test('three-digit colours work and so does a trailing alpha', () => {
    expect(readableOn('#fc0')).toBe(INK);
    expect(readableOn('#7A1A22ff')).toBe(WHITE);
  });

  test('a colour that is not hex falls back to white, never throws', () => {
    for (const junk of ['', 'red', 'rgb(1,2,3)', '#12', '#GGGGGG', 'transparent']) {
      expect(readableOn(junk)).toBe(WHITE);
    }
    expect(contrastRatio('red', '#FFFFFF')).toBeNull();
  });

  test('whatever the colour, the better of the two reaches at least 4:1', () => {
    for (let v = 0; v <= 255; v += 5) {
      const hex = '#' + [v, v, v].map((n) => n.toString(16).padStart(2, '0')).join('');
      const best = Math.max(contrastRatio(WHITE, hex) ?? 0, contrastRatio(INK, hex) ?? 0);
      expect(best).toBeGreaterThanOrEqual(4);
    }
  });
});
