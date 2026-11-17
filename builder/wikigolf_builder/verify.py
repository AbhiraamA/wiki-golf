"""Check a route against the real article HTML (Parsoid) for the pinned revisions."""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from urllib.parse import unquote

import requests

from . import net

_ANCHOR_RE = re.compile(r"<a\s[^>]*>", re.I)
_HREF_RE = re.compile(r'href="\./([^"]+)"')


def revision_url(lang: str, rev_id: int) -> str:
    return f"https://{lang}.wikipedia.org/w/rest.php/v1/revision/{rev_id}/html"


def html_fetcher(session: requests.Session, lang: str) -> Callable[[int], str]:
    cache: dict[int, str] = {}

    def fetch(rev_id: int) -> str:
        if rev_id not in cache:
            cache[rev_id] = net.get(session, revision_url(lang, rev_id)).text
        return cache[rev_id]

    return fetch


def link_titles(page_html: str) -> list[str]:
    """Titles of `rel="mw:WikiLink"` links in Parsoid HTML, in document order, underscored."""
    out = []
    for tag in _ANCHOR_RE.findall(page_html):
        if "mw:WikiLink" not in tag or "mw:WikiLink/Interwiki" in tag:
            continue
        m = _HREF_RE.search(tag)
        if not m:
            continue
        target = html.unescape(m.group(1)).split("#", 1)[0].split("?", 1)[0]
        title = unquote(target).replace(" ", "_")
        if title:
            out.append(title)
    return out


def linked_indices(page_html: str, title_to_idx: dict[str, int]) -> set[int]:
    out = set()
    for title in link_titles(page_html):
        idx = title_to_idx.get(title)
        if idx is None and title:
            idx = title_to_idx.get(title[0].upper() + title[1:])
        if idx is not None:
            out.add(idx)
    return out


def first_broken_edge(
    route: list[int],
    rev_ids,
    title_to_idx: dict[str, int],
    fetch: Callable[[int], str],
) -> tuple[int, int] | None:
    """Return the first (u, v) on the route whose link is missing from u's HTML, or None."""
    for u, v in zip(route, route[1:], strict=False):
        if v not in linked_indices(fetch(int(rev_ids[u])), title_to_idx):
            return (u, v)
    return None
