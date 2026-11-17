import { applyD1Migrations, env, SELF } from 'cloudflare:test';
import { beforeAll, describe, expect, it } from 'vitest';
import { seedFixture } from './fixture';

// Today's date (UTC) so the hole is current and the first round is ranked.
const DATE = new Date().toISOString().slice(0, 10);

beforeAll(async () => {
  await applyD1Migrations(env.DB, (env as unknown as { TEST_MIGRATIONS: [] }).TEST_MIGRATIONS);
  await seedFixture(DATE);
});

const BASE = 'https://wiki.golf';

function cookieFrom(res: Response): string {
  const raw = res.headers.get('set-cookie') ?? '';
  return raw.split(';')[0] ?? '';
}

async function post(path: string, body: unknown, cookie: string): Promise<Response> {
  return SELF.fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify(body),
  });
}

describe('full round through the API', () => {
  it('plays a hole: bunker, mulligan, caddie, holing; rejects fakes; second round is practice', async () => {
    // 1. Start a round. First round on a current date is ranked; a cookie is issued.
    const startRes = await SELF.fetch(`${BASE}/api/rounds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: DATE }),
    });
    expect(startRes.status).toBe(200);
    const start = await startRes.json<{
      roundId: string;
      ranked: boolean;
      page: { idx: number };
      html: string;
    }>();
    expect(start.ranked).toBe(true);
    expect(start.page.idx).toBe(0);
    expect(start.html).toContain('href="./Mid"');
    const cookie = cookieFrom(startRes);
    expect(cookie).toMatch(/^wg_pid=/);
    const id = start.roundId;

    // 2. A faked shot to a link that is not on the current page is rejected.
    const fake = await post(
      `/api/rounds/${id}/shots`,
      { shotNo: 1, fromIdx: 0, linkTitle: 'Target' },
      cookie,
    );
    expect(fake.status).toBe(422);
    expect((await fake.json<{ error: string }>()).error).toBe('link_not_on_page');

    // 3. A bunker: Start (d2) -> Far (d3).
    const bunker = await post(
      `/api/rounds/${id}/shots`,
      { shotNo: 1, fromIdx: 0, linkTitle: 'Far' },
      cookie,
    );
    const b = await bunker.json<{
      lie: string;
      toPin: number;
      strokes: number;
      done: boolean;
      page: { idx: number };
    }>();
    expect(b.lie).toBe('bunker');
    expect(b.toPin).toBe(3);
    expect(b.strokes).toBe(1);
    expect(b.done).toBe(false);
    expect(b.page.idx).toBe(3);

    // 4. Mulligan undoes the bunker, back to Start.
    const mull = await post(`/api/rounds/${id}/mulligan`, {}, cookie);
    const m = await mull.json<{ page: { idx: number }; strokes: number }>();
    expect(m.page.idx).toBe(0);
    expect(m.strokes).toBe(0);

    // A second mulligan is refused (one per round).
    const mull2 = await post(`/api/rounds/${id}/mulligan`, {}, cookie);
    expect(mull2.status).toBe(422);

    // 5. Caddie points to the link that gets closer (Mid), costs one penalty.
    const cad = await post(`/api/rounds/${id}/caddie`, { linkTitles: ['Far', 'Mid'] }, cookie);
    const ca = await cad.json<{ hint: string | null; strokes: number; done: boolean }>();
    expect(ca.hint).toBe('Mid');
    expect(ca.strokes).toBe(1); // one penalty so far
    expect(ca.done).toBe(false);

    // 6. Fairway: Start (d2) -> Mid (d1). Shot numbering restarted after the mulligan.
    const fairway = await post(
      `/api/rounds/${id}/shots`,
      { shotNo: 1, fromIdx: 0, linkTitle: 'Mid' },
      cookie,
    );
    const f = await fairway.json<{
      lie: string;
      toPin: number;
      strokes: number;
      page: { idx: number };
    }>();
    expect(f.lie).toBe('fairway');
    expect(f.toPin).toBe(1);
    expect(f.strokes).toBe(2); // 1 shot + 1 penalty
    expect(f.page.idx).toBe(1);

    // 7. Hole out: Mid (d1) -> Target (d0).
    const holed = await post(
      `/api/rounds/${id}/shots`,
      { shotNo: 2, fromIdx: 1, linkTitle: 'Target' },
      cookie,
    );
    const h = await holed.json<{
      lie: string;
      holed: boolean;
      done: boolean;
      strokes: number;
      html: string | null;
    }>();
    expect(h.lie).toBe('holed');
    expect(h.holed).toBe(true);
    expect(h.done).toBe(true);
    expect(h.strokes).toBe(3);
    expect(h.html).toBe(null);

    // 8. Result: par (3 on a par 3), ranked.
    const resultRes = await SELF.fetch(`${BASE}/api/rounds/${id}/result`, {
      headers: { Cookie: cookie },
    });
    const r = await resultRes.json<{
      done: boolean;
      word: string;
      strokes: number;
      ranked: boolean;
      rarity: unknown;
    }>();
    expect(r.done).toBe(true);
    expect(r.word).toBe('PAR!');
    expect(r.strokes).toBe(3);
    expect(r.ranked).toBe(true);
    expect(r.rarity).toBe('pending');

    // 9. A second round on the same date is practice, not ranked.
    const second = await post('/api/rounds', { date: DATE }, cookie);
    expect((await second.json<{ ranked: boolean }>()).ranked).toBe(false);
  });

  it('rejects a shot to a link that is not on the current page', async () => {
    // Target is not linked from Start, so claiming that shot is refused. (The distance-guard
    // against jumping more than one click closer is defensive: a valid graph never triggers it,
    // since a real link to a nearer page would itself shorten the BFS distance.)
    const startRes = await post('/api/rounds', { date: DATE }, '');
    const start = await startRes.json<{ roundId: string }>();
    const cookie = cookieFrom(startRes);
    const res = await post(
      `/api/rounds/${start.roundId}/shots`,
      { shotNo: 1, fromIdx: 0, linkTitle: 'Target' },
      cookie,
    );
    expect(res.status).toBe(422);
    expect((await res.json<{ error: string }>()).error).toBe('link_not_on_page');
  });

  it('another player cannot act on someone else’s round', async () => {
    const startRes = await post('/api/rounds', { date: DATE }, '');
    const start = await startRes.json<{ roundId: string }>();
    // No cookie -> not the owner.
    const res = await post(
      `/api/rounds/${start.roundId}/shots`,
      { shotNo: 1, fromIdx: 0, linkTitle: 'Mid' },
      '',
    );
    expect(res.status).toBe(401);
  });
});

describe('hole and page endpoints', () => {
  it('serves the public hole without distances or shortest route', async () => {
    const res = await SELF.fetch(`${BASE}/api/hole?date=${DATE}`);
    const hole = await res.json<Record<string, unknown>>();
    expect(hole.par).toBe(3);
    expect(hole.pickUp).toBe(6);
    expect(hole).not.toHaveProperty('shortest');
    expect(hole).not.toHaveProperty('snap');
  });

  it('rejects a future date', async () => {
    const res = await SELF.fetch(`${BASE}/api/hole?date=2099-01-01`);
    expect(res.status).toBe(404);
  });
});
