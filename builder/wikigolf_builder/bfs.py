"""Breadth-first search over CSR arrays, vectorised with NumPy."""

from __future__ import annotations

import numpy as np

from .config import NO_ROUTE


def gather(off: np.ndarray, tgt: np.ndarray, nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """All (source, neighbour) pairs for `nodes`; removed edges (-1) are skipped."""
    starts = off[nodes]
    lens = off[nodes + 1] - starts
    total = int(lens.sum())
    if total == 0:
        empty = np.zeros(0, dtype=np.int64)
        return empty, empty
    base = np.repeat(starts - (np.cumsum(lens) - lens), lens)
    nbrs = tgt[base + np.arange(total)].astype(np.int64)
    srcs = np.repeat(nodes, lens)
    keep = nbrs >= 0
    return srcs[keep], nbrs[keep]


def distances_to(target: int, rev_off: np.ndarray, rev_tgt: np.ndarray, n: int) -> np.ndarray:
    """Clicks from every article to `target` (uint8; 255 = no route)."""
    dist = np.full(n, NO_ROUTE, dtype=np.uint8)
    dist[target] = 0
    frontier = np.array([target], dtype=np.int64)
    level = 0
    while frontier.size and level < NO_ROUTE - 1:
        _, nbrs = gather(rev_off, rev_tgt, frontier)
        nbrs = np.unique(nbrs[dist[nbrs] == NO_ROUTE])
        level += 1
        dist[nbrs] = level
        frontier = nbrs
    return dist
