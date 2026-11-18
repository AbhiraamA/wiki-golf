"""Builder settings. Shared values come from shared/config.json so TS and Python agree."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_CONFIG_PATH = REPO_ROOT / "shared" / "config.json"
BLOCKLIST_PATH = Path(__file__).resolve().parents[1] / "blocklist.txt"

SHARED = json.loads(SHARED_CONFIG_PATH.read_text(encoding="utf-8"))

APP_VERSION: str = SHARED["appVersion"]
HOLE_EPOCH: str = SHARED["holeEpoch"]
PAGE_CHUNK_SIZE: int = SHARED["pageChunkSize"]
USER_AGENT = f"WikiGolf/{APP_VERSION} ({SHARED['repoUrl']}; {SHARED['contactEmail']})"

NO_ROUTE = 255

# Par range by weekday (Monday = 0), per plan.md section 1.
PAR_RANGES: dict[int, tuple[int, int]] = {
    0: (3, 4),
    1: (3, 4),
    2: (4, 5),
    3: (4, 5),
    4: (4, 6),
    5: (4, 6),
    6: (6, 7),
}

# Longest shortest-distance a hole can have (Sunday par 7 → 6 clicks). Used to scale difficulty.
MAX_DISTANCE = 6


@dataclass(frozen=True)
class PickSettings:
    """Thresholds for choosing holes.

    A target must be *famous*: in the top `target_langlink_fraction` of articles by interlanguage
    links (a navbox-proof fame signal, unlike raw inlinks) AND drawing at least `min_target_views`
    monthly pageviews on English Wikipedia for the same title (Simple English's own traffic is too
    small to rank by). A start only needs to be readable: not a stub, list, year/date, music page
    or "X at the Olympics" page (see exclude.py). Difficulty comes from distance (plan.md section
    1), not from obscurity.
    """

    target_langlink_fraction: float = 0.05  # targets: top 5% of articles by interlanguage links
    min_target_views: int = 30000  # targets: at least this many enwiki pageviews last month
    min_page_len: int = 2000  # below this a page counts as a stub (start/target excluded)
    candidates_per_day: int = 60
    starts_per_target: int = 12
    target_repeat_window_days: int = 365  # a target can't return for a year (the memorable role)
    start_repeat_window_days: int = 90  # a start may return sooner; it's just the jumping-off point
    max_verify_attempts: int = 12
    theme_par_widen: int = 1  # on a themed day, par may shift by up to this to fit a start


@dataclass(frozen=True)
class WikiSettings:
    wiki: str
    lang: str
    shard_count: int
    pick: PickSettings = field(default_factory=PickSettings)


def wiki_settings(wiki: str) -> WikiSettings:
    try:
        w = SHARED["wikis"][wiki]
    except KeyError:
        raise SystemExit(f"Unknown wiki {wiki!r}; known: {', '.join(SHARED['wikis'])}") from None
    pick = PickSettings(min_page_len=5000) if wiki == "enwiki" else PickSettings()
    return WikiSettings(wiki=wiki, lang=w["lang"], shard_count=w["shardCount"], pick=pick)
