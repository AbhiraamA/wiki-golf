import { APP_VERSION } from '@wiki-golf/shared';
import { Hono } from 'hono';
import type { Env } from './env';

const app = new Hono<{ Bindings: Env }>();

app.get('/api/health', (c) =>
  c.json({ ok: true, version: APP_VERSION, wiki: c.env.WIKI, environment: c.env.ENVIRONMENT }),
);

app.all('/api/*', (c) => c.json({ error: 'not_found' }, 404));

// Anything else falls through to the static front end (SPA fallback is handled by assets config).
app.all('*', (c) => c.env.ASSETS.fetch(c.req.raw));

app.onError((err, c) => {
  console.error(err);
  return c.json({ error: 'internal_error' }, 500);
});

export default app satisfies ExportedHandler<Env>;
