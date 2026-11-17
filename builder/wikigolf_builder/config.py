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

    Fame is a percentile of incoming-link count, so both endpoints are recognisable: targets sit
    in the top `target_top_fraction` of articles by inlinks. Starts are tiered by hole length,
    because few famous articles sit far from a famous target: short holes (distance <
    `long_distance`) demand a well-known start (top `start_top_fraction_short`), while long holes
    keep a looser bar (top `start_top_fraction_long`) so they can still be built. Difficulty comes
    from distance (plan.md section 1), not from obscurity.
    """

    target_top_fraction: float = 0.03  # targets: top 3% of articles by incoming links
    start_top_fraction_short: float = 0.08  # starts for short holes (distance < long_distance)
    start_top_fraction_long: float = 0.20  # starts for long holes (distance >= long_distance)
    long_distance: int = 5  # a hole is "long" at this shortest distance or more (par 6+)
    min_page_len: int = 2000  # below this a page counts as a stub (start/target excluded)
    candidates_per_day: int = 60
    starts_per_target: int = 12
    repeat_window_days: int = 365
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
