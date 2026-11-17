"""Build the article link graph as CSR arrays from the dump tables."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .dumps import DumpSource
from .sqlparse import iter_rows, text

MAX_REDIRECT_HOPS = 2


@dataclass
class Graph:
    wiki: str
    dump_date: str
    titles: list[str]  # idx -> title (underscored)
    page_ids: np.ndarray  # idx -> page_id (sorted ascending)
    rev_ids: np.ndarray  # idx -> revision id (page_latest)
    page_len: np.ndarray  # idx -> page length in bytes
    disambig: np.ndarray  # idx -> bool
    title_to_idx: dict[str, int]  # articles and redirects
    fwd_off: np.ndarray
    fwd_tgt: np.ndarray
    rev_off: np.ndarray
    rev_tgt: np.ndarray
    timings: dict[str, float] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.titles)

    @property
    def snap(self) -> str:
        return f"{self.wiki}-{self.dump_date}"

    @property
    def link_count(self) -> int:
        return int(np.count_nonzero(self.fwd_tgt >= 0))

    def in_degree(self) -> np.ndarray:
        return np.diff(self.rev_off).astype(np.int64)

    def out_links(self, idx: int) -> np.ndarray:
        t = self.fwd_tgt[self.fwd_off[idx] : self.fwd_off[idx + 1]]
        return t[t >= 0]

    def remove_edge(self, u: int, v: int) -> None:
        """Drop the link u -> v from both directions (marked as -1)."""
        a, b = self.fwd_off[u], self.fwd_off[u + 1]
        seg = self.fwd_tgt[a:b]
        seg[seg == v] = -1
        a, b = self.rev_off[v], self.rev_off[v + 1]
        seg = self.rev_tgt[a:b]
        seg[seg == u] = -1


def csr(src: np.ndarray, dst: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """CSR for edges sorted by src: offsets (int64, n+1) and targets (int32)."""
    off = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(np.bincount(src, minlength=n), out=off[1:])
    return off, dst.astype(np.int32)


def build_graph(source: DumpSource, log=print) -> Graph:
    timings: dict[str, float] = {}

    # 1. Articles and redirect pages in namespace 0.
    t0 = time.monotonic()
    art_ids, art_titles, art_rev, art_len = [], [], [], []
    redirect_page_title: dict[int, str] = {}
    with source.open("page") as f:
        cols = ["page_id", "page_title", "page_is_redirect", "page_latest", "page_len"]
        for batch in iter_rows(f, "page", cols, where={"page_namespace": b"0"}):
            for pid, title, is_redirect, latest, length in batch:
                if is_redirect == b"1":
                    redirect_page_title[int(pid)] = text(title)
                else:
                    art_ids.append(int(pid))
                    art_titles.append(text(title))
                    art_rev.append(int(latest))
                    art_len.append(int(length))
    order = np.argsort(np.asarray(art_ids, dtype=np.int64), kind="stable")
    page_ids = np.asarray(art_ids, dtype=np.int64)[order]
    titles = [art_titles[i] for i in order]
    rev_ids = np.asarray(art_rev, dtype=np.int64)[order]
    page_len = np.asarray(art_len, dtype=np.int64)[order]
    del art_ids, art_titles, art_rev, art_len
    n = len(titles)
    title_to_idx = {t: i for i, t in enumerate(titles)}
    timings["page"] = time.monotonic() - t0
    log(f"page: {n} articles, {len(redirect_page_title)} redirects")

    # 2. Redirects: fold each redirect title into its target article (at most 2 hops).
    t0 = time.monotonic()
    redirect_to: dict[str, str] = {}
    with source.open("redirect") as f:
        cols = ["rd_from", "rd_title", "rd_interwiki"]
        for batch in iter_rows(f, "redirect", cols, where={"rd_namespace": b"0"}):
            for rd_from, rd_title, interwiki in batch:
                src = redirect_page_title.get(int(rd_from))
                if src is not None and text(interwiki) == "":
                    redirect_to[src] = text(rd_title)
    del redirect_page_title
    articles = dict(title_to_idx)  # resolve against articles only, never other redirects
    for src, dst in redirect_to.items():
        hops = 1
        while dst not in articles and dst in redirect_to and hops < MAX_REDIRECT_HOPS:
            dst = redirect_to[dst]
            hops += 1
        idx = articles.get(dst)
        if idx is not None and src not in articles:
            title_to_idx[src] = idx
    del articles
    timings["redirect"] = time.monotonic() - t0
    log(f"redirect: {len(title_to_idx) - n} redirect titles resolved")

    # 3. Disambiguation pages (page_props).
    t0 = time.monotonic()
    disambig = np.zeros(n, dtype=bool)
    with source.open("page_props") as f:
        where = {"pp_propname": b"'disambiguation'"}
        for batch in iter_rows(f, "page_props", ["pp_page"], where=where):
            ids = np.asarray([int(r[0]) for r in batch], dtype=np.int64)
            pos = np.searchsorted(page_ids, ids)
            ok = (pos < n) & (page_ids[np.minimum(pos, n - 1)] == ids)
            disambig[pos[ok]] = True
    timings["page_props"] = time.monotonic() - t0
    log(f"page_props: {int(disambig.sum())} disambiguation pages")

    # 4. Link targets in namespace 0 -> article index.
    t0 = time.monotonic()
    lt_ids_l, lt_idx_l = [], []
    with source.open("linktarget") as f:
        for batch in iter_rows(
            f, "linktarget", ["lt_id", "lt_title"], where={"lt_namespace": b"0"}
        ):
            for lt_id, lt_title in batch:
                idx = title_to_idx.get(text(lt_title))
                if idx is not None:
                    lt_ids_l.append(int(lt_id))
                    lt_idx_l.append(idx)
    lt_order = np.argsort(np.asarray(lt_ids_l, dtype=np.int64), kind="stable")
    lt_ids = np.asarray(lt_ids_l, dtype=np.int64)[lt_order]
    lt_idx = np.asarray(lt_idx_l, dtype=np.int32)[lt_order]
    del lt_ids_l, lt_idx_l
    timings["linktarget"] = time.monotonic() - t0
    log(f"linktarget: {len(lt_ids)} targets resolve to articles")

    # 5. Page links between articles. Self-links and duplicates are dropped.
    t0 = time.monotonic()
    keys: list[np.ndarray] = []
    raw_rows = 0
    with source.open("pagelinks") as f:
        cols = ["pl_from", "pl_target_id"]
        for batch in iter_rows(f, "pagelinks", cols, where={"pl_from_namespace": b"0"}):
            arr = np.asarray(batch, dtype=np.bytes_).astype(np.int64)
            raw_rows += len(arr)
            keys.append(_edge_keys(arr[:, 0], arr[:, 1], page_ids, lt_ids, lt_idx))
    all_keys = np.unique(np.concatenate(keys)) if keys else np.zeros(0, dtype=np.int64)
    del keys
    src = (all_keys >> 32).astype(np.int64)
    dst = (all_keys & 0xFFFFFFFF).astype(np.int64)
    del all_keys
    fwd_off, fwd_tgt = csr(src, dst, n)
    rorder = np.argsort(dst, kind="stable")
    rev_off, rev_tgt = csr(dst[rorder], src[rorder], n)
    del src, dst, rorder
    timings["pagelinks"] = time.monotonic() - t0
    log(f"pagelinks: {raw_rows} rows -> {len(fwd_tgt)} article links")

    return Graph(
        wiki=source.wiki,
        dump_date=source.dump_date,
        titles=titles,
        page_ids=page_ids,
        rev_ids=rev_ids,
        page_len=page_len,
        disambig=disambig,
        title_to_idx=title_to_idx,
        fwd_off=fwd_off,
        fwd_tgt=fwd_tgt,
        rev_off=rev_off,
        rev_tgt=rev_tgt,
        timings=timings,
    )


def _edge_keys(from_ids, target_ids, page_ids, lt_ids, lt_idx) -> np.ndarray:
    n = len(page_ids)
    fpos = np.searchsorted(page_ids, from_ids)
    fpos_c = np.minimum(fpos, max(n - 1, 0))
    f_ok = (fpos < n) & (page_ids[fpos_c] == from_ids)
    m = len(lt_ids)
    tpos = np.searchsorted(lt_ids, target_ids)
    tpos_c = np.minimum(tpos, max(m - 1, 0))
    t_ok = (tpos < m) & (lt_ids[tpos_c] == target_ids) if m else np.zeros(len(tpos), bool)
    ok = f_ok & t_ok
    u = fpos_c[ok].astype(np.int64)
    v = lt_idx[tpos_c[ok]].astype(np.int64)
    keep = u != v
    return np.unique((u[keep] << 32) | v[keep])
