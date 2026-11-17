/** Read a snapshot's metadata, title index and page list from R2 (plan.md §4). */

import { PAGE_CHUNK_SIZE, titleShard, type PageRef } from '@wiki-golf/shared';
import type { Env } from '../env';

export interface SnapshotMeta {
  snap: string;
  wiki: string;
  articleCount: number;
  shardCount: number;
  pageChunkSize: number;
}

// Per-instance caches: snapshots are immutable, so anything read stays valid for the Worker's life.
const metaCache = new Map<string, SnapshotMeta>();
const shardCache = new Map<string, Record<string, [number, number]>>();
const chunkCache = new Map<string, [string, number][]>();

async function json<T>(env: Env, keyName: string): Promise<T | null> {
  const obj = await env.BUCKET.get(keyName);
  return obj ? ((await obj.json()) as T) : null;
}

export async function loadMeta(env: Env, snap: string): Promise<SnapshotMeta | null> {
  const cached = metaCache.get(snap);
  if (cached) return cached;
  const meta = await json<SnapshotMeta>(env, `snapshots/${snap}/meta.json`);
  if (meta) metaCache.set(snap, meta);
  return meta;
}

/** Normalise a title to the underscore form used as the index key. */
export function normTitle(title: string): string {
  return title.trim().replace(/ /g, '_');
}

/** Resolve a title (redirects already folded in the index) to {idx, revId}, or null. */
export async function resolveTitle(
  env: Env,
  meta: SnapshotMeta,
  title: string,
): Promise<{ idx: number; revId: number } | null> {
  const key = normTitle(title);
  const shard = titleShard(key, meta.shardCount);
  const cacheKey = `${meta.snap}/${shard}`;
  let data = shardCache.get(cacheKey);
  if (!data) {
    data =
      (await json<Record<string, [number, number]>>(
        env,
        `snapshots/${meta.snap}/titles/${shard}.json`,
      )) ?? {};
    shardCache.set(cacheKey, data);
  }
  const entry = data[key];
  return entry ? { idx: entry[0], revId: entry[1] } : null;
}

/** Title and revision for a page index. */
export async function pageByIdx(
  env: Env,
  meta: SnapshotMeta,
  idx: number,
): Promise<PageRef | null> {
  if (idx < 0 || idx >= meta.articleCount) return null;
  const size = meta.pageChunkSize || PAGE_CHUNK_SIZE;
  const chunk = Math.floor(idx / size);
  const cacheKey = `${meta.snap}/${chunk}`;
  let data = chunkCache.get(cacheKey);
  if (!data) {
    data =
      (await json<[string, number][]>(env, `snapshots/${meta.snap}/pages/${chunk}.json`)) ?? [];
    chunkCache.set(cacheKey, data);
  }
  const row = data[idx - chunk * size];
  return row ? { idx, title: row[0], revId: row[1] } : null;
}
