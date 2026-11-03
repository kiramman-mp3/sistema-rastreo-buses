// The app ships no Node typings; this test only needs to read files, so it declares what it uses.
declare const require: (name: string) => any;
declare const __dirname: string;
const { readdirSync, readFileSync } = require('fs');
const { join } = require('path');

/**
 * Spacing lives on a 4 px grid (2 and 1 for hairlines). A padding, margin or gap written as a bare number
 * must be one of these; anything else is a value somebody typed by eye. Use `space[n]` from theme.ts.
 */
const GRID = new Set([0, 1, 2, 4, 8, 12, 16, 20, 24, 32]);
const ROOT = join(__dirname, '..', '..');
const SPACING = /\b(padding[A-Za-z]*|margin[A-Za-z]*|gap|rowGap|columnGap)\s*:\s*(-?\d+(?:\.\d+)?)\b/g;

function sources(folder: string): string[] {
  return readdirSync(join(ROOT, folder))
    .filter((name: string) => name.endsWith('.tsx'))
    .map((name: string) => join(folder, name));
}

describe('spacing grid', () => {
  const files = [...sources('app'), ...sources(join('src', 'ui'))];

  test('there are screens to check', () => {
    expect(files.length).toBeGreaterThan(8);
  });

  test.each(files)('%s uses only grid values for padding, margin and gap', (file) => {
    const text = readFileSync(join(ROOT, file), 'utf8');
    const off: string[] = [];
    for (const match of text.matchAll(SPACING)) {
      if (!GRID.has(Math.abs(Number(match[2])))) off.push(`${match[1]}: ${match[2]}`);
    }
    expect(off).toEqual([]);
  });
});
