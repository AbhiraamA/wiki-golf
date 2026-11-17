import type { Wiki } from '@wiki-golf/shared';

export interface Env {
  ASSETS: Fetcher;
  DB: D1Database;
  BUCKET: R2Bucket;
  WIKI: Wiki;
  ENVIRONMENT: 'dev' | 'production';
}
