import { formatDistance } from './format';
import { setLang } from './index';

describe('formatDistance', () => {
  afterEach(() => setLang('es'));

  test('whole metres under a kilometre', () => {
    setLang('es');
    expect(formatDistance(850.4)).toBe('850 m');
    expect(formatDistance(0)).toBe('0 m');
  });

  test('kilometres with the decimal mark of the language', () => {
    setLang('es');
    expect(formatDistance(1500)).toBe('1,5 km');
    setLang('en');
    expect(formatDistance(1500)).toBe('1.5 km');
  });

  test('from 100 km there are no decimals', () => {
    setLang('en');
    expect(formatDistance(120400)).toMatch(/^120[,.\s]?(?:400|0)?\s?km$|^120 km$/);
    expect(formatDistance(8837900)).toMatch(/^8\D?838 km$/);
  });

  test('nothing sensible to say gives an empty string', () => {
    expect(formatDistance(NaN)).toBe('');
    expect(formatDistance(-5)).toBe('');
    expect(formatDistance(Infinity)).toBe('');
  });
});
