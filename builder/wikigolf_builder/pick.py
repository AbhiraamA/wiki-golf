"""Choose one hole per date.

Par comes from the weekday schedule. Both endpoints must be recognisable: the target sits in the
top few percent of articles by incoming links and the start in the top fifth (the "fame filter").
Difficulty is a function of the shortest distance, not of obscurity. Themed dates pin the target
from a private calendar and skip the fame filter for it (the owner chose it), then find a
well-known start at a fitting distance. See plan.md section 5.3 and themes.py.
"""

from __future__ import annotations

import datetime as dt
import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .bfs import distances_to
from .config import HOLE_EPOCH, MAX_DISTANCE, PAR_RANGES, PickSettings
from .graph import Graph
from .themes import Theme
from .verify import first_broken_edge


@dataclass
class Hole:
    date: str
    hole_no: int
    par: int
    shortest: int
    start: int
    target: int
    difficulty: float
    route: list[int]  # one verified shortest route, start..target
    dist: np.ndarray
    badge: dict | None = None  # {label, emoji} on themed days, else None

    @property
    def pick_up(self) -> int:
        return self.par * 2


@dataclass
class History:
    """Past holes, by title and role, used for the no-repeat rules.

    Start and target reuse are tracked separately so each can have its own window: a target is the
    memorable destination (no repeat for a year), while a start is only the jumping-off point (it
    may come round again sooner). The exact (start, target) pair is never reused.
    """

    target_dates: dict[str, list[str]]  # title -> dates used as a target
    start_dates: dict[str, list[str]]  # title -> dates used as a start
    pairs: set[tuple[str, str]]

    @classmethod
    def from_index(cls, entries: list[dict]) -> History:
        h = cls(target_dates={}, start_dates={}, pairs=set())
        for e in entries:
            if "start" in e and "target" in e:
                h.add(e["date"], e["start"], e["target"])
        return h

    def add(self, date: str, start: str, target: str) -> None:
        self.start_dates.setdefault(start, []).append(date)
        self.target_dates.setdefault(target, []).append(date)
        self.pairs.add((start, target))

    @staticmethod
    def _recent(dates: list[str], date: str, window_days: int) -> bool:
        d = dt.date.fromisoformat(date)
        return any(abs((d - dt.date.fromisoformat(x)).days) < window_days for x in dates)

    def target_recent(self, title: str, date: str, window_days: int) -> bool:
        return self._recent(self.target_dates.get(title, ()), date, window_days)

    def start_recent(self, title: str, date: str, window_days: int) -> bool:
        return self._recent(self.start_dates.get(title, ()), date, window_days)


def par_for(date: str) -> int:
    lo, hi = PAR_RANGES[dt.date.fromisoformat(date).weekday()]
    return random.Random(date).randint(lo, hi)


def hole_number(date: str, epoch: str = HOLE_EPOCH) -> int:
    return (dt.date.fromisoformat(date) - dt.date.fromisoformat(epoch)).days + 1


def difficulty_from_distance(d: int) -> float:
    """0..1, driven only by how many clicks the shortest route is."""
    return round(min(d, MAX_DISTANCE) / MAX_DISTANCE, 2)


def fame_threshold(counts: np.ndarray, top_fraction: float) -> int:
    """Smallest count that puts an article in roughly the top `top_fraction` of `counts`."""
    return int(np.quantile(counts, 1.0 - top_fraction))


def shortest_route(g: Graph, start: int, dist: np.ndarray) -> list[int]:
    """One shortest route (at each step, the lowest-index link that gets one click closer)."""
    route = [start]
    cur = start
    while dist[cur] > 0:
        nxt = next(int(v) for v in g.out_links(cur) if dist[v] == dist[cur] - 1)
        route.append(nxt)
        cur = nxt
    return route


class Picker:
    def __init__(
        self,
        g: Graph,
        excluded: np.ndarray,
        settings: PickSettings,
        history: History,
        fetch_html: Callable[[int], str] | None,
        view_lookup: Callable[[str], int | None] | None = None,
        sensitive: Callable[[int], str | None] | None = None,
        log=print,
    ) -> None:
        self.g = g
        self.s = settings
        self.history = history
        self.fetch_html = fetch_html
        self.view_lookup = view_lookup  # en title -> monthly pageviews (None if no such article)
        # idx -> reason if a target is a sensitive topic (murderer, drug, conspiracy theory, …).
        self.sensitive = sensitive
        self.sensitive_dropped = 0  # count only; reasons/titles stay out of the public log
        self.log = log
        # Fame uses interlanguage-link count, not inlinks: navboxes inflate inlinks but not the
        # number of other-language Wikipedias that cover a topic. Targets are in the top
        # `target_langlink_fraction`; a real-readership floor is applied lazily in _famous_enough.
        self.langlink_thresh = fame_threshold(g.langlinks, settings.target_langlink_fraction)
        self.target_ok = ~excluded & (g.langlinks >= self.langlink_thresh)
        # Starts only need to be readable: the light `excluded` filter (stub/list/year/music/
        # Olympics) is the whole bar, with no fame requirement.
        self.start_ok = ~excluded
        self.removed_edges: list[tuple[int, int]] = []

    def fame_summary(self) -> str:
        views = (
            f" and >= {self.s.min_target_views:,} enwiki monthly views"
            if self.view_lookup is not None
            else " (pageview check off)"
        )
        sens = "on" if self.sensitive is not None else "off"
        return (
            f"fame filter: targets = top {self.s.target_langlink_fraction:.0%} by interlanguage "
            f"links (>= {self.langlink_thresh} langlinks, {int(self.target_ok.sum())} articles)"
            f"{views}; starts = {int(self.start_ok.sum())} readable articles; "
            f"sensitive-target filter {sens}"
        )

    def _famous_enough(self, idx: int) -> bool:
        """A target also needs real readership: enough enwiki pageviews for the same title."""
        if self.view_lookup is None:
            return True
        views = self.view_lookup(self.g.en_title[idx] or self.g.titles[idx])
        if views is None:  # no English article for this title: judge on langlinks alone
            return True
        return views >= self.s.min_target_views

    def _sensitive_target(self, idx: int) -> bool:
        """True if the target is a sensitive topic (and should not be a destination)."""
        if self.sensitive is None:
            return False
        if self.sensitive(idx) is not None:
            self.sensitive_dropped += 1
            return True
        return False

    def _fresh_target(self, idx: int, date: str) -> bool:
        window = self.s.target_repeat_window_days
        return not self.history.target_recent(self.g.titles[idx], date, window)

    def _fresh_start(self, idx: int, date: str) -> bool:
        window = self.s.start_repeat_window_days
        return not self.history.start_recent(self.g.titles[idx], date, window)

    def _find_start(self, target: int, dist: np.ndarray, dist_list, date, rng):
        """A well-known, fresh start at one of `dist_list` clicks from the target. (start, used_d)."""
        for used_d in dist_list:
            pool = [
                int(x)
                for x in np.flatnonzero(self.start_ok & (dist == used_d))
                if int(x) != target
                and self._fresh_start(int(x), date)
                and (self.g.titles[int(x)], self.g.titles[target]) not in self.history.pairs
            ]
            if pool:
                rng.shuffle(pool)
                return pool[0], used_d
        return None

    def _one_candidate(self, targets, dist_list, date, rng, check_sensitive=True):
        """First (start, target, dist, used_d) over `targets` with a start at a `dist_list` click.

        Sensitivity is checked lazily here, only for targets actually tried (in shuffled order),
        so a build makes a Wikidata call per attempted target, not per shortlisted one. Themed
        targets are owner-chosen, so the caller passes check_sensitive=False.
        """
        for t in targets:
            if check_sensitive and self._sensitive_target(t):
                continue
            dist = distances_to(t, self.g.rev_off, self.g.rev_tgt, self.g.n)
            found = self._find_start(t, dist, dist_list, date, rng)
            if found is not None:
                return found[0], t, dist, found[1]
        return None

    def _verify(self, route: list[int]) -> tuple[int, int] | None:
        if self.fetch_html is None:
            return None
        return first_broken_edge(route, self.g.rev_ids, self.g.title_to_idx, self.fetch_html)

    def _drop(self, broken: tuple[int, int], date: str) -> None:
        # No titles in the log: build output is public (see render_summary).
        self.log(f"  {date}: a route link was missing from the page HTML; dropped, retrying")
        self.g.remove_edge(*broken)
        self.removed_edges.append(broken)

    def _finish(self, date, d, start, target, dist, route, badge) -> Hole:
        self.history.add(date, self.g.titles[start], self.g.titles[target])
        return Hole(
            date=date,
            hole_no=hole_number(date),
            par=d + 1,
            shortest=d,
            start=start,
            target=target,
            difficulty=difficulty_from_distance(d),
            route=route,
            dist=dist,
            badge=badge,
        )

    def _resolve(self, title: str) -> int | None:
        key = title.replace(" ", "_")
        idx = self.g.title_to_idx.get(key)
        if idx is None and key:
            idx = self.g.title_to_idx.get(key[0].upper() + key[1:])
        return idx

    def pick(self, date: str) -> Hole | None:
        """A regular hole: famous target, well-known start, at the day's par."""
        par = par_for(date)
        d = par - 1
        rng = random.Random(f"{date}|{self.g.snap}")
        cands = [int(i) for i in np.flatnonzero(self.target_ok) if self._fresh_target(int(i), date)]
        rng.shuffle(cands)
        # The pageview floor needs a network call each, so apply it only to the day's shortlist.
        cands = [i for i in cands[: self.s.candidates_per_day] if self._famous_enough(i)]
        for _ in range(self.s.max_verify_attempts):
            cand = self._one_candidate(cands, [d], date, rng)
            if cand is None:
                return None
            start, target, dist, used_d = cand
            route = shortest_route(self.g, start, dist)
            broken = self._verify(route)
            if broken is None:
                return self._finish(date, used_d, start, target, dist, route, None)
            self._drop(broken, date)
        return None

    def pick_themed(self, date: str, theme: Theme) -> Hole | None:
        """A themed hole: the owner's chosen target (fame filter skipped), well-known start.

        Returns None (so the caller falls back to a normal hole) if the target is not in this
        wiki, or no well-known start fits even after widening the par.
        """
        d0 = par_for(date) - 1
        rng = random.Random(f"{date}|{self.g.snap}|theme")
        targets = [i for i in (self._resolve(t) for t in theme.targets) if i is not None]
        # Keep distinct, in a date-seeded order.
        targets = list(dict.fromkeys(targets))
        rng.shuffle(targets)
        if not targets:
            self.log(f"{date}: themed target not in this wiki; falling back to a normal hole")
            return None
        dist_list = _widen(d0, self.s.theme_par_widen)
        badge = theme.badge.to_json() if theme.badge else None
        for _ in range(self.s.max_verify_attempts):
            cand = self._one_candidate(targets, dist_list, date, rng, check_sensitive=False)
            if cand is None:
                self.log(
                    f"{date}: no well-known start for the themed hole within par "
                    f"{d0 + 1}±{self.s.theme_par_widen}; falling back to a normal hole"
                )
                return None
            start, target, dist, used_d = cand
            if used_d != d0:
                self.log(f"{date}: widened themed hole to par {used_d + 1} to fit a start")
            route = shortest_route(self.g, start, dist)
            broken = self._verify(route)
            if broken is None:
                return self._finish(date, used_d, start, target, dist, route, badge)
            self._drop(broken, date)
        return None


def _widen(d0: int, widen: int) -> list[int]:
    """Distances to try, exact first then ±1, ±2 …, dropping anything below 1 click."""
    out = [d0]
    for k in range(1, widen + 1):
        out += [d0 + k, d0 - k]
    return [d for d in out if d >= 1]
