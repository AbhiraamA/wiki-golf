import numpy as np

from conftest import idx
from wikigolf_builder.bfs import distances_to
from wikigolf_builder.config import PickSettings
from wikigolf_builder.exclude import excluded_mask
from wikigolf_builder.pick import (
    History,
    Picker,
    _widen,
    difficulty_from_distance,
    fame_threshold,
    shortest_route,
)
from wikigolf_builder.themes import Badge, Theme
from wikigolf_builder.verify import link_titles, linked_indices

# Fame filter effectively off (top 100%) so the 20-node fixture yields holes.
OPEN = PickSettings(
    target_top_fraction=1.0,
    start_top_fraction_short=1.0,
    start_top_fraction_long=1.0,
    min_page_len=100,
    candidates_per_day=20,
    starts_per_target=20,
    max_verify_attempts=6,
    theme_par_widen=1,
)


def parsoid(links: list[str]) -> str:
    parts = [
        f'<a rel="mw:WikiLink" href="./{t}" title="{t}" id="mw{i}">{t}</a>'
        for i, t in enumerate(links)
    ]
    return "<html><body><p>" + " and ".join(parts) + "</p></body></html>"


def fake_fetch(g, missing: set[tuple[str, str]] = frozenset()):
    rev_to_idx = {int(r): i for i, r in enumerate(g.rev_ids)}
    calls = []

    def fetch(rev_id: int) -> str:
        u = rev_to_idx[rev_id]
        calls.append(g.titles[u])
        links = [
            g.titles[int(v)]
            for v in g.out_links(u)
            if (g.titles[u], g.titles[int(v)]) not in missing
        ]
        return parsoid(links)

    fetch.calls = calls
    return fetch


def picker(g, settings=OPEN, fetch=None, history=None):
    ex = excluded_mask(g.titles, g.disambig, g.page_len, settings.min_page_len, set())
    return Picker(
        g, ex, settings, history or History(used={}, pairs=set()), fetch, log=lambda *_: None
    )


def test_difficulty_comes_from_distance():
    assert difficulty_from_distance(2) == round(2 / 6, 2)
    assert difficulty_from_distance(6) == 1.0
    assert difficulty_from_distance(1) == round(1 / 6, 2)
    # Monotonic in distance, nothing to do with obscurity.
    assert difficulty_from_distance(3) < difficulty_from_distance(5)


def test_fame_threshold_selects_top_fraction():
    indeg = np.arange(100)  # 0..99
    # Top 10% -> threshold around the 90th percentile.
    assert (indeg >= fame_threshold(indeg, 0.10)).sum() <= 12
    assert (indeg >= fame_threshold(indeg, 0.10)).sum() >= 8
    assert fame_threshold(indeg, 1.0) == 0  # everything qualifies


def test_fame_filter_restricts_endpoints(graph):
    # Fame nests: target (10%) within short-start (25%) within long-start (60%) eligibility.
    p = picker(
        graph,
        PickSettings(
            target_top_fraction=0.10,
            start_top_fraction_short=0.25,
            start_top_fraction_long=0.60,
            min_page_len=100,
        ),
    )
    assert 0 < int(p.target_ok.sum()) <= int(p.start_ok_short.sum()) <= int(p.start_ok_long.sum())
    assert p.target_thresh >= p.start_thresh_short >= p.start_thresh_long
    assert bool(np.all(~p.target_ok | p.start_ok_short))
    assert bool(np.all(~p.start_ok_short | p.start_ok_long))


def test_link_titles_parses_parsoid_hrefs():
    html = (
        '<a rel="mw:WikiLink" href="./Jules_Verne#Life" title="Jules Verne">x</a>'
        '<a href="./Caf%C3%A9" rel="mw:WikiLink">y</a>'
        '<a rel="mw:WikiLink" href="./Red?action=edit&amp;redlink=1" class="new">z</a>'
        '<a rel="mw:ExtLink" href="https://example.com">e</a>'
        '<a rel="mw:WikiLink/Interwiki" href="./fr:Lune">i</a>'
    )
    assert link_titles(html) == ["Jules_Verne", "Café", "Red"]


def test_linked_indices_resolve_redirects(graph):
    got = linked_indices(parsoid(["Luna", "Octopi", "Nowhere"]), graph.title_to_idx)
    assert got == {idx(graph, "Moon"), idx(graph, "Octopus")}


def test_shortest_route_follows_links(graph):
    dist = distances_to(idx(graph, "Apollo_11"), graph.rev_off, graph.rev_tgt, graph.n)
    route = shortest_route(graph, idx(graph, "Octopus"), dist)
    assert [graph.titles[i] for i in route] == ["Octopus", "Ocean", "Earth", "Moon", "Apollo_11"]


def test_pick_gives_valid_verified_hole(graph):
    fetch = fake_fetch(graph)
    hole = picker(graph, fetch=fetch).pick("2026-12-07")  # Monday: par 3-4
    assert hole is not None
    assert 3 <= hole.par <= 4 and hole.shortest == hole.par - 1
    assert hole.dist[hole.start] == hole.shortest and hole.dist[hole.target] == 0
    assert hole.difficulty == difficulty_from_distance(hole.shortest)
    assert hole.badge is None
    assert len(hole.route) == hole.shortest + 1
    for a, b in zip(hole.route, hole.route[1:], strict=False):
        assert b in set(graph.out_links(a).tolist())
    assert fetch.calls


def test_pick_is_deterministic(graph, source):
    from wikigolf_builder.graph import build_graph

    a = picker(graph).pick("2026-12-09")
    b = picker(build_graph(source, log=lambda *_: None)).pick("2026-12-09")
    assert (a.start, a.target, a.par) == (b.start, b.target, b.par)


def test_missing_link_is_dropped_and_retried(graph):
    first = picker(graph, fetch=fake_fetch(graph)).pick("2026-12-07")
    u, v = first.route[0], first.route[1]
    p = picker(graph, fetch=fake_fetch(graph, {(graph.titles[u], graph.titles[v])}))
    hole = p.pick("2026-12-07")
    assert p.removed_edges == [(u, v)]
    assert hole is not None
    assert (u, v) not in set(zip(hole.route, hole.route[1:], strict=False))


def test_no_repeats(graph):
    p = picker(graph)
    seen_pairs, used = set(), {}
    for day in range(1, 8):
        hole = p.pick(f"2026-12-0{day}")
        if hole is None:
            continue
        assert (hole.start, hole.target) not in seen_pairs
        seen_pairs.add((hole.start, hole.target))
        for t in (hole.start, hole.target):
            assert t not in used, graph.titles[t]
            used[t] = day


def test_widen_order():
    assert _widen(3, 1) == [3, 4, 2]
    assert _widen(1, 1) == [1, 2]  # distance 0 dropped
    assert _widen(4, 2) == [4, 5, 3, 6, 2]


def theme(targets, badge=("Apollo", "🚀")):
    return Theme(
        id="t",
        when={"type": "fixed", "month": 12, "day": 7},
        targets=tuple(targets),
        badge=Badge(label=badge[0], emoji=badge[1]),
    )


def test_pick_themed_uses_chosen_target_with_badge(graph):
    # Apollo 11 is not famous enough to be a regular target here, but a theme pins it anyway.
    tight = PickSettings(
        target_top_fraction=0.03,
        start_top_fraction_short=1.0,
        start_top_fraction_long=1.0,
        min_page_len=100,
    )
    p = picker(graph, tight, fetch=fake_fetch(graph))
    assert not p.target_ok[idx(graph, "Apollo_11")]  # fame filter would exclude it
    hole = p.pick_themed("2026-12-07", theme(["Apollo 11"]))
    assert hole is not None
    assert hole.target == idx(graph, "Apollo_11")
    assert hole.badge == {"label": "Apollo", "emoji": "🚀"}
    assert hole.dist[hole.start] == hole.shortest
    assert 3 <= hole.par <= 5  # Monday par 3-4, possibly widened by one


def test_pick_themed_resolves_redirect_target(graph):
    hole = picker(graph, fetch=fake_fetch(graph)).pick_themed("2026-12-07", theme(["Luna"]))
    assert hole is not None and hole.target == idx(graph, "Moon")


def test_pick_themed_target_pool_skips_missing(graph):
    hole = picker(graph, fetch=fake_fetch(graph)).pick_themed(
        "2026-12-07", theme(["Nonexistent_page", "Apollo 11"])
    )
    assert hole is not None and hole.target == idx(graph, "Apollo_11")


def test_pick_themed_falls_back_when_target_absent(graph):
    assert picker(graph).pick_themed("2026-12-07", theme(["Nonexistent_page"])) is None
