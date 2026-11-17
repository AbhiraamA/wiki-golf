/** Seed a tiny snapshot + hole into the test R2 bucket, mirroring the builder's output.

Graph (distances to the target, idx 2 = Target):
  0 Start (d2) -> Mid, Far      1 Mid (d1) -> Target
  2 Target (d0)                 3 Far (d3) -> Start   (a bunker from Start)
*/
import { titleShard } from '@wiki-golf/shared';
import { env } from 'cloudflare:test';

export const SNAP = 'simplewiki-test';
export const SHARDS = 4;
export const PAGES: [title: string, revId: number, links: string[]][] = [
  ['Start', 1000, ['Mid', 'Far']],
  ['Mid', 1001, ['Target']],
  ['Target', 1002, []],
  ['Far', 1003, ['Start']],
];
export const DISTANCES = Uint8Array.from([2, 1, 0, 3]);

function parsoid(links: string[]): string {
  const body = links.map((t) => `<a rel="mw:WikiLink" href="./${t}">${t}</a>`).join(' and ');
  return `<section>${body}</section>`;
}

export async function seedFixture(date: string): Promise<void> {
  const bucket = env.BUCKET;
  await bucket.put(
    `snapshots/${SNAP}/meta.json`,
    JSON.stringify({
      snap: SNAP,
      wiki: 'simplewiki',
      articleCount: PAGES.length,
      shardCount: SHARDS,
      pageChunkSize: 1000,
    }),
  );
  // Title shards (redirects already folded; none here).
  const shards: Record<string, [number, number]>[] = Array.from({ length: SHARDS }, () => ({}));
  PAGES.forEach(([title, revId], idx) => {
    const shard = shards[titleShard(title, SHARDS)];
    if (shard) shard[title] = [idx, revId];
  });
  for (let i = 0; i < SHARDS; i++) {
    await bucket.put(`snapshots/${SNAP}/titles/${i}.json`, JSON.stringify(shards[i]));
  }
  // Pages chunk 0.
  await bucket.put(
    `snapshots/${SNAP}/pages/0.json`,
    JSON.stringify(PAGES.map(([title, revId]) => [title, revId])),
  );
  // HTML for each pinned revision.
  for (const [, revId, links] of PAGES) {
    await bucket.put(`html/simplewiki/${revId}.html`, parsoid(links));
  }
  // Hole + distances.
  await bucket.put(
    `simplewiki/holes/${date}.json`,
    JSON.stringify({
      holeNo: 1,
      date,
      snap: SNAP,
      wiki: 'simplewiki',
      par: 3,
      pickUp: 6,
      shortest: 2,
      start: { idx: 0, title: 'Start', revId: 1000 },
      target: { idx: 2, title: 'Target', revId: 1002 },
      difficulty: 0.33,
      status: 'queued',
    }),
  );
  await bucket.put(`simplewiki/distances/${date}.bin`, DISTANCES);
}
