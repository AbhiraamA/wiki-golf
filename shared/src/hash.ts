const encoder = new TextEncoder();

/** FNV-1a 32-bit hash over the UTF-8 bytes of a string. Must match builder/wikigolf_builder/fnv.py. */
export function fnv1a32(text: string): number {
  let hash = 0x811c9dc5;
  for (const byte of encoder.encode(text)) {
    hash ^= byte;
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/** Title index shard for a title (underscored form, e.g. `Apollo_11`). */
export function titleShard(title: string, shardCount: number): number {
  return fnv1a32(title) % shardCount;
}
