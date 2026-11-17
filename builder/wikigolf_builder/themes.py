"""Themed days: a private calendar (R2 `themes.json`, never in the repo) that pins the target
article for a date — a holiday, an anniversary — and a badge the tee screen can show.

A theme's `when` is either a fixed month/day, the nth weekday of a month (n may be negative for
"last"), or Easter Sunday (with an optional day offset). Each theme maps to one target title or a
small pool, plus an optional badge {label, emoji}. The builder picks the target (owner's choice,
so it skips the fame filter) and then finds a well-known start at a fitting distance.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class Badge:
    label: str
    emoji: str

    def to_json(self) -> dict:
        return {"label": self.label, "emoji": self.emoji}


@dataclass(frozen=True)
class Theme:
    id: str
    when: dict
    targets: tuple[str, ...]  # one target or a small pool (titles; spaces or underscores)
    badge: Badge | None

    def matches(self, d: dt.date) -> bool:
        return _date_for(self.when, d.year) == d


def easter_sunday(year: int) -> dt.date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """The nth (1-based) `weekday` in a month; n = -1 for the last one."""
    if n > 0:
        first = dt.date(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + dt.timedelta(days=offset + 7 * (n - 1))
    # Last occurrence: step back from the first day of the next month.
    nxt = dt.date(year + (month == 12), (month % 12) + 1, 1)
    last = nxt - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def _date_for(when: dict, year: int) -> dt.date:
    kind = when["type"]
    if kind == "fixed":
        return dt.date(year, int(when["month"]), int(when["day"]))
    if kind == "nth_weekday":
        wd = when["weekday"]
        idx = WEEKDAYS[wd.lower()] if isinstance(wd, str) else int(wd)
        return nth_weekday(year, int(when["month"]), idx, int(when["n"]))
    if kind == "easter":
        return easter_sunday(year) + dt.timedelta(days=int(when.get("offset", 0)))
    raise ValueError(f"Unknown theme 'when' type: {kind!r}")


def load_themes(data: dict | None) -> list[Theme]:
    """Parse a themes.json document. Tolerant of a missing/empty file (returns [])."""
    if not data:
        return []
    out: list[Theme] = []
    for raw in data.get("themes", []):
        targets = raw.get("targets") or ([raw["target"]] if raw.get("target") else [])
        if not targets:
            raise ValueError(f"Theme {raw.get('id')!r} has no targets")
        badge = None
        if raw.get("badge"):
            badge = Badge(label=raw["badge"]["label"], emoji=raw["badge"]["emoji"])
        theme = Theme(
            id=str(raw.get("id", "")),
            when=raw["when"],
            targets=tuple(targets),
            badge=badge,
        )
        _date_for(theme.when, 2000)  # validate the rule early
        out.append(theme)
    return out


def theme_for(date: str, themes: list[Theme]) -> Theme | None:
    d = dt.date.fromisoformat(date)
    for theme in themes:
        if theme.matches(d):
            return theme
    return None
