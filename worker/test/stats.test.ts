import { applyD1Migrations, env } from 'cloudflare:test';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { aggregateHoleStats, recordFinish, RETENTION_DAYS, runRetention } from '../src/lib/stats';

const DAY_MS = 86_400_000;

beforeAll(async () => {
  await applyD1Migrations(env.DB, (env as unknown as { TEST_MIGRATIONS: [] }).TEST_MIGRATIONS);
});

beforeEach(async () => {
  // Each test starts from an empty database.
  await env.DB.batch([
    env.DB.prepare('DELETE FROM shots'),
    env.DB.prepare('DELETE FROM rounds'),
    env.DB.prepare('DELETE FROM players'),
    env.DB.prepare('DELETE FROM page_visits'),
    env.DB.prepare('DELETE FROM hole_stats'),
  ]);
});

/** Insert a finished (but not yet recorded) round, plus optional shots. */
async function seedRound(opts: {
  id: string;
  player: string;
  date: string;
  ranked: boolean;
  strokes: number;
  penalties?: number;
  startedAt?: number;
  finishedAt?: number;
  shots?: [from: number, to: number][];
}): Promise<void> {
  const now = opts.finishedAt ?? Date.now();
  await env.DB.prepare('INSERT OR IGNORE INTO players (id, created_at) VALUES (?, ?)')
    .bind(opts.player, now)
    .run();
  await env.DB.prepare(
    `INSERT INTO rounds (id, player_id, hole_date, ranked, started_at, finished_at,
       current_idx, current_title, strokes, penalties, result)
     VALUES (?, ?, ?, ?, ?, ?, 2, 'Target', ?, ?, 'holed')`,
  )
    .bind(
      opts.id,
      opts.player,
      opts.date,
      opts.ranked ? 1 : 0,
      opts.startedAt ?? now,
      now,
      opts.strokes,
      opts.penalties ?? 0,
    )
    .run();
  const shots = opts.shots ?? [];
  for (let i = 0; i < shots.length; i++) {
    const [from, to] = shots[i]!;
    await env.DB.prepare(
      `INSERT INTO shots (round_id, shot_no, from_idx, to_idx, to_title, lie, created_at)
       VALUES (?, ?, ?, ?, 'X', 'fairway', ?)`,
    )
      .bind(opts.id, i + 1, from, to, now)
      .run();
  }
}

describe('recordFinish', () => {
  it('folds a ranked finish into streak, games played and page visits, exactly once', async () => {
    await seedRound({
      id: 'r1',
      player: 'p1',
      date: '2026-12-01',
      ranked: true,
      strokes: 3,
      shots: [
        [0, 1],
        [1, 2],
      ],
    });

    await recordFinish(env, 'r1', Date.now());

    const player = await env.DB.prepare(
      'SELECT games_played, streak_current, streak_best, last_date FROM players WHERE id = ?',
    )
      .bind('p1')
      .first<{
        games_played: number;
        streak_current: number;
        streak_best: number;
        last_date: string;
      }>();
    expect(player).toMatchObject({
      games_played: 1,
      streak_current: 1,
      streak_best: 1,
      last_date: '2026-12-01',
    });

    // Pages 0, 1, 2 each got one finisher.
    const visits = await env.DB.prepare(
      'SELECT page_idx, finishers FROM page_visits WHERE hole_date = ? ORDER BY page_idx',
    )
      .bind('2026-12-01')
      .all<{ page_idx: number; finishers: number }>();
    expect(visits.results).toEqual([
      { page_idx: 0, finishers: 1 },
      { page_idx: 1, finishers: 1 },
      { page_idx: 2, finishers: 1 },
    ]);

    // A replay is a no-op: counts stay put.
    await recordFinish(env, 'r1', Date.now());
    const again = await env.DB.prepare('SELECT games_played FROM players WHERE id = ?')
      .bind('p1')
      .first<{ games_played: number }>();
    expect(again?.games_played).toBe(1);
  });

  it('advances a streak across consecutive days and resets after a gap', async () => {
    await seedRound({ id: 'a1', player: 'p2', date: '2026-12-01', ranked: true, strokes: 3 });
    await recordFinish(env, 'a1', Date.now());
    await seedRound({ id: 'a2', player: 'p2', date: '2026-12-02', ranked: true, strokes: 3 });
    await recordFinish(env, 'a2', Date.now());

    let p = await env.DB.prepare('SELECT streak_current, streak_best FROM players WHERE id = ?')
      .bind('p2')
      .first<{ streak_current: number; streak_best: number }>();
    expect(p).toMatchObject({ streak_current: 2, streak_best: 2 });

    // Skip 2026-12-03, play 2026-12-04: streak restarts at 1, best stays 2.
    await seedRound({ id: 'a3', player: 'p2', date: '2026-12-04', ranked: true, strokes: 3 });
    await recordFinish(env, 'a3', Date.now());
    p = await env.DB.prepare('SELECT streak_current, streak_best FROM players WHERE id = ?')
      .bind('p2')
      .first<{ streak_current: number; streak_best: number }>();
    expect(p).toMatchObject({ streak_current: 1, streak_best: 2 });
  });

  it('counts a practice finish toward games played only, not streak or page visits', async () => {
    await seedRound({
      id: 'pr1',
      player: 'p3',
      date: '2026-12-01',
      ranked: false,
      strokes: 4,
      shots: [[0, 2]],
    });
    await recordFinish(env, 'pr1', Date.now());
    const p = await env.DB.prepare(
      'SELECT games_played, streak_current, last_date FROM players WHERE id = ?',
    )
      .bind('p3')
      .first<{ games_played: number; streak_current: number; last_date: string | null }>();
    expect(p).toMatchObject({ games_played: 1, streak_current: 0, last_date: null });
    const visits = await env.DB.prepare('SELECT COUNT(*) AS n FROM page_visits').first<{
      n: number;
    }>();
    expect(visits?.n).toBe(0);
  });
});

describe('aggregateHoleStats', () => {
  it('keeps rarity pending below 100 finishers, then computes it once the field is large enough', async () => {
    const date = '2026-12-10';
    // 99 finishers: below the threshold.
    for (let i = 0; i < 99; i++) {
      await seedRound({ id: `s${i}`, player: `pp${i}`, date, ranked: true, strokes: 4 });
    }
    await aggregateHoleStats(env, Date.now());
    let stats = await env.DB.prepare('SELECT finishers FROM hole_stats WHERE hole_date = ?')
      .bind(date)
      .first<{ finishers: number }>();
    expect(stats?.finishers).toBe(99);
    let row = await env.DB.prepare('SELECT rarity FROM rounds WHERE id = ?')
      .bind('s0')
      .first<{ rarity: number | null }>();
    expect(row?.rarity).toBeNull();

    // A 100th finisher crosses the threshold; now rarity is written for everyone.
    await seedRound({ id: 'birdie', player: 'ace', date, ranked: true, strokes: 2 });
    await aggregateHoleStats(env, Date.now());

    stats = await env.DB.prepare('SELECT finishers FROM hole_stats WHERE hole_date = ?')
      .bind(date)
      .first<{ finishers: number }>();
    expect(stats?.finishers).toBe(100);

    // The lone score-2 round beat the field: 1 of 100 at-or-below -> rarity 1.
    row = await env.DB.prepare('SELECT rarity FROM rounds WHERE id = ?')
      .bind('birdie')
      .first<{ rarity: number | null }>();
    expect(row?.rarity).toBe(1);
    // Everyone else scored 4: all 100 are at-or-below -> rarity 100.
    const common = await env.DB.prepare('SELECT rarity FROM rounds WHERE id = ?')
      .bind('s0')
      .first<{ rarity: number | null }>();
    expect(common?.rarity).toBe(100);
  });
});

describe('runRetention', () => {
  it('deletes rounds, shots and tallies older than the retention window, keeping players and recent rows', async () => {
    const now = Date.now();
    const old = now - (RETENTION_DAYS + 1) * DAY_MS;
    const oldDate = new Date(old).toISOString().slice(0, 10);
    const recentDate = new Date(now).toISOString().slice(0, 10);

    await seedRound({
      id: 'old',
      player: 'keep',
      date: oldDate,
      ranked: true,
      strokes: 3,
      startedAt: old,
      finishedAt: old,
      shots: [[0, 2]],
    });
    await seedRound({
      id: 'new',
      player: 'keep',
      date: recentDate,
      ranked: true,
      strokes: 3,
      shots: [[0, 2]],
    });
    await env.DB.prepare(
      'INSERT INTO page_visits (hole_date, page_idx, finishers) VALUES (?, 0, 5)',
    )
      .bind(oldDate)
      .run();
    await env.DB.prepare(
      "INSERT INTO hole_stats (hole_date, finishers, score_spread, updated_at) VALUES (?, 5, '{}', ?)",
    )
      .bind(oldDate, old)
      .run();

    await runRetention(env, now);

    expect(
      (await env.DB.prepare('SELECT COUNT(*) AS n FROM rounds').first<{ n: number }>())?.n,
    ).toBe(1);
    expect(
      (await env.DB.prepare('SELECT COUNT(*) AS n FROM shots').first<{ n: number }>())?.n,
    ).toBe(1);
    expect(
      (await env.DB.prepare('SELECT COUNT(*) AS n FROM page_visits').first<{ n: number }>())?.n,
    ).toBe(0);
    expect(
      (await env.DB.prepare('SELECT COUNT(*) AS n FROM hole_stats').first<{ n: number }>())?.n,
    ).toBe(0);
    // The player survives retention.
    expect(
      (await env.DB.prepare('SELECT COUNT(*) AS n FROM players').first<{ n: number }>())?.n,
    ).toBe(1);
  });
});
