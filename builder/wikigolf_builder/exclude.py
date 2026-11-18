"""Pages that may not be a start or target (they can still appear mid-route). plan.md 5.4."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# Parenthetical disambiguators for music works, e.g. "Thriller_(album)", "Hello_(2015_song)".
_MUSIC = "album|song|single|EP|soundtrack|mixtape|opera|musical"
_PATTERNS = [
    re.compile(r"^Lists?_of_", re.I),
    # Navigational/index pages: "Index of…", "Glossary of…", "Outline of…", "Timeline of…".
    re.compile(r"^(Index|Glossary|Outline|Timeline|Comparison|Table)_of_", re.I),
    re.compile(r"_[–—-]_[A-Z0-9]$"),  # by-letter index: "UK_railway_stations_–_U"
    re.compile(r"_discography$", re.I),  # "Beatles_discography"
    re.compile(r"^\d{1,4}(_(BC|BCE|AD|CE))?$"),  # years: 1999, 44_BC
    re.compile(r"^(AD_)\d{1,4}$"),
    re.compile(r"^\d{1,4}0s(_(BC|BCE))?$"),  # decades: 1990s
    re.compile(r"^\d{1,2}(st|nd|rd|th)_(century|millennium)(_(BC|BCE))?$", re.I),
    re.compile(rf"^({_MONTHS})(_\d{{1,2}})?(,?_\d{{1,4}})?$"),  # March, March_3, March_1999
    re.compile(rf"^\d{{1,2}}_({_MONTHS})$"),  # 3_March
    re.compile(r"_\(disambiguation\)$", re.I),
    # Music works by their disambiguator: "(album)", "(1999 song)", "(Beatles album)", "(EP)".
    re.compile(rf"_\([^)]*\b({_MUSIC})\)$", re.I),
    # "X at the Olympics" results pages: "Germany_at_the_2008_Summer_Olympics", "Athletics_at_the_…
    # Olympic_Games", Paralympics. Fine mid-route, but a dull start or target.
    re.compile(r"_at_the_.*(Olympic|Paralympic)", re.I),
    # Technical standards/codes: "ISO_4217", "ISO/IEC_27001", "ISO_8601". High fame signals
    # (linked everywhere, many langlinks) but no one recognises the number and they aren't aimable.
    re.compile(r"^ISO(/IEC)?[_ ]?\d", re.I),
    # Wikimedia's own projects: linked from everywhere (huge fame signals) but self-referential and
    # unrecognisable to most players. "Wikipedia" the article is excluded too (meta for this game).
    re.compile(
        r"^(Wikipedia|Wiktionary|Wikiquote|Wikisource|Wikibooks|Wikinews|Wikiversity"
        r"|Wikivoyage|Wikidata|Wikispecies|Wikifunctions|MediaWiki|Wikimedia(_.*)?)$"
    ),
]


def norm(title: str) -> str:
    return title.strip().replace(" ", "_").casefold()


def load_blocklist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(norm(line))
    return out


def title_excluded(title: str, blocklist: set[str]) -> bool:
    return norm(title) in blocklist or any(p.search(title) for p in _PATTERNS)


def excluded_mask(
    titles: list[str],
    disambig: np.ndarray,
    page_len: np.ndarray,
    min_page_len: int,
    blocklist: set[str],
) -> np.ndarray:
    by_title = np.fromiter((title_excluded(t, blocklist) for t in titles), bool, len(titles))
    return by_title | disambig | (page_len < min_page_len)
