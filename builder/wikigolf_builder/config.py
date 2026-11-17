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

# Target difficulty score (0 easy .. 1 hard) by weekday; the picker keeps the closest pair.
TARGET_DIFFICULTY: dict[int, float] = {
    0: 0.35,
    1: 0.35,
    2: 0.45,
    3: 0.45,
    4: 0.55,
    5: 0.55,
    6: 0.65,
}


@dataclass(frozen=True)
class PickSettings:
    """Thresholds for choosing holes. Defaults follow plan.md section 5.3."""

    target_min_in: int = 20
    target_max_in: int = 2000
    start_min_in: int = 200
    min_page_len: int = 2000
    hub_count: int = 1000
    candidates_per_day: int = 40
    starts_per_target: int = 12
    repeat_window_days: int = 365
    max_verify_attempts: int = 12


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
