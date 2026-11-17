import type { Wiki } from '@wiki-golf/shared';

export interface Env {
  ASSETS: Fetcher;
  DB: D1Database;
  BUCKET: R2Bucket;
  WIKI: Wiki;
  ENVIRONMENT: 'dev' | 'production';
  /** HMAC key for the identity cookie. Dev value in wrangler.jsonc; prod via `wrangler secret put`. */
  COOKIE_SECRET: string;
}
