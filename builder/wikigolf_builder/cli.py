"""Command line: `build` (CI), plus `show` and `approve` (local, for the owner to review R2)."""

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
from .enrich import make_describe, make_policy, make_view_lookup
from .exclude import excluded_mask, load_blocklist
from .graph import build_graph
from .pick import History, Picker
from .themes import load_themes, theme_for
from .verify import html_fetcher

THEMES_KEY = "themes.json"  # private calendar in R2 (never in the repo)


def load_themes_doc(args, r2) -> dict | None:
    """The themes.json document: from a local --themes file, else from R2 (upload builds)."""
    import json

    if args.themes:
        return json.loads(Path(args.themes).read_text(encoding="utf-8"))
    if r2 is not None:
        return r2.get_json(THEMES_KEY)
    return None


def log(msg: str) -> None:
    print(msg, flush=True)


def index_key(wiki: str) -> str:
    return f"{wiki}/holes/index.json"


def hole_key(wiki: str, date: str) -> str:
    return f"{wiki}/holes/{date}.json"


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
    # f.type is a string annotation here (config.py uses `from __future__ import annotations`).
    fields = {f.name: f.type for f in dataclasses.fields(base)}
    changes = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        key = key.replace("-", "_")
        if key not in fields:
            raise SystemExit(f"Unknown --pick setting {key!r}; known: {', '.join(fields)}")
        changes[key] = float(value) if fields[key] == "float" else int(value)
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
        index = r2.get_json(index_key(args.wiki)) or {"holes": []}
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

    today = dt.datetime.now(dt.UTC).date()
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
    # Local-dump builds (the tests) stay offline; real builds consult the pageview and Wikidata
    # APIs. The pageview floor ranks targets by English-Wikipedia readership for the same title.
    online = not args.dumps_dir
    view_lookup = None
    if online and not args.no_pageviews:
        view_lookup = make_view_lookup(session, today, log=log)
    # Content policy for targets (CONTENT_GUIDE.md): drops murderers/criminals, drugs, conspiracy
    # theories, terrorism, hate groups, sexual topics, modern politicians, disputed territories and
    # recent deaths. Uses the local short description offline; also consults Wikidata when online.
    # The blocklist and title patterns are the offline backstop (and cover starts).
    sensitive = None
    if not args.no_sensitive:
        sensitive = make_policy(g, session if online else None, settings.lang, today).target_reason
    picker = Picker(
        g,
        excluded,
        pick_settings,
        History.from_index(index["holes"]),
        fetch,
        view_lookup,
        sensitive,
        log=log,
    )
    log(picker.fame_summary())

    themes = load_themes(load_themes_doc(args, r2))
    if themes:
        log(f"Loaded {len(themes)} themed-day rule(s)")

    t0 = time.monotonic()
    holes, missing = [], []
    for date in dates:
        theme = theme_for(date, themes)
        hole = picker.pick_themed(date, theme) if theme else None
        if hole is None:
            hole = picker.pick(date)
        if hole is None:
            log(f"{date}: no hole found")
            missing.append(date)
            continue
        # No titles or routes in build logs: the repo is public, so the Actions log is public.
        tag = " themed" if hole.badge else ""
        log(f"{date}: #{hole.hole_no} par {hole.par}{tag} found (route verified)")
        holes.append(hole)
    # Edges dropped during verification change distances: recompute every hole's file at the end.
    for hole in holes:
        hole.dist = distances_to(hole.target, g.rev_off, g.rev_tgt, g.n)
        assert int(hole.dist[hole.start]) == hole.shortest, f"{hole.date}: route changed"
    pick_secs = time.monotonic() - t0

    if view_lookup is not None and view_lookup.failures[0]:
        log(f"pageview API: {view_lookup.failures[0]} lookup(s) failed; those judged on langlinks")
    describe = make_describe(g, session if online else None, settings.lang, log=log)
    snapshot_files = export.write_snapshot(g, out, settings.shard_count)
    written = export.write_holes(g, holes, out, describe)
    new_entries = [export.index_entry(rec) for rec, _, _ in written]

    uploaded = "no (--upload not set)"
    if r2 is not None:
        uploaded = upload_all(r2, out, g.wiki, g.snap, snapshot_files, written)
    else:
        merged = export.merge_index(index.get("holes", []), new_entries)
        export.write_index(merged, out, g.wiki)

    summary = render_summary(
        g=g,
        holes=holes,
        missing=missing,
        removed=picker.removed_edges,
        sensitive_dropped=picker.sensitive_dropped,
        verified=not args.no_verify,
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


def upload_all(r2, out: Path, wiki: str, snap: str, snapshot_files, written) -> str:
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
    current = r2.get_json(index_key(wiki)) or {"holes": []}
    index = export.merge_index(current.get("holes", []), done)
    r2.put_json(index_key(wiki), index)
    export.write_index(index, out, wiki)
    return f"yes: {len(done)} holes, {r2.puts} objects written"


def render_summary(
    g, holes, missing, removed, verified, timings, uploaded, sensitive_dropped=0
) -> str:
    # No titles or routes here: this goes to the public Actions job summary. Owners review the
    # start and target privately with `python -m wikigolf_builder show`.
    check = "passed" if verified else "skipped (--no-verify)"
    lines = [
        f"## Wiki Golf holes: {g.snap}",
        "",
        f"- Articles: {g.n:,}  Links: {g.link_count:,}  Redirect titles: {len(g.title_to_idx) - g.n:,}",
        f"- Holes built: {len(holes)}  No hole found: {len(missing)}",
        f"- Peak memory: {peak_memory_mb():,.0f} MB",
        f"- Uploaded to R2: {uploaded}",
        f"- Links dropped after HTML check: {len(removed)}",
        f"- Sensitive targets skipped: {sensitive_dropped}",
        "",
        "Start, target and route are withheld from this public log. Review them with "
        "`python -m wikigolf_builder show --status queued` before approving.",
        "",
        "| Date | Hole | Par | Route check |",
        "| --- | --- | --- | --- |",
    ]
    for h in holes:
        lines.append(f"| {h.date} | {h.hole_no} | {h.par} | {check} |")
    if missing:
        lines += ["", f"**No hole found for:** {', '.join(missing)}"]
    lines += ["", "| Stage | Seconds |", "| --- | --- |"]
    lines += [f"| {k} | {v:,.1f} |" for k, v in timings.items()]
    return "\n".join(lines)


def _oldid_url(wiki: str, rev_id: int) -> str:
    lang = wiki_settings(wiki).lang
    return f"https://{lang}.wikipedia.org/w/index.php?oldid={rev_id}"


def open_r2(via: str):
    """R2 client for review commands. 'wrangler' uses the owner's login; 'keys' uses S3 keys."""
    if via == "keys":
        from .upload import R2

        return R2()
    from .wrangler_r2 import WranglerR2

    return WranglerR2()


def _select_dates(index: dict, dates, through, status) -> list[str]:
    if dates:
        return list(dates)
    entries = index.get("holes", [])
    return [
        e["date"]
        for e in entries
        if (through is None or e["date"] <= through) and (status is None or e["status"] == status)
    ]


def show(args: argparse.Namespace) -> int:
    """Print full hole details from R2 for local review. Not used in CI (would leak answers)."""
    r2 = open_r2(args.via)
    index = r2.get_json(index_key(args.wiki)) or {"holes": []}
    dates = _select_dates(index, args.dates, args.through, args.status)
    if not dates:
        log(f"No matching holes in R2 for {args.wiki}.")
        return 0
    for date in sorted(dates):
        rec = r2.get_json(hole_key(args.wiki, date))
        if rec is None:
            log(f"{date}: not found in R2")
            continue
        start, target = rec["start"], rec["target"]
        log(
            f"\n── {date}  hole #{rec['holeNo']}  par {rec['par']} "
            f"(pick up {rec['pickUp']})  [{rec['status']}]"
        )
        log(
            f"   {rec['wiki']} {rec['snap']}  shortest {rec['shortest']} clicks  "
            f"difficulty {rec['difficulty']}"
        )
        if rec.get("badge"):
            log(f"   badge:  {rec['badge']['emoji']} {rec['badge']['label']}")
        log(f"   start:  {start['title'].replace('_', ' ')}")
        if start.get("shortDesc"):
            log(f"           “{start['shortDesc']}”")
        log(f"           {_oldid_url(rec['wiki'], start['revId'])}")
        log(f"   target: {target['title'].replace('_', ' ')}")
        if target.get("shortDesc"):
            log(f"           “{target['shortDesc']}”")
        log(f"           {_oldid_url(rec['wiki'], target['revId'])}")
    log("\n(The route is not stored in R2. Review judges the start and target articles.)")
    return 0


def check(args: argparse.Namespace) -> int:
    """Re-check holes in R2 against the content policy (CONTENT_GUIDE.md), for local review.

    Resolves each start/target to its Wikidata item by title and applies the start/target policy;
    prints PASS/FAIL per hole and a list of dates to re-roll. Read-only (no R2 writes). This is the
    guide's final review step; run it on every batch before `approve`.
    """
    from . import enrich
    from .sensitive import start_policy_reason, target_policy_reason

    today = dt.datetime.now(dt.UTC).date()
    want = list(dict.fromkeys(["en", wiki_settings(args.wiki).lang]))
    session = net.make_session()
    r2 = open_r2(args.via)
    index = r2.get_json(index_key(args.wiki)) or {"holes": []}
    dates = _select_dates(index, args.dates, args.through, args.status)
    if not dates:
        log(f"No matching holes in R2 for {args.wiki}.")
        return 0

    failing: list[str] = []
    for date in sorted(dates):
        rec = r2.get_json(hole_key(args.wiki, date))
        if rec is None:
            log(f"{date}: not found in R2")
            continue
        problems = []
        for role, ep in (("start", rec["start"]), ("target", rec["target"])):
            fields = enrich.fields_by_title(session, args.wiki, ep["title"], want)
            if fields is None:
                problems.append(
                    f"{role} {ep['title'].replace('_', ' ')}: could not check (network)"
                )
                continue
            desc = fields["desc"] or ep.get("shortDesc", "")
            if role == "target":
                reason = target_policy_reason(
                    desc=desc,
                    instance_classes=fields["classes"],
                    occupations=fields["occupations"],
                    positions_held=fields["positions"],
                    convicted_of=fields["convicted"],
                    death_iso=fields["death"],
                    today=today,
                )
            else:
                reason = start_policy_reason(
                    desc=desc,
                    instance_classes=fields["classes"],
                    occupations=fields["occupations"],
                    convicted_of=fields["convicted"],
                    death_iso=fields["death"],
                    today=today,
                )
            if reason:
                problems.append(f"{role} {ep['title'].replace('_', ' ')}: {reason}")
        if problems:
            failing.append(date)
            log(f"✗ {date} [{rec['status']}]")
            for p in problems:
                log(f"    {p}")
        else:
            log(f"✓ {date} [{rec['status']}]")
    log("")
    if failing:
        log(f"{len(failing)} hole(s) fail the content policy: {' '.join(failing)}")
    else:
        log(f"All {len(dates)} checked hole(s) pass the content policy.")
    return 1 if failing else 0


def approve(args: argparse.Namespace) -> int:
    r2 = open_r2(args.via)
    index = r2.get_json(index_key(args.wiki)) or {"holes": []}
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
        record = r2.get_json(hole_key(args.wiki, date))
        log(
            f"{date}: {record['start']['title']} -> {record['target']['title']} ({record['status']})"
        )
        if args.dry_run:
            continue
        record["status"] = "approved"
        r2.put_json(hole_key(args.wiki, date), record)
        by_date[date]["status"] = "approved"
    if not args.dry_run:
        r2.put_json(index_key(args.wiki), index)
        log(f"Approved {len(dates)} hole(s)")
    return 0


def relayout(args: argparse.Namespace) -> int:
    """One-off: move the old top-level holes/ and distances/ into a wiki prefix.

    Copies each object to {wiki}/<key>, then (with --delete-old) removes the original only after
    the copy is confirmed present. Dry-run by default.
    """
    from .upload import R2

    r2 = R2()
    wiki = args.wiki
    old_keys = [
        k
        for k in r2.list_keys("holes/") + r2.list_keys("distances/")
        if not k.startswith(f"{wiki}/")
    ]
    if not old_keys:
        log("Nothing to move: no old top-level holes/ or distances/ objects.")
        return 0
    log(f"{'Moving' if args.apply else 'Would move'} {len(old_keys)} object(s) under {wiki}/:")
    for key in sorted(old_keys):
        dst = f"{wiki}/{key}"
        log(f"  {key} -> {dst}")
        if not args.apply:
            continue
        r2.copy(key, dst)
        if not r2.exists(dst):
            raise SystemExit(f"Copy of {key} to {dst} not confirmed; stopping before any delete")
        if args.delete_old:
            r2.delete(key)
    if args.apply:
        log(
            f"Done. Copied {len(old_keys)} object(s)"
            + (" and deleted originals." if args.delete_old else ".")
        )
    else:
        log("Dry run: pass --apply to copy, and --delete-old to remove the originals afterwards.")
    return 0


def clear(args: argparse.Namespace) -> int:
    """Delete a wiki's holes, distances and index from R2 (so a rebuild can replace them)."""
    from .upload import R2

    r2 = R2()
    keys = r2.list_keys(f"{args.wiki}/holes/") + r2.list_keys(f"{args.wiki}/distances/")
    if not keys:
        log(f"Nothing to clear under {args.wiki}/.")
        return 0
    log(f"{'Deleting' if args.apply else 'Would delete'} {len(keys)} object(s) under {args.wiki}/")
    if not args.apply:
        log("Dry run: pass --apply to delete.")
        return 0
    for key in keys:
        r2.delete(key)
    log(f"Deleted {len(keys)} object(s).")
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
    b.add_argument(
        "--no-pageviews", action="store_true", help="Skip the enwiki pageview floor for targets"
    )
    b.add_argument(
        "--no-sensitive", action="store_true", help="Skip the sensitive-topic filter for targets"
    )
    b.add_argument("--pick", action="append", metavar="KEY=N", help="Override a pick setting")
    b.add_argument("--themes", help="Local themes.json (default: R2 themes.json on --upload)")
    b.set_defaults(func=build)

    s = sub.add_parser("show", help="Print full hole details from R2 for local review")
    s.add_argument("--wiki", default="simplewiki")
    s.add_argument("--via", choices=["wrangler", "keys"], default="wrangler", help="R2 access")
    s.add_argument("--dates", nargs="+", help="Specific dates; default is all in the index")
    s.add_argument("--through", help="Only holes up to this date")
    s.add_argument("--status", choices=["queued", "approved"], help="Only holes with this status")
    s.set_defaults(func=show)

    ck = sub.add_parser("check", help="Re-check R2 holes against the content policy (review step)")
    ck.add_argument("--wiki", default="simplewiki")
    ck.add_argument("--via", choices=["wrangler", "keys"], default="wrangler", help="R2 access")
    ck.add_argument("--dates", nargs="+", help="Specific dates; default is all in the index")
    ck.add_argument("--through", help="Only holes up to this date")
    ck.add_argument("--status", choices=["queued", "approved"], help="Only holes with this status")
    ck.set_defaults(func=check)

    a = sub.add_parser("approve", help="Mark queued holes as approved in R2")
    a.add_argument("--wiki", default="simplewiki")
    a.add_argument("--via", choices=["wrangler", "keys"], default="wrangler", help="R2 access")
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--dates", nargs="+")
    g.add_argument("--through", help="Approve every queued hole up to this date")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=approve)

    r = sub.add_parser(
        "relayout", help="One-off: move old holes/ and distances/ under a wiki prefix"
    )
    r.add_argument("--wiki", default="simplewiki")
    r.add_argument("--apply", action="store_true", help="Perform the copies (default: dry run)")
    r.add_argument("--delete-old", action="store_true", help="Delete originals after copying")
    r.set_defaults(func=relayout)

    c = sub.add_parser("clear", help="Delete a wiki's holes, distances and index from R2")
    c.add_argument("--wiki", default="simplewiki")
    c.add_argument("--apply", action="store_true", help="Perform the deletes (default: dry run)")
    c.set_defaults(func=clear)

    args = p.parse_args(argv)
    return args.func(args)
