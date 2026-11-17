"""Write the R2 layout (plan.md section 4) into a local folder."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

from .config import PAGE_CHUNK_SIZE
from .fnv import title_shard
from .graph import Graph
from .pick import Hole


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def page_ref(g: Graph, idx: int) -> dict:
    return {"idx": int(idx), "title": g.titles[idx], "revId": int(g.rev_ids[idx])}


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


def hole_record(g: Graph, h: Hole, status: str = "queued") -> dict:
    return {
        "holeNo": h.hole_no,
        "date": h.date,
        "snap": g.snap,
        "wiki": g.wiki,
        "par": h.par,
        "pickUp": h.pick_up,
        "shortest": h.shortest,
        "start": page_ref(g, h.start),
        "target": page_ref(g, h.target),
        "difficulty": h.difficulty,
        "status": status,
    }


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


def write_holes(g: Graph, holes: list[Hole], out: Path) -> list[tuple[dict, Path, Path]]:
    written = []
    for h in holes:
        record = hole_record(g, h)
        hp = out / "holes" / f"{h.date}.json"
        _write_json(hp, record)
        dp = out / "distances" / f"{h.date}.bin"
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_bytes(np.ascontiguousarray(h.dist, dtype=np.uint8).tobytes())
        written.append((record, hp, dp))
    return written


def merge_index(existing: list[dict], new_entries: list[dict]) -> dict:
    by_date = {e["date"]: e for e in existing}
    for e in new_entries:
        by_date.setdefault(e["date"], e)
    return {"holes": [by_date[d] for d in sorted(by_date)]}


def write_index(index: dict, out: Path) -> Path:
    p = out / "holes" / "index.json"
    _write_json(p, index)
    return p
