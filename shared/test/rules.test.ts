import { describe, expect, it } from 'vitest';
import { lieFor, NO_ROUTE, parFromShortest, pickUpAt, resultWord } from '../src/rules';

describe('rules', () => {
  it('derives par and pick-up', () => {
    expect(parFromShortest(5)).toBe(6);
    expect(pickUpAt(6)).toBe(12);
  });

  it('classifies lies', () => {
    expect(lieFor(3, 2)).toBe('fairway');
    expect(lieFor(3, 3)).toBe('rough');
    expect(lieFor(3, 4)).toBe('bunker');
    expect(lieFor(1, 0)).toBe('holed');
    expect(lieFor(3, NO_ROUTE)).toBe('out_of_bounds');
  });

  it('names results', () => {
    expect(resultWord(true, 6, 6)).toBe('PAR!');
    expect(resultWord(true, 5, 6)).toBe('BIRDIE!');
    expect(resultWord(true, 9, 6)).toBe('+3');
    expect(resultWord(false, 12, 6)).toBe('PICKED UP');
  });
});
