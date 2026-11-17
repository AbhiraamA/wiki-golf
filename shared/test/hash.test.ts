import { describe, expect, it } from 'vitest';
import vectors from '../test-vectors/fnv1a.json';
import { fnv1a32, titleShard } from '../src/hash';

describe('fnv1a32', () => {
  it('matches the shared test vectors', () => {
    for (const v of vectors.vectors) {
      expect(fnv1a32(v.input), v.input).toBe(v.fnv1a32);
      expect(titleShard(v.input, 64), v.input).toBe(v.shard64);
      expect(titleShard(v.input, 1024), v.input).toBe(v.shard1024);
    }
  });
});
