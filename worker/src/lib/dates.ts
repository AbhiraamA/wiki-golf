/** Date-window helpers. A date is playable if it is "today" somewhere on Earth, or past. */

const DAY = 86_400_000;

function ymd(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** Latest date that is "today" somewhere (UTC+14). */
export function latestToday(now: number = Date.now()): string {
  return ymd(now + 14 * 3_600_000);
}

/** Earliest date that is still "today" somewhere (UTC-12). */
export function earliestToday(now: number = Date.now()): string {
  return ymd(now - 12 * 3_600_000);
}

/** A hole date may be served if it is today somewhere or in the past (not a future date). */
export function isServable(date: string, now: number = Date.now()): boolean {
  return date <= latestToday(now);
}

/** A round on this date counts as ranked-eligible only while the date is current (today somewhere). */
export function isCurrent(date: string, now: number = Date.now()): boolean {
  return date >= earliestToday(now) && date <= latestToday(now);
}

export { DAY };
