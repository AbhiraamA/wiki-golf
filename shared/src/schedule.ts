/** Calendar helpers: hole numbers, weekdays and the difficulty schedule. Dates are `YYYY-MM-DD`. */

import { HOLE_EPOCH } from './config';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 86_400_000;

export const WEEKDAYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const;
export type Weekday = (typeof WEEKDAYS)[number];

/** Parse a `YYYY-MM-DD` date to UTC midnight epoch ms. Throws on bad input. */
export function parseDate(date: string): number {
  if (!DATE_RE.test(date)) throw new Error(`Invalid date: ${date}`);
  const ms = Date.parse(`${date}T00:00:00Z`);
  if (Number.isNaN(ms) || new Date(ms).toISOString().slice(0, 10) !== date) {
    throw new Error(`Invalid date: ${date}`);
  }
  return ms;
}

export function isValidDate(date: string): boolean {
  try {
    parseDate(date);
    return true;
  } catch {
    return false;
  }
}

/** Hole number for a date: days since HOLE_EPOCH + 1. */
export function holeNumber(date: string, epoch: string = HOLE_EPOCH): number {
  return Math.round((parseDate(date) - parseDate(epoch)) / DAY_MS) + 1;
}

export function weekday(date: string): Weekday {
  return WEEKDAYS[new Date(parseDate(date)).getUTCDay()] as Weekday;
}

const MONTHS = [
  'JAN',
  'FEB',
  'MAR',
  'APR',
  'MAY',
  'JUN',
  'JUL',
  'AUG',
  'SEP',
  'OCT',
  'NOV',
  'DEC',
] as const;

/** Uppercase month + day, e.g. "NOV 19" — shown on the tee screen before launch. */
export function monthDay(date: string): string {
  const d = new Date(parseDate(date));
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

/** Inclusive par range for a date, per the difficulty schedule. */
export function parRange(date: string): readonly [min: number, max: number] {
  switch (new Date(parseDate(date)).getUTCDay()) {
    case 1:
    case 2:
      return [3, 4];
    case 3:
    case 4:
      return [4, 5];
    case 5:
    case 6:
      return [4, 6];
    default:
      return [6, 7];
  }
}

export function isLongHole(date: string): boolean {
  return weekday(date) === 'Sunday';
}

/** Local calendar date (`YYYY-MM-DD`) in the viewer's time zone. */
export function localDate(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}
