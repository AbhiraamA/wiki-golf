"""FNV-1a 32-bit hash. Must match shared/src/hash.ts (checked by shared/test-vectors/fnv1a.json)."""

FNV_OFFSET = 0x811C9DC5
FNV_PRIME = 0x01000193


def fnv1a32(text: str) -> int:
    h = FNV_OFFSET
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * FNV_PRIME) & 0xFFFFFFFF
    return h


def title_shard(title: str, shard_count: int) -> int:
    return fnv1a32(title) % shard_count
