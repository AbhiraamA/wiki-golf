/**
 * Phase 0 only: a fixed sample hole so the tee screen can render before the API exists.
 * Replaced by `GET /api/hole` in Phase 3.
 */
import { holeNumber, localDate, pickUpAt, type HoleInfo } from '@wiki-golf/shared';

export function placeholderHole(date: string = localDate()): HoleInfo {
  const par = 6;
  return {
    holeNo: Math.max(1, holeNumber(date)),
    date,
    wiki: 'simplewiki',
    par,
    pickUp: pickUpAt(par),
    start: { idx: 0, title: 'Octopus', revId: 0 },
    target: { idx: 1, title: 'Apollo 11', revId: 0 },
  };
}
