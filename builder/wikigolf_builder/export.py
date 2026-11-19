"""Write the R2 layout (plan.md section 4) into a local folder."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .config import PAGE_CHUNK_SIZE
from .fnv import title_shard
from .graph import Graph
from .pick import Hole

# idx -> short description (""); passed in so the snapshot/pageview lookups live in the CLI.
Describe = Callable[[int], str]


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def page_ref(g: Graph, idx: int, describe: Describe | None = None) -> dict:
    ref = {"idx": int(idx), "title": g.titles[idx], "revId": int(g.rev_ids[idx])}
    desc = describe(idx) if describe else ""
    if desc:
        ref["shortDesc"] = desc
    return ref


def write_snapshot(g: Graph, out: Path, shard_count: int) -> list[Path]:
    """meta.json, title index shards and page chunks for the snapshot."""
    base = out / "snapshots" / g.snap
    shards: list[dict[str, list[int]]] = [{} for _ in range(shard_count)]
    for title, idx in g.title_to_idx.items():
        shards[title_shard(title, shard_count)][title] = [idx, int(g.rev_ids[idx])]
    files = []
    for i, shard in enumerate(shards):
        p = base / "titles" / f"{i}.json"
        _write_json(p, shard)
        files.append(p)
    for start in range(0, g.n, PAGE_CHUNK_SIZE):
        chunk = [
            [g.titles[i], int(g.rev_ids[i])]
            for i in range(start, min(start + PAGE_CHUNK_SIZE, g.n))
        ]
        p = base / "pages" / f"{start // PAGE_CHUNK_SIZE}.json"
        _write_json(p, chunk)
        files.append(p)
    meta = {
        "snap": g.snap,
        "wiki": g.wiki,
        "dumpDate": g.dump_date,
        "articleCount": g.n,
        "linkCount": g.link_count,
        "shardCount": shard_count,
        "pageChunkSize": PAGE_CHUNK_SIZE,
        "builtAt": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    _write_json(base / "meta.json", meta)
    files.append(base / "meta.json")
    return files


def hole_record(
    g: Graph, h: Hole, status: str = "queued", describe: Describe | None = None
) -> dict:
    record = {
        "holeNo": h.hole_no,
        "date": h.date,
        "snap": g.snap,
        "wiki": g.wiki,
        "par": h.par,
        "pickUp": h.pick_up,
        "shortest": h.shortest,
        "start": page_ref(g, h.start, describe),
        "target": page_ref(g, h.target, describe),
        "difficulty": h.difficulty,
        "status": status,
    }
    if h.badge:  # themed days carry a badge the tee screen can show
        record["badge"] = h.badge
    return record


def index_entry(record: dict) -> dict:
    """Entry in holes/index.json. Titles are kept for the builder's no-repeat rules."""
    return {
        "date": record["date"],
        "holeNo": record["holeNo"],
        "status": record["status"],
        "snap": record["snap"],
        "par": record["par"],
        "start": record["start"]["title"],
        "target": record["target"]["title"],
    }


def write_holes(
    g: Graph, holes: list[Hole], out: Path, describe: Describe | None = None
) -> list[tuple[dict, Path, Path]]:
    # Holes and distances live under the wiki's own prefix (e.g. simplewiki/holes/…) so that
    # one wiki's dates never collide with another's. Snapshots keep their own prefix because
    # `snap` already names the wiki (e.g. simplewiki-20261101).
    written = []
    for h in holes:
        record = hole_record(g, h, describe=describe)
        hp = out / g.wiki / "holes" / f"{h.date}.json"
        _write_json(hp, record)
        dp = out / g.wiki / "distances" / f"{h.date}.bin"
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_bytes(np.ascontiguousarray(h.dist, dtype=np.uint8).tobytes())
        written.append((record, hp, dp))
    return written


def merge_index(existing: list[dict], new_entries: list[dict]) -> dict:
    by_date = {e["date"]: e for e in existing}
    for e in new_entries:
        by_date.setdefault(e["date"], e)
    return {"holes": [by_date[d] for d in sorted(by_date)]}


def write_index(index: dict, out: Path, wiki: str) -> Path:
    p = out / wiki / "holes" / "index.json"
    _write_json(p, index)
    return p
