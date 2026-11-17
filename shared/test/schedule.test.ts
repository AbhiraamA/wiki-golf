import { describe, expect, it } from 'vitest';
import { holeNumber, isValidDate, localDate, parRange, weekday } from '../src/schedule';

describe('schedule', () => {
  it('numbers holes from the epoch', () => {
    expect(holeNumber('2026-12-01', '2026-12-01')).toBe(1);
    expect(holeNumber('2026-12-02', '2026-12-01')).toBe(2);
    expect(holeNumber('2027-12-01', '2026-12-01')).toBe(366);
  });

  it('knows the weekday', () => {
    expect(weekday('2026-11-15')).toBe('Sunday');
    expect(weekday('2026-11-16')).toBe('Monday');
  });

  it('follows the difficulty schedule', () => {
    expect(parRange('2026-11-16')).toEqual([3, 4]); // Mon
    expect(parRange('2026-11-17')).toEqual([3, 4]); // Tue
    expect(parRange('2026-11-18')).toEqual([4, 5]); // Wed
    expect(parRange('2026-11-19')).toEqual([4, 5]); // Thu
    expect(parRange('2026-11-20')).toEqual([4, 6]); // Fri
    expect(parRange('2026-11-21')).toEqual([4, 6]); // Sat
    expect(parRange('2026-11-22')).toEqual([6, 7]); // Sun
  });

  it('validates dates', () => {
    expect(isValidDate('2026-02-28')).toBe(true);
    expect(isValidDate('2026-02-30')).toBe(false);
    expect(isValidDate('26-1-1')).toBe(false);
  });

  it('formats local dates', () => {
    expect(localDate(new Date(2026, 0, 5, 12))).toBe('2026-01-05');
  });
});
