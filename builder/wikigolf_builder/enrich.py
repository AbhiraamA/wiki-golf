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
from .sensitive import CLAIM_PROPS, sensitive_by_description, sensitive_reason

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


def make_sensitivity(
    g: Graph, session: requests.Session | None, lang: str, log=print
) -> Callable[[int], str | None]:
    """idx -> a reason string if the article is a sensitive *target* topic, else None.

    Combines three signals (see sensitive.py): the local short description, and - when online - the
    Wikidata item's description and its instance-of/subclass-of/occupation claims. Degrades quietly
    to the local-description check alone on any network trouble, so a build never fails here; the
    blocklist is the backstop for topics neither Wikidata nor the description flags.
    """
    want = list(dict.fromkeys(["en", lang]))
    throttle = _Throttle(MIN_INTERVAL)
    cache: dict[str, str | None] = {}

    def wikidata(qid: str) -> str | None:
        if qid in cache:
            return cache[qid]
        params = (
            f"?action=wbgetentities&ids={quote(qid)}&props=descriptions|claims"
            f"&languages={'|'.join(want)}&format=json&formatversion=2"
        )
        reason: str | None = None
        throttle.wait()
        try:
            ent = net.get(session, WIKIDATA_API + params).json().get("entities", {}).get(qid, {})
            descs = ent.get("descriptions", {})
            desc = next(
                (str(descs[c].get("value", "")) for c in want if c in descs),
                "",
            )
            claims = ent.get("claims", {})
            qids = [
                v["mainsnak"]["datavalue"]["value"]["id"]
                for prop in CLAIM_PROPS
                for v in claims.get(prop, [])
                if v.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
            ]
            reason = sensitive_reason(desc, qids)
        except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError):
            reason = None
        cache[qid] = reason
        return reason

    def sensitivity(idx: int) -> str | None:
        local = sensitive_by_description(g.shortdesc[idx])
        if local:
            return local
        qid = g.qid[idx]
        if qid and session is not None:
            return wikidata(qid)
        return None

    return sensitivity
