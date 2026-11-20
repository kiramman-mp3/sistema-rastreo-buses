import type { Fine } from '../api/types';
import { APPEAL_MAX, appealText, fineStatus, hoursToAppeal, money, sortFines } from './format';

function fine(over: Partial<Fine> = {}): Fine {
  return {
    id: 1,
    number: 'MUL-0001',
    type: 'Exceso de velocidad',
    rule: 'speeding',
    state: 'fined',
    occurred_at: '2026-11-19T12:00:00Z',
    vehicle: 'Bus 1',
    route: 'L1',
    headline: '82 km/h',
    summary: 'Por encima de 70 km/h',
    amount: 25,
    currency: '$',
    simulated: false,
    can_appeal: true,
    appeal_deadline: '2026-11-22T12:00:00Z',
    appeal_text: null,
    appeal_date: null,
    appeal_result: null,
    appeal_answer: null,
    checks: [],
    ...over,
  };
}

describe('appealText', () => {
  it('trims the statement and refuses an empty or too long one', () => {
    expect(appealText('  Iba al hospital  ')).toBe('Iba al hospital');
    expect(appealText('   ')).toBeNull();
    expect(appealText('x'.repeat(APPEAL_MAX))).toHaveLength(APPEAL_MAX);
    expect(appealText('x'.repeat(APPEAL_MAX + 1))).toBeNull();
  });
});

describe('fineStatus', () => {
  it('follows the appeal', () => {
    expect(fineStatus(fine())).toBe('fined');
    expect(fineStatus(fine({ state: 'appealed', can_appeal: false }))).toBe('appealed');
    expect(fineStatus(fine({ state: 'fined', appeal_result: 'rejected' }))).toBe('rejected');
    expect(fineStatus(fine({ state: 'discarded', appeal_result: 'accepted' }))).toBe('accepted');
  });
});

describe('hoursToAppeal', () => {
  const now = Date.parse('2026-11-21T11:30:00Z');
  it('rounds up the hours left', () => {
    expect(hoursToAppeal(fine(), now)).toBe(25);
  });
  it('is zero when the time is over or the fine cannot be appealed', () => {
    expect(hoursToAppeal(fine({ appeal_deadline: '2026-11-21T11:00:00Z' }), now)).toBe(0);
    expect(hoursToAppeal(fine({ can_appeal: false }), now)).toBe(0);
    expect(hoursToAppeal(fine({ appeal_deadline: null }), now)).toBe(0);
  });
});

describe('money', () => {
  it('shows two decimals after the symbol', () => {
    expect(money(25, '$', 'en-US')).toBe('$25.00');
    expect(money(Number.NaN, '$', 'en-US')).toBe('$0.00');
  });
});

describe('sortFines', () => {
  it('puts the ones to answer first, then the newest', () => {
    const old = fine({ id: 1, occurred_at: '2026-11-01T12:00:00Z', can_appeal: false });
    const recent = fine({ id: 2, occurred_at: '2026-11-19T12:00:00Z', can_appeal: false });
    const open = fine({ id: 3, occurred_at: '2026-11-10T12:00:00Z', can_appeal: true });
    expect(sortFines([old, recent, open]).map((f) => f.id)).toEqual([3, 2, 1]);
  });
});
