import { exports } from 'cloudflare:workers';
import { describe, expect, it } from 'vitest';

describe('worker', () => {
  it('answers the health check', async () => {
    const res = await exports.default.fetch('https://example.com/api/health');
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ ok: true, wiki: 'simplewiki' });
  });

  it('returns JSON 404 for unknown API routes', async () => {
    const res = await exports.default.fetch('https://example.com/api/nope');
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: 'not_found' });
  });
});
