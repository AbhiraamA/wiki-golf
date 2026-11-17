"""Command line: `python -m wikigolf_builder build ...` and `... approve ...`."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import os
import resource
import sys
import time
from pathlib import Path

from . import dumps, export, net
from .bfs import distances_to
from .config import BLOCKLIST_PATH, wiki_settings
from .exclude import excluded_mask, load_blocklist
from .graph import build_graph
from .pick import History, Picker
from .verify import html_fetcher


def log(msg: str) -> None:
    print(msg, flush=True)


def peak_memory_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def date_range(start: str, days: int) -> list[str]:
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(days)]


def resolve_start(start: str, index: dict) -> str:
    if start != "auto":
        dt.date.fromisoformat(start)
        return start
    tomorrow = dt.datetime.now(dt.UTC).date() + dt.timedelta(days=1)
    dates = [dt.date.fromisoformat(e["date"]) for e in index.get("holes", [])]
    nxt = max(dates) + dt.timedelta(days=1) if dates else tomorrow
    return max(nxt, tomorrow).isoformat()


def parse_overrides(pairs: list[str], base):
    fields = {f.name: f.type for f in dataclasses.fields(base)}
    changes = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        key = key.replace("-", "_")
        if key not in fields:
            raise SystemExit(f"Unknown --pick setting {key!r}; known: {', '.join(fields)}")
        changes[key] = int(value)
    return dataclasses.replace(base, **changes)


def build(args: argparse.Namespace) -> int:
    t_start = time.monotonic()
    settings = wiki_settings(args.wiki)
    pick_settings = parse_overrides(args.pick or [], settings.pick)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    r2 = None
    if args.upload:
        from .upload import R2

        r2 = R2()
        index = r2.get_json("holes/index.json") or {"holes": []}
    elif args.index and Path(args.index).exists():
        import json

        index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    else:
        index = {"holes": []}

    start = resolve_start(args.start, index)
    have = {e["date"] for e in index.get("holes", [])}
    dates = [d for d in date_range(start, args.days) if d not in have]
    skipped = args.days - len(dates)
    if skipped:
        log(f"Skipping {skipped} date(s) that already have holes")
    if not dates:
        log("Nothing to build.")
        return 0

    session = net.make_session()
    if args.dumps_dir:
        source = dumps.LocalDumps(Path(args.dumps_dir), args.wiki, args.dump_date or "00000000")
    else:
        source = dumps.find_remote(session, args.wiki, args.dump_date)
    log(f"Building {args.wiki} snapshot {source.dump_date} for {dates[0]}..{dates[-1]}")

    t0 = time.monotonic()
    g = build_graph(source, log=log)
    graph_secs = time.monotonic() - t0

    excluded = excluded_mask(
        g.titles, g.disambig, g.page_len, pick_settings.min_page_len, load_blocklist(BLOCKLIST_PATH)
    )
    fetch = None if args.no_verify else html_fetcher(session, settings.lang)
    picker = Picker(g, excluded, pick_settings, History.from_index(index["holes"]), fetch, log=log)

    t0 = time.monotonic()
    holes, missing = [], []
    for date in dates:
        hole = picker.pick(date)
        if hole is None:
            log(f"{date}: no hole found")
            missing.append(date)
            continue
        log(
            f"{date}: #{hole.hole_no} par {hole.par} {g.titles[hole.start]} -> "
            f"{g.titles[hole.target]} (difficulty {hole.difficulty}, {hole.routes:.0f} routes)"
        )
        holes.append(hole)
    # Edges dropped during verification change distances: recompute every hole's file at the end.
    for hole in holes:
        hole.dist = distances_to(hole.target, g.rev_off, g.rev_tgt, g.n)
        assert int(hole.dist[hole.start]) == hole.shortest, f"{hole.date}: route changed"
    pick_secs = time.monotonic() - t0

    snapshot_files = export.write_snapshot(g, out, settings.shard_count)
    written = export.write_holes(g, holes, out)
    new_entries = [export.index_entry(rec) for rec, _, _ in written]

    uploaded = "no (--upload not set)"
    if r2 is not None:
        uploaded = upload_all(r2, out, g.snap, snapshot_files, written, new_entries)
    else:
        export.write_index(export.merge_index(index.get("holes", []), new_entries), out)

    summary = render_summary(
        g=g,
        holes=holes,
        missing=missing,
        removed=picker.removed_edges,
        timings={
            **g.timings,
            "graph total": graph_secs,
            "pick + verify": pick_secs,
            "run total": time.monotonic() - t_start,
        },
        uploaded=uploaded,
    )
    log(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    return 1 if missing else 0


def upload_all(r2, out: Path, snap: str, snapshot_files, written, new_entries) -> str:
    from .upload import key_for

    meta_key = f"snapshots/{snap}/meta.json"
    if r2.exists(meta_key):
        log(f"Snapshot {snap} already in R2; not re-uploading it")
    else:
        # meta.json goes last so its presence means the snapshot is complete.
        for p in sorted(snapshot_files, key=lambda p: p.name == "meta.json"):
            r2.put_file(key_for(p, out), p)
        log(f"Uploaded snapshot {snap} ({len(snapshot_files)} files)")
    done = []
    for record, hp, dp in written:
        key = key_for(hp, out)
        if r2.exists(key):
            log(f"{record['date']}: already in R2; left unchanged")
            continue
        r2.put_file(key_for(dp, out), dp)
        r2.put_file(key, hp)
        done.append(export.index_entry(record))
    current = r2.get_json("holes/index.json") or {"holes": []}
    index = export.merge_index(current.get("holes", []), done)
    r2.put_json("holes/index.json", index)
    export.write_index(index, out)
    return f"yes: {len(done)} holes, {r2.puts} objects written"


def render_summary(g, holes, missing, removed, timings, uploaded) -> str:
    lines = [
        f"## Wiki Golf holes: {g.snap}",
        "",
        f"- Articles: {g.n:,}  Links: {g.link_count:,}  Redirect titles: {len(g.title_to_idx) - g.n:,}",
        f"- Peak memory: {peak_memory_mb():,.0f} MB",
        f"- Uploaded to R2: {uploaded}",
        f"- Links dropped after HTML check: {len(removed)}",
        "",
        "| Date | Hole | Par | Start | Target | Verified shortest route | Difficulty | Routes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for h in holes:
        route = " → ".join(g.titles[i].replace("_", " ") for i in h.route)
        lines.append(
            f"| {h.date} | {h.hole_no} | {h.par} | {g.titles[h.start].replace('_', ' ')} | "
            f"{g.titles[h.target].replace('_', ' ')} | {route} | {h.difficulty} | {h.routes:,.0f} |"
        )
    if missing:
        lines += ["", f"**No hole found for:** {', '.join(missing)}"]
    lines += ["", "| Stage | Seconds |", "| --- | --- |"]
    lines += [f"| {k} | {v:,.1f} |" for k, v in timings.items()]
    return "\n".join(lines)


def approve(args: argparse.Namespace) -> int:
    from .upload import R2

    r2 = R2()
    index = r2.get_json("holes/index.json") or {"holes": []}
    if args.through:
        dates = [
            e["date"]
            for e in index["holes"]
            if e["date"] <= args.through and e["status"] == "queued"
        ]
    else:
        dates = args.dates
    by_date = {e["date"]: e for e in index["holes"]}
    for date in dates:
        if date not in by_date:
            log(f"{date}: no such hole")
            continue
        record = r2.get_json(f"holes/{date}.json")
        log(
            f"{date}: {record['start']['title']} -> {record['target']['title']} ({record['status']})"
        )
        if args.dry_run:
            continue
        record["status"] = "approved"
        r2.put_json(f"holes/{date}.json", record)
        by_date[date]["status"] = "approved"
    if not args.dry_run:
        r2.put_json("holes/index.json", index)
        log(f"Approved {len(dates)} hole(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wikigolf_builder")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build holes from a Wikipedia dump")
    b.add_argument("--wiki", default="simplewiki")
    b.add_argument("--days", type=int, default=30)
    b.add_argument("--start", default="auto", help="YYYY-MM-DD, or 'auto' (day after last hole)")
    b.add_argument("--upload", action="store_true", help="Upload results to R2")
    b.add_argument("--out", default="out")
    b.add_argument("--dump-date", help="Dump folder date YYYYMMDD (default: newest complete)")
    b.add_argument("--dumps-dir", help="Read {table}.sql[.gz] from this folder (tests)")
    b.add_argument("--index", help="Local holes/index.json to treat as history (no upload)")
    b.add_argument("--no-verify", action="store_true", help="Skip the HTML route check (tests)")
    b.add_argument("--pick", action="append", metavar="KEY=N", help="Override a pick setting")
    b.set_defaults(func=build)

    a = sub.add_parser("approve", help="Mark queued holes as approved in R2")
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--dates", nargs="+")
    g.add_argument("--through", help="Approve every queued hole up to this date")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=approve)

    args = p.parse_args(argv)
    return args.func(args)
