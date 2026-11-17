/** Per-target distance arrays from R2 (`{wiki}/distances/{date}.bin`), cached in memory. */

import type { Env } from '../env';

const cache = new Map<string, Uint8Array>();

export async function loadDistances(env: Env, date: string): Promise<Uint8Array | null> {
  const key = `${env.WIKI}/${date}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const obj = await env.BUCKET.get(`${env.WIKI}/distances/${date}.bin`);
  if (!obj) return null;
  const arr = new Uint8Array(await obj.arrayBuffer());
  // Keep only a few arrays resident (each is ~articleCount bytes).
  if (cache.size > 6) cache.clear();
  cache.set(key, arr);
  return arr;
}
