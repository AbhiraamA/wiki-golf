/** Load hole records and the index from R2, with dev/prod status gating (plan.md §4, §6). */

import type { HoleInfo } from '@wiki-golf/shared';
import type { Env } from '../env';
import { isServable } from './dates';

export interface HoleRecord extends HoleInfo {
  snap: string;
  shortest: number;
  status: 'queued' | 'approved';
}

function servableStatus(env: Env): Set<string> {
  // Production serves only approved holes; dev also serves queued ones.
  return env.ENVIRONMENT === 'production' ? new Set(['approved']) : new Set(['approved', 'queued']);
}

export async function loadHole(env: Env, date: string): Promise<HoleRecord | null> {
  if (!isServable(date)) return null;
  const obj = await env.BUCKET.get(`${env.WIKI}/holes/${date}.json`);
  if (!obj) return null;
  const rec = (await obj.json()) as HoleRecord;
  if (!servableStatus(env).has(rec.status)) return null;
  return rec;
}

/** Public hole info (never includes distances or the shortest route). */
export function publicHole(rec: HoleRecord): HoleInfo {
  const info: HoleInfo = {
    holeNo: rec.holeNo,
    date: rec.date,
    wiki: rec.wiki,
    par: rec.par,
    pickUp: rec.pickUp,
    start: rec.start,
    target: rec.target,
  };
  if (rec.badge) info.badge = rec.badge;
  return info;
}
