import { buildReport, MESSAGE_MAX, SHORT_MAX, STACK_MAX } from './report';

const NOW = new Date('2026-11-02T20:00:00Z');

describe('error report', () => {
  test('an Error becomes its name and message, with the stack', () => {
    const error = new TypeError('x is undefined');
    const report = buildReport(error, { app: '1.0.0', screen: '/shift', now: NOW });
    expect(report.message).toBe('TypeError: x is undefined');
    expect(report.stack).toContain('TypeError');
    expect(report).toMatchObject({ app: '1.0.0', screen: '/shift', at: '2026-11-02T20:00:00.000Z' });
  });

  test('a string, an object and null are all reported', () => {
    expect(buildReport('boom', { app: 'a', now: NOW }).message).toBe('boom');
    expect(buildReport({ code: 7 }, { app: 'a', now: NOW }).message).toBe('{"code":7}');
    expect(buildReport(null, { app: 'a', now: NOW }).message).toBe('null');
    expect(buildReport(undefined, { app: 'a', now: NOW }).message).toBe('undefined');
  });

  test('something that cannot be turned into text still gives a report', () => {
    const loop: Record<string, unknown> = {};
    loop.self = loop;
    expect(buildReport(loop, { app: 'a', now: NOW }).message).toBe('[object Object]');
    expect(buildReport('   ', { app: 'a', now: NOW }).message).toBe('Unknown error');
  });

  test('everything fits the limits the server enforces', () => {
    const error = new Error('m'.repeat(2000));
    error.stack = 's'.repeat(9000);
    const report = buildReport(error, { app: 'v'.repeat(200), screen: 'p'.repeat(200), now: NOW });
    expect(report.message.length).toBeLessThanOrEqual(MESSAGE_MAX);
    expect(report.stack!.length).toBeLessThanOrEqual(STACK_MAX);
    expect(report.app.length).toBeLessThanOrEqual(SHORT_MAX);
    expect(report.screen!.length).toBeLessThanOrEqual(SHORT_MAX);
  });

  test('an optional field that is missing is left out', () => {
    const report = buildReport('boom', { app: 'a', now: NOW });
    expect('stack' in report).toBe(false);
    expect('screen' in report).toBe(false);
  });
});
