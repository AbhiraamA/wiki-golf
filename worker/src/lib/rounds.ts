/** Round state in D1: create, apply a shot, mulligan, caddie, finish (plan.md §6). */

import { lieFor, resultWord, type Lie, type PageRef } from '@wiki-golf/shared';
import type { Env } from '../env';
import { isCurrent } from './dates';
import type { HoleRecord } from './holes';
import { getRevisionHtml, linkTitles } from './pages';
import { pageByIdx, resolveTitle, type SnapshotMeta } from './snapshot';

export interface Round {
  id: string;
  player_id: string;
  hole_date: string;
  ranked: number;
  started_at: number;
  first_shot_at: number | null;
  finished_at: number | null;
  current_idx: number;
  current_title: string;
  strokes: number;
  penalties: number;
  mulligan_used: number;
  result: string | null;
  rarity: number | null;
}

export interface Shot {
  round_id: string;
  shot_no: number;
  from_idx: number;
  to_idx: number;
  to_title: string;
  lie: Lie;
  created_at: number;
}

export type ShotError =
  | 'round_done'
  | 'wrong_page'
  | 'bad_shot_number'
  | 'link_not_on_page'
  | 'unknown_link'
  | 'impossible_shot';

export interface ShotResult {
  lie: Lie;
  strokes: number; // total score so far (shots + penalties)
  toPin: number;
  holed: boolean;
  done: boolean;
  page: PageRef;
}

export const score = (r: Round): number => r.strokes + r.penalties;

export async function getRound(env: Env, id: string): Promise<Round | null> {
  return env.DB.prepare('SELECT * FROM rounds WHERE id = ?').bind(id).first<Round>();
}

/** Reload a round that must exist (just written); throws if it has vanished. */
async function reloadRound(env: Env, id: string): Promise<Round> {
  const round = await getRound(env, id);
  if (!round) throw new Error(`round ${id} not found after write`);
  return round;
}

export async function getShots(env: Env, roundId: string): Promise<Shot[]> {
  const res = await env.DB.prepare('SELECT * FROM shots WHERE round_id = ? ORDER BY shot_no')
    .bind(roundId)
    .all<Shot>();
  return res.results;
}

/** Create a round. Ranked iff the date is current and the player has no round for it yet. */
export async function createRound(
  env: Env,
  playerId: string,
  hole: HoleRecord,
  now: number,
): Promise<Round> {
  const prior = await env.DB.prepare(
    'SELECT COUNT(*) AS n FROM rounds WHERE player_id = ? AND hole_date = ?',
  )
    .bind(playerId, hole.date)
    .first<{ n: number }>();
  const wantRanked = isCurrent(hole.date, now) && (prior?.n ?? 0) === 0;
  const id = crypto.randomUUID();
  const insert = (ranked: number) =>
    env.DB.prepare(
      `INSERT INTO rounds (id, player_id, hole_date, ranked, started_at, current_idx, current_title)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    )
      .bind(id, playerId, hole.date, ranked, now, hole.start.idx, hole.start.title)
      .run();
  try {
    await insert(wantRanked ? 1 : 0);
  } catch {
    // Unique ranked index lost a race: fall back to a practice round.
    await insert(0);
  }
  return reloadRound(env, id);
}

async function currentPageLinks(env: Env, revId: number): Promise<Set<string> | null> {
  const html = await getRevisionHtml(env, revId);
  return html ? new Set(linkTitles(html)) : null;
}

/** Apply shot `body` to a round. Returns a ShotResult or a typed error. */
export async function applyShot(
  env: Env,
  round: Round,
  hole: HoleRecord,
  meta: SnapshotMeta,
  dist: Uint8Array,
  body: { shotNo: number; fromIdx: number; linkTitle: string },
  now: number,
): Promise<ShotResult | { error: ShotError }> {
  if (round.finished_at !== null) return { error: 'round_done' };

  const shots = await getShots(env, round.id);
  const nextNo = shots.length + 1;
  const lastShot = shots.at(-1);
  if (lastShot && body.shotNo === shots.length) {
    return replay(env, round, hole, meta, dist, lastShot);
  }
  if (body.shotNo !== nextNo) return { error: 'bad_shot_number' };
  if (body.fromIdx !== round.current_idx) return { error: 'wrong_page' };

  const fromPage = await pageByIdx(env, meta, round.current_idx);
  if (!fromPage) return { error: 'wrong_page' };
  const links = await currentPageLinks(env, fromPage.revId);
  const wanted = body.linkTitle.trim().replace(/ /g, '_');
  if (!links || !links.has(wanted)) return { error: 'link_not_on_page' };

  const resolved = await resolveTitle(env, meta, wanted);
  if (!resolved) return { error: 'unknown_link' };
  const toIdx = resolved.idx;
  const fromD = dist[round.current_idx] ?? 255;
  const toD = dist[toIdx] ?? 255;
  if (toD < fromD - 1) return { error: 'impossible_shot' }; // no real link gets >1 click closer

  const lie = lieFor(fromD, toD);
  const toPage = await pageByIdx(env, meta, toIdx);
  if (!toPage) return { error: 'unknown_link' };
  const holed = toIdx === hole.target.idx;
  const newStrokes = round.strokes + 1;
  const newScore = newStrokes + round.penalties;
  const done = holed || newScore >= hole.pickUp;
  const finishedAt = done ? now : null;
  const result = holed ? 'holed' : newScore >= hole.pickUp ? 'pickup' : null;

  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO shots (round_id, shot_no, from_idx, to_idx, to_title, lie, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ).bind(round.id, nextNo, round.current_idx, toIdx, toPage.title, lie, now),
    env.DB.prepare(
      `UPDATE rounds SET current_idx = ?, current_title = ?, strokes = ?,
         first_shot_at = COALESCE(first_shot_at, ?), finished_at = ?, result = ?
       WHERE id = ?`,
    ).bind(toIdx, toPage.title, newStrokes, now, finishedAt, result, round.id),
  ]);

  return { lie, strokes: newScore, toPin: toD, holed, done, page: toPage };
}

async function replay(
  env: Env,
  round: Round,
  hole: HoleRecord,
  meta: SnapshotMeta,
  dist: Uint8Array,
  shot: Shot,
): Promise<ShotResult> {
  const page = (await pageByIdx(env, meta, shot.to_idx)) ?? {
    idx: shot.to_idx,
    title: shot.to_title,
    revId: 0,
  };
  return {
    lie: shot.lie,
    strokes: round.strokes + round.penalties,
    toPin: dist[shot.to_idx] ?? 255,
    holed: shot.to_idx === hole.target.idx,
    done: round.finished_at !== null,
    page,
  };
}

export async function mulligan(
  env: Env,
  round: Round,
  meta: SnapshotMeta,
): Promise<Round | { error: 'no_mulligan' }> {
  if (round.finished_at !== null || round.mulligan_used || round.strokes < 1) {
    return { error: 'no_mulligan' };
  }
  const shots = await getShots(env, round.id);
  const last = shots.at(-1);
  if (!last) return { error: 'no_mulligan' };
  const fromPage = await pageByIdx(env, meta, last.from_idx);
  const fromTitle = fromPage?.title ?? last.to_title;
  await env.DB.batch([
    env.DB.prepare('DELETE FROM shots WHERE round_id = ? AND shot_no = ?').bind(
      round.id,
      last.shot_no,
    ),
    env.DB.prepare(
      `UPDATE rounds SET current_idx = ?, current_title = ?, strokes = strokes - 1,
         mulligan_used = 1, result = NULL, finished_at = NULL WHERE id = ?`,
    ).bind(last.from_idx, fromTitle, round.id),
  ]);
  return reloadRound(env, round.id);
}

export interface CaddieResult {
  hint: string | null;
  strokes: number;
  done: boolean;
}

/** Highlight the first of the given links that gets closer; costs one penalty either way. */
export async function caddie(
  env: Env,
  round: Round,
  hole: HoleRecord,
  meta: SnapshotMeta,
  dist: Uint8Array,
  linkTitles: string[],
  now: number,
): Promise<CaddieResult | { error: 'round_done' }> {
  if (round.finished_at !== null) return { error: 'round_done' };
  const fromD = dist[round.current_idx] ?? 255;
  let hint: string | null = null;
  for (const title of linkTitles.slice(0, 40)) {
    const resolved = await resolveTitle(env, meta, title.trim().replace(/ /g, '_'));
    if (resolved && (dist[resolved.idx] ?? 255) < fromD) {
      hint = title;
      break;
    }
  }
  const newPenalties = round.penalties + 1;
  const newScore = round.strokes + newPenalties;
  const done = newScore >= hole.pickUp;
  await env.DB.prepare(
    `UPDATE rounds SET penalties = ?, first_shot_at = COALESCE(first_shot_at, ?),
       finished_at = ?, result = ? WHERE id = ?`,
  )
    .bind(newPenalties, now, done ? now : null, done ? 'pickup' : null, round.id)
    .run();
  return { hint, strokes: newScore, done };
}

export interface RoundResult {
  done: true;
  holed: boolean;
  word: string;
  strokes: number;
  par: number;
  seconds: number;
  ranked: boolean;
  shots: { toTitle: string; lie: Lie }[];
  rarity: number | 'pending';
}

export async function roundResult(
  env: Env,
  round: Round,
  hole: HoleRecord,
): Promise<RoundResult | null> {
  if (round.finished_at === null) return null;
  const shots = await getShots(env, round.id);
  const holed = round.result === 'holed';
  const total = score(round);
  const start = round.first_shot_at ?? round.finished_at;
  return {
    done: true,
    holed,
    word: resultWord(holed, total, hole.par),
    strokes: total,
    par: hole.par,
    seconds: Math.max(0, Math.round((round.finished_at - start) / 1000)),
    ranked: round.ranked === 1,
    shots: shots.map((s) => ({ toTitle: s.to_title, lie: s.lie })),
    rarity: round.rarity ?? 'pending',
  };
}
