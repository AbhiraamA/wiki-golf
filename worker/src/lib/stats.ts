/** Phase 4: fold finished rounds into player streaks and hole stats, plus the scheduled jobs
 * that compute rarity and prune old rows (plan.md §4, §6 "Scheduled jobs"). */

import type { Env } from '../env';
import { getRound, getShots } from './rounds';

export const RARITY_MIN_FINISHERS = 100; // rarity stays "pending" until a hole has this many
export const RETENTION_DAYS = 31; // rounds and per-hole tallies are kept this long
export const RETENTION_CRON = '41 3 * * *'; // daily; the other cron aggregates hole stats

const DAY_MS = 86_400_000;

/** The calendar date (YYYY-MM-DD) one day before `date`. */
function previousDate(date: string): string {
  return new Date(Date.parse(`${date}T00:00:00Z`) - DAY_MS).toISOString().slice(0, 10);
}

/**
 * Fold a just-finished round into durable player/hole state, exactly once.
 *
 * A conditional UPDATE claims the round (recorded_at was null); only the claimer updates the
 * player and tallies, so replays and double submits never double-count. Ranked rounds advance the
 * daily streak and the hole's per-page finisher counts; every finish bumps games_played.
 */
export async function recordFinish(env: Env, roundId: string, now: number): Promise<void> {
  const claim = await env.DB.prepare(
    'UPDATE rounds SET recorded_at = ? WHERE id = ? AND finished_at IS NOT NULL AND recorded_at IS NULL',
  )
    .bind(now, roundId)
    .run();
  if (claim.meta.changes !== 1) return; // already recorded, or not finished

  const round = await getRound(env, roundId);
  if (!round) return;

  const statements: D1PreparedStatement[] = [];

  if (round.ranked === 1) {
    const player = await env.DB.prepare(
      'SELECT streak_current, streak_best, last_date FROM players WHERE id = ?',
    )
      .bind(round.player_id)
      .first<{ streak_current: number; streak_best: number; last_date: string | null }>();
    const prev = player?.last_date ?? null;
    const continues = prev !== null && previousDate(round.hole_date) === prev;
    const sameDay = prev === round.hole_date;
    const streak = sameDay
      ? (player?.streak_current ?? 1)
      : continues
        ? (player?.streak_current ?? 0) + 1
        : 1;
    const best = Math.max(player?.streak_best ?? 0, streak);
    statements.push(
      env.DB.prepare(
        `UPDATE players
           SET games_played = games_played + 1,
               streak_current = ?, streak_best = ?, last_date = ?
         WHERE id = ?`,
      ).bind(streak, best, round.hole_date, round.player_id),
    );
    // Per-page finisher tallies (ranked field only) feed route popularity and rarity context.
    const shots = await getShots(env, round.id);
    const visited = new Set<number>();
    for (const s of shots) {
      visited.add(s.from_idx);
      visited.add(s.to_idx);
    }
    for (const idx of visited) {
      statements.push(
        env.DB.prepare(
          `INSERT INTO page_visits (hole_date, page_idx, finishers) VALUES (?, ?, 1)
             ON CONFLICT(hole_date, page_idx) DO UPDATE SET finishers = finishers + 1`,
        ).bind(round.hole_date, idx),
      );
    }
  } else {
    statements.push(
      env.DB.prepare('UPDATE players SET games_played = games_played + 1 WHERE id = ?').bind(
        round.player_id,
      ),
    );
  }

  await env.DB.batch(statements);
}

/**
 * For each hole with ranked finishers, write hole_stats (finisher count + score spread) and, once
 * the field reaches RARITY_MIN_FINISHERS, set each finisher's rarity: the percentage of finishers
 * who scored that well or better (so a low number means a rare, strong result).
 */
export async function aggregateHoleStats(env: Env, now: number): Promise<void> {
  const dates = await env.DB.prepare(
    'SELECT DISTINCT hole_date FROM rounds WHERE ranked = 1 AND finished_at IS NOT NULL',
  ).all<{ hole_date: string }>();

  for (const { hole_date } of dates.results) {
    const rows = await env.DB.prepare(
      'SELECT id, strokes + penalties AS score FROM rounds WHERE hole_date = ? AND ranked = 1 AND finished_at IS NOT NULL',
    )
      .bind(hole_date)
      .all<{ id: string; score: number }>();
    const finishers = rows.results.length;
    if (finishers === 0) continue;

    const spread: Record<number, number> = {};
    for (const r of rows.results) spread[r.score] = (spread[r.score] ?? 0) + 1;

    const statements: D1PreparedStatement[] = [
      env.DB.prepare(
        `INSERT INTO hole_stats (hole_date, finishers, score_spread, updated_at)
           VALUES (?, ?, ?, ?)
         ON CONFLICT(hole_date) DO UPDATE SET
           finishers = excluded.finishers,
           score_spread = excluded.score_spread,
           updated_at = excluded.updated_at`,
      ).bind(hole_date, finishers, JSON.stringify(spread), now),
    ];

    if (finishers >= RARITY_MIN_FINISHERS) {
      // atOrBelow[s] = how many finishers scored s or better (fewer strokes).
      const scores = Object.keys(spread)
        .map(Number)
        .sort((a, b) => a - b);
      const atOrBelow = new Map<number, number>();
      let running = 0;
      for (const s of scores) {
        running += spread[s] ?? 0;
        atOrBelow.set(s, running);
      }
      for (const r of rows.results) {
        const rarity = Math.max(
          1,
          Math.round((100 * (atOrBelow.get(r.score) ?? finishers)) / finishers),
        );
        statements.push(
          env.DB.prepare('UPDATE rounds SET rarity = ? WHERE id = ?').bind(rarity, r.id),
        );
      }
    }
    await env.DB.batch(statements);
  }
}

/** Delete rounds (and their shots) and per-hole tallies older than RETENTION_DAYS. Players stay. */
export async function runRetention(env: Env, now: number): Promise<void> {
  const cutoffMs = now - RETENTION_DAYS * DAY_MS;
  const cutoffDate = new Date(cutoffMs).toISOString().slice(0, 10);
  await env.DB.batch([
    env.DB.prepare(
      'DELETE FROM shots WHERE round_id IN (SELECT id FROM rounds WHERE started_at < ?)',
    ).bind(cutoffMs),
    env.DB.prepare('DELETE FROM rounds WHERE started_at < ?').bind(cutoffMs),
    env.DB.prepare('DELETE FROM page_visits WHERE hole_date < ?').bind(cutoffDate),
    env.DB.prepare('DELETE FROM hole_stats WHERE hole_date < ?').bind(cutoffDate),
  ]);
}

/** Scheduled entry point: the daily cron prunes; any other cron aggregates stats and rarity. */
export async function runScheduled(cron: string, env: Env, now: number): Promise<void> {
  if (cron === RETENTION_CRON) await runRetention(env, now);
  else await aggregateHoleStats(env, now);
}
