"""Choose one hole per date: par from the schedule, then a (start, target) pair. plan.md 5.3."""

from __future__ import annotations

import datetime as dt
import math
import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .bfs import distances_to, gather
from .config import HOLE_EPOCH, PAR_RANGES, TARGET_DIFFICULTY, PickSettings
from .graph import Graph
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
    routes: float
    route: list[int]  # one verified shortest route, start..target
    dist: np.ndarray

    @property
    def pick_up(self) -> int:
        return self.par * 2


@dataclass
class History:
    """Past holes, by title, used for the no-repeat rules."""

    used: dict[str, list[str]]  # title -> dates used as start or target
    pairs: set[tuple[str, str]]

    @classmethod
    def from_index(cls, entries: list[dict]) -> History:
        h = cls(used={}, pairs=set())
        for e in entries:
            if "start" in e and "target" in e:
                h.add(e["date"], e["start"], e["target"])
        return h

    def add(self, date: str, start: str, target: str) -> None:
        self.used.setdefault(start, []).append(date)
        self.used.setdefault(target, []).append(date)
        self.pairs.add((start, target))

    def recent(self, title: str, date: str, window_days: int) -> bool:
        d = dt.date.fromisoformat(date)
        return any(
            abs((d - dt.date.fromisoformat(x)).days) < window_days for x in self.used.get(title, ())
        )


def par_for(date: str) -> int:
    lo, hi = PAR_RANGES[dt.date.fromisoformat(date).weekday()]
    return random.Random(date).randint(lo, hi)


def hole_number(date: str, epoch: str = HOLE_EPOCH) -> int:
    return (dt.date.fromisoformat(date) - dt.date.fromisoformat(epoch)).days + 1


def route_stats(g: Graph, start: int, dist: np.ndarray, hubs: np.ndarray) -> tuple[float, float]:
    """(number of distinct shortest routes, share of on-route pages that are hubs)."""
    d = int(dist[start])
    layer = np.array([start], dtype=np.int64)
    ways = np.ones(1)
    middle: list[np.ndarray] = []
    for k in range(d, 0, -1):
        srcs, nbrs = gather(g.fwd_off, g.fwd_tgt, layer)
        keep = dist[nbrs] == k - 1
        srcs, nbrs = srcs[keep], nbrs[keep]
        nxt = np.unique(nbrs)
        nxt_ways = np.zeros(len(nxt))
        np.add.at(nxt_ways, np.searchsorted(nxt, nbrs), ways[np.searchsorted(layer, srcs)])
        if k > 1:
            middle.append(nxt)
        layer, ways = nxt, nxt_ways
    total_ways = float(ways.sum())
    inner = np.concatenate(middle) if middle else np.zeros(0, dtype=np.int64)
    hub_share = float(hubs[inner].mean()) if inner.size else 0.0
    return total_ways, hub_share


def difficulty_score(routes: float, target_in: int, hub_share: float, s: PickSettings) -> float:
    route_term = 1.0 / (1.0 + math.log10(max(routes, 1.0)))
    span = math.log(s.target_max_in / s.target_min_in)
    back_term = 1.0 - math.log(max(target_in, s.target_min_in) / s.target_min_in) / span
    back_term = min(max(back_term, 0.0), 1.0)
    hub_term = 1.0 - hub_share
    return round((route_term + back_term + hub_term) / 3.0, 3)


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
        log=print,
    ) -> None:
        self.g = g
        self.s = settings
        self.history = history
        self.fetch_html = fetch_html
        self.log = log
        indeg = g.in_degree()
        self.indeg = indeg
        self.target_ok = ~excluded & (indeg >= settings.target_min_in)
        self.target_ok &= indeg <= settings.target_max_in
        self.start_ok = ~excluded & (indeg >= settings.start_min_in)
        hubs = np.zeros(g.n, dtype=bool)
        hubs[np.argsort(-indeg, kind="stable")[: settings.hub_count]] = True
        self.hubs = hubs
        self.removed_edges: list[tuple[int, int]] = []

    def _fresh(self, idx: int, date: str) -> bool:
        return not self.history.recent(self.g.titles[idx], date, self.s.repeat_window_days)

    def pick(self, date: str) -> Hole | None:
        par = par_for(date)
        d = par - 1
        goal = TARGET_DIFFICULTY[dt.date.fromisoformat(date).weekday()]
        rng = random.Random(f"{date}|{self.g.snap}")
        cands = [int(i) for i in np.flatnonzero(self.target_ok) if self._fresh(int(i), date)]
        rng.shuffle(cands)
        cands = cands[: self.s.candidates_per_day]

        for _attempt in range(self.s.max_verify_attempts):
            best = self._best_pair(date, d, goal, cands, rng)
            if best is None:
                return None
            score, routes, start, target, dist = best
            route = shortest_route(self.g, start, dist)
            broken = None
            if self.fetch_html is not None:
                broken = first_broken_edge(
                    route, self.g.rev_ids, self.g.title_to_idx, self.fetch_html
                )
            if broken is None:
                hole = Hole(
                    date=date,
                    hole_no=hole_number(date),
                    par=par,
                    shortest=d,
                    start=start,
                    target=target,
                    difficulty=score,
                    routes=routes,
                    route=route,
                    dist=dist,
                )
                self.history.add(date, self.g.titles[start], self.g.titles[target])
                return hole
            u, v = broken
            # No titles in the log: build output is public (see render_summary).
            self.log(f"  {date}: a route link was missing from the page HTML; dropped, retrying")
            self.g.remove_edge(u, v)
            self.removed_edges.append(broken)
        return None

    def _best_pair(self, date, d, goal, cands, rng):
        g, s = self.g, self.s
        best = None
        for t in cands:
            dist = distances_to(t, g.rev_off, g.rev_tgt, g.n)
            starts = np.flatnonzero(self.start_ok & (dist == d))
            starts = [
                int(x)
                for x in starts
                if (g.titles[int(x)], g.titles[t]) not in self.history.pairs
                and self._fresh(int(x), date)
            ]
            if not starts:
                continue
            rng.shuffle(starts)
            for st in starts[: s.starts_per_target]:
                routes, hub_share = route_stats(g, st, dist, self.hubs)
                score = difficulty_score(routes, int(self.indeg[t]), hub_share, s)
                key = abs(score - goal)
                if best is None or key < best[0]:
                    best = (key, (score, routes, st, t, dist))
            if best is not None and best[0] < 0.02:
                break
        return None if best is None else best[1]
