/** Share text for a finished round: a headline line and one square per shot. No page names. */

import type { Lie } from '@wiki-golf/shared';

const MARK: Record<Lie, string> = {
  fairway: '🟩',
  rough: '🟫',
  bunker: '🟨',
  holed: '⛳',
  out_of_bounds: '🟥',
};

export function shareText(
  holeNo: number,
  word: string,
  strokes: number,
  par: number,
  shots: { lie: Lie }[],
): string {
  const squares = shots.map((s) => MARK[s.lie]).join('');
  return `Wiki Golf ${holeNo} · ${word} (${strokes} on a par ${par})\n${squares}`;
}

export async function copyShare(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
