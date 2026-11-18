import { describe, expect, it } from 'vitest';
import { shareText } from '../src/lib/share';

describe('shareText', () => {
  it('builds the headline and one square per shot, no page names', () => {
    const text = shareText(128, 'BIRDIE!', 5, 6, [
      { lie: 'fairway' },
      { lie: 'rough' },
      { lie: 'bunker' },
      { lie: 'fairway' },
      { lie: 'holed' },
    ]);
    expect(text).toBe('Wiki Golf 128 · BIRDIE! (5 on a par 6)\n🟩🟫🟨🟩⛳');
    // No article titles anywhere: only the headline words and square emoji.
    expect(text).not.toMatch(/Octopus|Moon|Apollo/);
  });
});
