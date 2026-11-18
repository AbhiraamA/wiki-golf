"""Locate and open dump files, from dumps.wikimedia.org or a local folder (tests)."""

from __future__ import annotations

import gzip
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import requests

from . import net

BASE = "https://dumps.wikimedia.org"
TABLES = ("page", "redirect", "page_props", "langlinks", "linktarget", "pagelinks")
JOBS = {
    "page": "pagetable",
    "redirect": "redirecttable",
    "page_props": "pagepropstable",
    "langlinks": "langlinkstable",
    "linktarget": "linktargettable",
    "pagelinks": "pagelinkstable",
}


class DumpSource:
    wiki: str
    dump_date: str

    @contextmanager
    def open(self, table: str) -> Iterator[BinaryIO]:  # pragma: no cover - interface
        raise NotImplementedError
        yield


@dataclass
class LocalDumps(DumpSource):
    """Reads `{table}.sql` or `{table}.sql.gz` from a folder."""

    folder: Path
    wiki: str
    dump_date: str

    @contextmanager
    def open(self, table: str) -> Iterator[BinaryIO]:
        gz = self.folder / f"{table}.sql.gz"
        if gz.exists():
            with gzip.open(gz, "rb") as f:
                yield f
        else:
            with open(self.folder / f"{table}.sql", "rb") as f:
                yield f


@dataclass
class RemoteDumps(DumpSource):
    """Streams gzip dumps over HTTP straight into the parser; nothing unzipped touches disk."""

    session: requests.Session
    wiki: str
    dump_date: str
    urls: dict[str, str]

    @contextmanager
    def open(self, table: str) -> Iterator[BinaryIO]:
        raw = net.ResumableStream(self.session, self.urls[table])
        try:
            with gzip.GzipFile(fileobj=raw, mode="rb") as f:
                yield f
        finally:
            raw.close()


def find_remote(session: requests.Session, wiki: str, dump_date: str | None) -> RemoteDumps:
    """Use `dump_date`, or the newest dated folder where every needed table is done."""
    if dump_date:
        dates = [dump_date]
    else:
        listing = net.get(session, f"{BASE}/{wiki}/").text
        dates = sorted(set(re.findall(r'href="(\d{8})/"', listing)), reverse=True)[:4]
    for date in dates:
        try:
            status = net.get(session, f"{BASE}/{wiki}/{date}/dumpstatus.json").json()
        except (requests.HTTPError, RuntimeError, ValueError):
            continue
        urls: dict[str, str] = {}
        for table in TABLES:
            job = status.get("jobs", {}).get(JOBS[table], {})
            if job.get("status") != "done":
                break
            name = f"{wiki}-{date}-{table}.sql.gz"
            info = job.get("files", {}).get(name)
            if not info:
                break
            urls[table] = BASE + info["url"]
        if len(urls) == len(TABLES):
            return RemoteDumps(session=session, wiki=wiki, dump_date=date, urls=urls)
    raise SystemExit(f"No complete dump found for {wiki} (tried {', '.join(dates)})")
