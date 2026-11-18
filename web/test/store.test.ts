import { beforeEach, describe, expect, it } from 'vitest';
import { savedResult, saveResult, toStored } from '../src/lib/store';

describe('local store', () => {
  beforeEach(() => localStorage.clear());

  it('saves and reads today’s result by date', () => {
    expect(savedResult('2026-12-01')).toBeNull();
    saveResult({
      holeNo: 1,
      date: '2026-12-01',
      word: 'PAR!',
      holed: true,
      strokes: 4,
      par: 4,
      seconds: 65,
      ranked: true,
      shots: [{ lie: 'fairway', title: 'A' }],
    });
    const r = savedResult('2026-12-01');
    expect(r?.word).toBe('PAR!');
    expect(r?.shots).toHaveLength(1);
  });

  it('maps a round result to a stored result', () => {
    const s = toStored('2026-12-01', 7, {
      done: true,
      holed: true,
      word: 'EAGLE!',
      strokes: 4,
      par: 6,
      seconds: 30,
      ranked: true,
      shots: [{ toTitle: 'Moon', lie: 'fairway' }],
      rarity: 'pending',
    });
    expect(s).toMatchObject({ holeNo: 7, word: 'EAGLE!', holed: true });
    expect(s.shots).toEqual([{ lie: 'fairway', title: 'Moon' }]);
  });
});
