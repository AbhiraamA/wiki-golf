/** Browser-local persistence: today's result and recent history. Works with storage disabled. */

import type { RoundResult } from './api';

const KEY = 'wikigolf-v1';

export interface Saved {
  results: Record<string, StoredResult>; // keyed by hole date
}

export interface StoredResult {
  holeNo: number;
  date: string;
  word: string;
  holed: boolean;
  strokes: number;
  par: number;
  seconds: number;
  ranked: boolean;
  shots: { lie: import('@wiki-golf/shared').Lie; title: string }[];
}

function read(): Saved {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as Saved;
  } catch {
    /* storage unavailable */
  }
  return { results: {} };
}

function write(data: Saved): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    /* storage unavailable: the server remains the source of truth */
  }
}

export function savedResult(date: string): StoredResult | null {
  return read().results[date] ?? null;
}

export function saveResult(r: StoredResult): void {
  const data = read();
  data.results[r.date] = r;
  write(data);
}

export function toStored(date: string, holeNo: number, result: RoundResult): StoredResult {
  return {
    holeNo,
    date,
    word: result.word ?? '',
    holed: result.holed ?? false,
    strokes: result.strokes ?? 0,
    par: result.par ?? 0,
    seconds: result.seconds ?? 0,
    ranked: result.ranked ?? false,
    shots: (result.shots ?? []).map((sh) => ({ lie: sh.lie, title: sh.toTitle })),
  };
}
