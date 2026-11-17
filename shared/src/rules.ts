/** Game rules shared by the web app and the Worker. See plan.md section 1. */

import type { Lie } from './types';

/** Distance value meaning "no route to the target". */
export const NO_ROUTE = 255;

/** Par is the shortest route in clicks + 1. */
export function parFromShortest(shortest: number): number {
  return shortest + 1;
}

/** At double par the round ends with a score of double par. */
export function pickUpAt(par: number): number {
  return par * 2;
}

/** Lie for a shot from a page at distance `from` to a page at distance `to`. */
export function lieFor(from: number, to: number): Lie {
  if (to === 0) return 'holed';
  if (to === NO_ROUTE) return 'out_of_bounds';
  if (from === NO_ROUTE || to < from) return 'fairway';
  if (to === from) return 'rough';
  return 'bunker';
}

/** Result word for a finished round. */
export function resultWord(holed: boolean, strokes: number, par: number): string {
  if (!holed) return 'PICKED UP';
  const diff = strokes - par;
  if (diff <= -3) return 'ALBATROSS!';
  if (diff === -2) return 'EAGLE!';
  if (diff === -1) return 'BIRDIE!';
  if (diff === 0) return 'PAR!';
  if (diff === 1) return 'BOGEY';
  if (diff === 2) return 'DOUBLE BOGEY';
  return `+${diff}`;
}
