import { APP_VERSION, isValidDate } from '@wiki-golf/shared';
import { Hono } from 'hono';
import { newPlayerId, readPlayerId, setCookieHeader } from './lib/cookie';
import { loadDistances } from './lib/distances';
import { loadHole, publicHole, type HoleRecord } from './lib/holes';
import { getRevisionHtml } from './lib/pages';
import {
  applyShot,
  caddie,
  createRound,
  getRound,
  mulligan,
  roundResult,
  type Round,
} from './lib/rounds';
import { loadMeta, pageByIdx, resolveTitle, type SnapshotMeta } from './lib/snapshot';
import { allowRestoreAttempt, createBackupCode, restoreByCode } from './lib/backup';
import { recordFinish, runScheduled } from './lib/stats';
import type { Env } from './env';

import type { Context } from 'hono';

const app = new Hono<{ Bindings: Env }>();

// ---- helpers ----------------------------------------------------------------

type Ctx = Context<{ Bindings: Env }>;

const bad = (c: Ctx, error: string, status = 400) =>
  c.json({ error }, status as 400 | 401 | 403 | 404 | 422 | 500);

async function player(c: Ctx): Promise<string | null> {
  return readPlayerId(c.req.raw, c.env.COOKIE_SECRET);
}

/** Load the hole for a date plus its snapshot meta and distance array, or null if unavailable. */
async function holeContext(
  env: Env,
  date: string,
): Promise<{ hole: HoleRecord; meta: SnapshotMeta; dist: Uint8Array } | null> {
  const hole = await loadHole(env, date);
  if (!hole) return null;
  const [meta, dist] = await Promise.all([loadMeta(env, hole.snap), loadDistances(env, date)]);
  if (!meta || !dist) return null;
  return { hole, meta, dist };
}

async function ownedRound(c: Ctx): Promise<Round | Response> {
  const pid = await player(c);
  if (!pid) return bad(c, 'no_player', 401);
  const round = await getRound(c.env, c.req.param('id') ?? '');
  if (!round) return bad(c, 'round_not_found', 404);
  if (round.player_id !== pid) return bad(c, 'forbidden', 403);
  return round;
}

// ---- routes -----------------------------------------------------------------

// Security headers on every API (JSON) response.
app.use('/api/*', async (c, next) => {
  await next();
  c.res.headers.set('X-Content-Type-Options', 'nosniff');
  c.res.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
});

app.get('/api/health', (c) =>
  c.json({ ok: true, version: APP_VERSION, wiki: c.env.WIKI, environment: c.env.ENVIRONMENT }),
);

app.get('/api/hole', async (c) => {
  const date = c.req.query('date') ?? '';
  if (!isValidDate(date)) return bad(c, 'bad_date');
  const hole = await loadHole(c.env, date);
  if (!hole) return bad(c, 'no_hole', 404);
  return c.json(publicHole(hole));
});

app.get('/api/page', async (c) => {
  const title = c.req.query('title') ?? '';
  const date = c.req.query('date') ?? '';
  if (!title || !isValidDate(date)) return bad(c, 'bad_request');
  const ctx = await holeContext(c.env, date);
  if (!ctx) return bad(c, 'no_hole', 404);
  const ref = await resolveTitle(c.env, ctx.meta, title);
  if (!ref) return bad(c, 'unknown_title', 404);
  const page = await pageByIdx(c.env, ctx.meta, ref.idx);
  const html = await getRevisionHtml(c.env, ref.revId);
  if (!page || html === null) return bad(c, 'no_page', 404);
  c.header('Cache-Control', 'public, max-age=31536000, immutable');
  return c.json({ title: page.title, idx: page.idx, revId: page.revId, html });
});

app.post('/api/rounds', async (c) => {
  const body = await c.req.json<{ date?: string }>().catch(() => ({}) as { date?: string });
  const date = body.date ?? '';
  if (!isValidDate(date)) return bad(c, 'bad_date');
  const ctx = await holeContext(c.env, date);
  if (!ctx) return bad(c, 'no_hole', 404);

  let pid = await player(c);
  let setCookie = false;
  if (!pid) {
    pid = newPlayerId();
    setCookie = true;
  }
  await c.env.DB.prepare('INSERT OR IGNORE INTO players (id, created_at) VALUES (?, ?)')
    .bind(pid, Date.now())
    .run();

  const round = await createRound(c.env, pid, ctx.hole, Date.now());
  const html = await getRevisionHtml(c.env, ctx.hole.start.revId);
  if (setCookie) c.header('Set-Cookie', await setCookieHeader(pid, c.env.COOKIE_SECRET));
  return c.json({
    roundId: round.id,
    ranked: round.ranked === 1,
    hole: publicHole(ctx.hole),
    page: ctx.hole.start,
    html,
  });
});

app.post('/api/rounds/:id/shots', async (c) => {
  const round = await ownedRound(c);
  if (round instanceof Response) return round;
  const ctx = await holeContext(c.env, round.hole_date);
  if (!ctx) return bad(c, 'no_hole', 404);
  const body = await c.req.json<{ shotNo?: number; fromIdx?: number; linkTitle?: string }>();
  const { shotNo, fromIdx, linkTitle } = body;
  if (!Number.isInteger(shotNo) || !Number.isInteger(fromIdx) || typeof linkTitle !== 'string') {
    return bad(c, 'bad_request');
  }
  const out = await applyShot(
    c.env,
    round,
    ctx.hole,
    ctx.meta,
    ctx.dist,
    { shotNo: shotNo as number, fromIdx: fromIdx as number, linkTitle },
    Date.now(),
  );
  if ('error' in out) return bad(c, out.error, 422);
  if (out.done) await recordFinish(c.env, round.id, Date.now());
  const html = out.holed ? null : await getRevisionHtml(c.env, out.page.revId);
  return c.json({ ...out, html });
});

app.post('/api/rounds/:id/mulligan', async (c) => {
  const round = await ownedRound(c);
  if (round instanceof Response) return round;
  const ctx = await holeContext(c.env, round.hole_date);
  if (!ctx) return bad(c, 'no_hole', 404);
  const out = await mulligan(c.env, round, ctx.meta);
  if ('error' in out) return bad(c, out.error, 422);
  const page = await pageByIdx(c.env, ctx.meta, out.current_idx);
  const html = page ? await getRevisionHtml(c.env, page.revId) : null;
  return c.json({ page, html, strokes: out.strokes + out.penalties });
});

app.post('/api/rounds/:id/caddie', async (c) => {
  const round = await ownedRound(c);
  if (round instanceof Response) return round;
  const ctx = await holeContext(c.env, round.hole_date);
  if (!ctx) return bad(c, 'no_hole', 404);
  const body = await c.req.json<{ linkTitles?: string[] }>();
  if (!Array.isArray(body.linkTitles)) return bad(c, 'bad_request');
  const out = await caddie(
    c.env,
    round,
    ctx.hole,
    ctx.meta,
    ctx.dist,
    body.linkTitles.filter((t) => typeof t === 'string'),
    Date.now(),
  );
  if ('error' in out) return bad(c, out.error, 422);
  if (out.done) await recordFinish(c.env, round.id, Date.now());
  return c.json(out);
});

app.get('/api/rounds/:id/result', async (c) => {
  const round = await ownedRound(c);
  if (round instanceof Response) return round;
  const ctx = await holeContext(c.env, round.hole_date);
  if (!ctx) return bad(c, 'no_hole', 404);
  const result = await roundResult(c.env, round, ctx.hole);
  if (!result) return c.json({ done: false });
  return c.json(result);
});

app.get('/api/me', async (c) => {
  const pid = await player(c);
  if (!pid) return c.json({ streakCurrent: 0, streakBest: 0, gamesPlayed: 0, lastDate: null });
  const row = await c.env.DB.prepare(
    'SELECT streak_current, streak_best, games_played, last_date FROM players WHERE id = ?',
  )
    .bind(pid)
    .first<{
      streak_current: number;
      streak_best: number;
      games_played: number;
      last_date: string | null;
    }>();
  return c.json({
    streakCurrent: row?.streak_current ?? 0,
    streakBest: row?.streak_best ?? 0,
    gamesPlayed: row?.games_played ?? 0,
    lastDate: row?.last_date ?? null,
  });
});

// Create (or replace) this player's backup code; the plaintext is returned once and only its hash
// is stored. Requires an existing player.
app.post('/api/backup-code', async (c) => {
  const pid = await player(c);
  if (!pid) return bad(c, 'no_player', 401);
  const code = await createBackupCode(c.env, pid);
  if (!code) return bad(c, 'no_player', 401);
  return c.json({ code });
});

// Move this browser's cookie to the player that owns the given backup code. Throttled (no PII).
app.post('/api/restore', async (c) => {
  if (!(await allowRestoreAttempt(c.env, Date.now()))) return bad(c, 'rate_limited', 429);
  const body = await c.req.json<{ code?: string }>().catch(() => ({}) as { code?: string });
  if (typeof body.code !== 'string') return bad(c, 'bad_request');
  const pid = await restoreByCode(c.env, body.code);
  if (!pid) return bad(c, 'invalid_code', 404);
  const row = await c.env.DB.prepare(
    'SELECT streak_current, streak_best, games_played, last_date FROM players WHERE id = ?',
  )
    .bind(pid)
    .first<{
      streak_current: number;
      streak_best: number;
      games_played: number;
      last_date: string | null;
    }>();
  c.header('Set-Cookie', await setCookieHeader(pid, c.env.COOKIE_SECRET));
  return c.json({
    restored: true,
    streakCurrent: row?.streak_current ?? 0,
    streakBest: row?.streak_best ?? 0,
    gamesPlayed: row?.games_played ?? 0,
    lastDate: row?.last_date ?? null,
  });
});

app.all('/api/*', (c) => bad(c, 'not_found', 404));

// Non-API requests fall through to the static front end. Its security headers (CSP,
// nosniff, referrer) come from web/public/_headers, since the assets layer serves these
// paths directly (run_worker_first is only "/api/*").
app.all('*', (c) => c.env.ASSETS.fetch(c.req.raw));

app.onError((err, c) => {
  console.error(err);
  return c.json({ error: 'internal_error' }, 500);
});

export default {
  fetch: app.fetch,
  // Cron-driven jobs: aggregate hole stats + rarity (hourly) and prune old rows (daily).
  scheduled(event, env, ctx) {
    ctx.waitUntil(runScheduled(event.cron, env, Date.now()));
  },
} satisfies ExportedHandler<Env>;
