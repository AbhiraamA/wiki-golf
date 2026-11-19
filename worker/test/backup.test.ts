import { applyD1Migrations, env, SELF } from 'cloudflare:test';
import { beforeAll, describe, expect, it } from 'vitest';
import { seedFixture } from './fixture';
import { RESTORE_MAX_PER_MINUTE } from '../src/lib/backup';

const DATE = new Date().toISOString().slice(0, 10);
const BASE = 'https://wiki.golf';

beforeAll(async () => {
  await applyD1Migrations(env.DB, (env as unknown as { TEST_MIGRATIONS: [] }).TEST_MIGRATIONS);
  await seedFixture(DATE);
});

function cookieFrom(res: Response): string {
  return (res.headers.get('set-cookie') ?? '').split(';')[0] ?? '';
}

async function post(path: string, body: unknown, cookie = ''): Promise<Response> {
  return SELF.fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify(body),
  });
}

describe('backup code and restore', () => {
  it('moves a player to a new browser via a backup code', async () => {
    // Player A starts a (ranked) round, so they own the ranked slot for DATE.
    const startRes = await post('/api/rounds', { date: DATE });
    const cookieA = cookieFrom(startRes);
    expect(cookieA).toMatch(/^wg_pid=/);

    // Create a backup code for A.
    const codeRes = await post('/api/backup-code', {}, cookieA);
    expect(codeRes.status).toBe(200);
    const { code } = await codeRes.json<{ code: string }>();
    expect(code).toMatch(/^[a-z]+-[a-z]+-[a-z]+-\d$/);

    // A brand-new browser (no cookie) restores with the code.
    const restoreRes = await post('/api/restore', { code });
    expect(restoreRes.status).toBe(200);
    const restored = await restoreRes.json<{ restored: boolean }>();
    expect(restored.restored).toBe(true);
    const cookieB = cookieFrom(restoreRes);
    expect(cookieB).toMatch(/^wg_pid=/);

    // Cookie B is now player A: starting a round on DATE is practice, since A already ranked.
    const second = await post('/api/rounds', { date: DATE }, cookieB);
    expect((await second.json<{ ranked: boolean }>()).ranked).toBe(false);
  });

  it('rejects an unknown or malformed code', async () => {
    expect((await post('/api/restore', { code: 'fox-fox-fox-1' })).status).toBe(404);
    expect((await post('/api/restore', { code: 'not a real code' })).status).toBe(404);
    expect((await post('/api/restore', {})).status).toBe(400);
  });

  it('requires a player to create a backup code', async () => {
    expect((await post('/api/backup-code', {})).status).toBe(401);
  });

  it('throttles restore attempts without storing any identifier', async () => {
    await env.DB.prepare('DELETE FROM rate_limits').run();
    // Up to the cap, attempts are processed (unknown code -> 404).
    for (let i = 0; i < RESTORE_MAX_PER_MINUTE; i++) {
      const res = await post('/api/restore', { code: 'pine-pine-pine-0' });
      expect(res.status).toBe(404);
    }
    // The next one trips the limit.
    const limited = await post('/api/restore', { code: 'pine-pine-pine-0' });
    expect(limited.status).toBe(429);

    // Only PII-free counters are stored.
    const cols = await env.DB.prepare('SELECT * FROM rate_limits LIMIT 1').first<
      Record<string, unknown>
    >();
    expect(Object.keys(cols ?? {}).sort()).toEqual(['bucket', 'count', 'reset_at']);
  });
});
