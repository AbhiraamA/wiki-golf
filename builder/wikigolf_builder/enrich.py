"""Online enrichment for the picker and the hole files, over Wikimedia's public APIs.

Two things live here, both keyed off data already in the graph:

* `make_view_lookup` - monthly pageviews for a title on *English* Wikipedia (the project User-Agent
  and a courtesy rate limit apply). Simple English's own traffic is too small to rank targets by,
  so fame is judged on the English article for the same title.
* `make_describe` - a one-line short description for a hole endpoint: the local wikibase-shortdesc
  if the article has one, else the Wikidata item's description.

Both degrade quietly to "unknown" (None / "") on any network trouble so a build never fails on an
API hiccup; callers treat a missing pageview count as "judge on interlanguage links alone".
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from urllib.parse import quote

import requests

from . import net
from .graph import SHORTDESC_MAX, Graph
from .sensitive import (
    sensitive_by_description,
    start_policy_reason,
    target_policy_reason,
)

PAGEVIEW_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
PAGEVIEW_PROJECT = "en.wikipedia.org"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MIN_INTERVAL = 0.05  # seconds between API calls: stay well under Wikimedia's rate limit


def latest_complete_month(today: dt.date) -> tuple[str, str]:
    """(start, end) as YYYYMMDD for the most recent fully elapsed month before `today`."""
    first_this = today.replace(day=1)
    last_day = first_this - dt.timedelta(days=1)  # last day of the previous month
    start = last_day.replace(day=1)
    return start.strftime("%Y%m%d"), last_day.strftime("%Y%m%d")


class _Throttle:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.last = 0.0

    def wait(self) -> None:
        gap = self.interval - (time.monotonic() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.monotonic()


def make_view_lookup(
    session: requests.Session, today: dt.date, log=print
) -> Callable[[str], int | None]:
    """title -> English-Wikipedia pageviews last month, None if there is no such article."""
    start, end = latest_complete_month(today)
    cache: dict[str, int | None] = {}
    throttle = _Throttle(MIN_INTERVAL)
    failures = [0]

    def lookup(title: str) -> int | None:
        if title in cache:
            return cache[title]
        path = quote(title.replace(" ", "_"), safe="")
        url = f"{PAGEVIEW_API}/{PAGEVIEW_PROJECT}/all-access/user/{path}/monthly/{start}/{end}"
        throttle.wait()
        views: int | None = None
        try:
            resp = net.get(session, url)
            views = sum(int(item.get("views", 0)) for item in resp.json().get("items", []))
        except requests.HTTPError as err:
            # 404 => no such English article (expected); anything else is a real failure.
            if err.response is None or err.response.status_code != 404:
                failures[0] += 1
        except (requests.RequestException, RuntimeError, ValueError):
            failures[0] += 1
        cache[title] = views
        return views

    lookup.failures = failures  # type: ignore[attr-defined]
    lookup.month = f"{start}..{end}"  # type: ignore[attr-defined]
    return lookup


def make_describe(
    g: Graph, session: requests.Session | None, lang: str, log=print
) -> Callable[[int], str]:
    """idx -> short description: local wikibase-shortdesc, else the Wikidata item description."""
    want = list(dict.fromkeys(["en", lang]))  # prefer English, then the wiki's own language
    throttle = _Throttle(MIN_INTERVAL)
    cache: dict[str, str] = {}

    def wikidata(qid: str) -> str:
        if qid in cache:
            return cache[qid]
        params = (
            f"?action=wbgetentities&ids={quote(qid)}&props=descriptions"
            f"&languages={'|'.join(want)}&format=json&formatversion=2"
        )
        desc = ""
        throttle.wait()
        try:
            data = net.get(session, WIKIDATA_API + params).json()
            descs = data.get("entities", {}).get(qid, {}).get("descriptions", {})
            for code in want:
                if code in descs:
                    desc = str(descs[code].get("value", ""))[:SHORTDESC_MAX]
                    break
        except (requests.RequestException, RuntimeError, ValueError):
            desc = ""
        cache[qid] = desc
        return desc

    def describe(idx: int) -> str:
        local = g.shortdesc[idx]
        if local:
            return local
        qid = g.qid[idx]
        if qid and session is not None:
            return wikidata(qid)
        return ""

    return describe


def _claim_ids(claims: dict, prop: str) -> list[str]:
    return [
        v["mainsnak"]["datavalue"]["value"]["id"]
        for v in claims.get(prop, [])
        if v.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
    ]


def _claim_time(claims: dict, prop: str) -> str | None:
    for v in claims.get(prop, []):
        val = v.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(val, dict) and val.get("time"):
            return str(val["time"])
    return None


def _extract_fields(ent: dict, want: list[str]) -> dict:
    """The content-policy fields we read from a Wikidata entity (see Policy)."""
    descs = ent.get("descriptions", {})
    claims = ent.get("claims", {})
    return {
        "desc": next((str(descs[c].get("value", "")) for c in want if c in descs), ""),
        "classes": _claim_ids(claims, "P31") + _claim_ids(claims, "P279"),
        "occupations": _claim_ids(claims, "P106"),
        "positions": _claim_ids(claims, "P39"),
        "convicted": _claim_ids(claims, "P1399"),
        "death": _claim_time(claims, "P570"),
    }


_EMPTY_FIELDS = {
    "desc": "",
    "classes": [],
    "occupations": [],
    "positions": [],
    "convicted": [],
    "death": None,
}


def fields_by_title(
    session: requests.Session, site: str, title: str, want: list[str]
) -> dict | None:
    """Content-policy fields for a wiki article, fetched from Wikidata by site+title in one call.

    Used by the review command to re-check existing holes in R2 without loading a dump. Returns
    None on any network/parse trouble (caller treats that as "couldn't check").
    """
    params = (
        f"?action=wbgetentities&sites={quote(site)}&titles={quote(title.replace('_', ' '))}"
        f"&props=descriptions|claims&languages={'|'.join(want)}&format=json&formatversion=2"
    )
    try:
        entities = net.get(session, WIKIDATA_API + params).json().get("entities", {})
        for qid, ent in entities.items():
            if not qid.startswith("-"):  # "-1" means no item for this title
                return _extract_fields(ent, want)
        return dict(_EMPTY_FIELDS)
    except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError):
        return None


class Policy:
    """Content-guide checks for a hole endpoint (see sensitive.py and CONTENT_GUIDE.md).

    `target_reason(idx)` / `start_reason(idx)` return a reason string if the article may not fill
    that role, else None. Offline (no session) they use the local short description only; online
    they also fetch the Wikidata item's description plus the claims the guide names - instance of /
    subclass of / occupation (classes), position held and politician occupation (modern politics),
    convicted-of P1399 (Tier A), and date of death P570 (recent-death and modern-politics cutoff).
    Every fetch is cached per QID and degrades quietly to "allowed" on any network trouble.
    """

    def __init__(
        self, g: Graph, session: requests.Session | None, lang: str, today: dt.date, log=print
    ) -> None:
        self.g = g
        self.session = session
        self.today = today
        self.log = log
        self.want = list(dict.fromkeys(["en", lang]))
        self.throttle = _Throttle(MIN_INTERVAL)
        self._cache: dict[str, dict] = {}  # qid -> extracted fields

    def _fields(self, qid: str) -> dict:
        if qid in self._cache:
            return self._cache[qid]
        params = (
            f"?action=wbgetentities&ids={quote(qid)}&props=descriptions|claims"
            f"&languages={'|'.join(self.want)}&format=json&formatversion=2"
        )
        self.throttle.wait()
        fields = dict(_EMPTY_FIELDS)
        try:
            ent = (
                net.get(self.session, WIKIDATA_API + params).json().get("entities", {}).get(qid, {})
            )
            fields = _extract_fields(ent, self.want)
        except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError):
            pass
        self._cache[qid] = fields
        return fields

    def _reason(self, idx: int, target: bool) -> str | None:
        # Local short description first (works offline).
        local = sensitive_by_description(self.g.shortdesc[idx], target=target)
        if local:
            return local
        qid = self.g.qid[idx]
        if not qid or self.session is None:
            return None
        f = self._fields(qid)
        if target:
            return target_policy_reason(
                desc=f["desc"],
                instance_classes=f["classes"],
                occupations=f["occupations"],
                positions_held=f["positions"],
                convicted_of=f["convicted"],
                death_iso=f["death"],
                today=self.today,
            )
        return start_policy_reason(
            desc=f["desc"],
            instance_classes=f["classes"],
            occupations=f["occupations"],
            convicted_of=f["convicted"],
            death_iso=f["death"],
            today=self.today,
        )

    def target_reason(self, idx: int) -> str | None:
        return self._reason(idx, target=True)

    def start_reason(self, idx: int) -> str | None:
        return self._reason(idx, target=False)


def make_policy(
    g: Graph, session: requests.Session | None, lang: str, today: dt.date, log=print
) -> Policy:
    """Build a Policy for this graph (see Policy)."""
    return Policy(g, session, lang, today, log=log)
