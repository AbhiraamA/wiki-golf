/** Plain date helpers (kept out of the runes module so Date instances aren't flagged reactive). */

import { HOLE_EPOCH } from '@wiki-golf/shared';

const DAY = 86_400_000;

function iso(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** Past hole dates (HOLE_EPOCH .. yesterday), most recent first, capped for the archive list. */
export function pastDates(today: string, limit = 30): string[] {
  const out: string[] = [];
  let t = Date.parse(`${today}T00:00:00Z`) - DAY;
  const epoch = Date.parse(`${HOLE_EPOCH}T00:00:00Z`);
  while (t >= epoch && out.length < limit) {
    out.push(iso(t));
    t -= DAY;
  }
  return out;
}

/** The Monday (UTC) of the week containing `date`, as YYYY-MM-DD. */
export function weekStart(date: string): string {
  const t = Date.parse(`${date}T00:00:00Z`);
  const dow = (new Date(t).getUTCDay() + 6) % 7; // 0 = Monday
  return iso(t - dow * DAY);
}
