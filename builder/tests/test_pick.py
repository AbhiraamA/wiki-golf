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

# Fame filter effectively off (top 100% by langlinks) so the 20-node fixture yields holes.
OPEN = PickSettings(
    target_langlink_fraction=1.0,
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
        g,
        ex,
        settings,
        history or History(target_dates={}, start_dates={}, pairs=set()),
        fetch,
        log=lambda *_: None,
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


def test_fame_filter_targets_by_langlinks_starts_light(graph):
    # Targets are the most inter-linked articles; starts only have to be readable (not excluded).
    p = picker(graph, PickSettings(target_langlink_fraction=0.10, min_page_len=100))
    assert p.target_ok[idx(graph, "Moon")]  # 7 interlanguage links
    assert not p.target_ok[idx(graph, "Squid")]  # only 1
    ex = excluded_mask(graph.titles, graph.disambig, graph.page_len, 100, set())
    assert bool(np.array_equal(p.start_ok, ~ex))  # the light filter is the whole bar for starts
    assert p.start_ok[idx(graph, "Squid")]  # a 1-langlink article is a perfectly good start
    assert not p.start_ok[idx(graph, "List_of_cephalopods")]  # lists excluded
    assert not p.target_ok[idx(graph, "Mercury_(planet,_element)")]  # disambiguation excluded


def test_pageview_floor_filters_targets(graph):
    # The pageview gate drops a famous-by-langlinks target that few people actually read.
    moon, earth = idx(graph, "Moon"), idx(graph, "Earth")
    views = {graph.en_title[moon]: 500_000, graph.en_title[earth]: 10}
    # Default min_target_views is 30,000.
    p = picker(graph, PickSettings(target_langlink_fraction=0.10, min_page_len=100))
    p.view_lookup = lambda title: views.get(title)
    assert p._famous_enough(moon)  # 500k views
    assert not p._famous_enough(earth)  # 10 views, below the floor
    assert p._famous_enough(idx(graph, "Ocean"))  # unknown title -> judged on langlinks alone


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
    seen_pairs, targets, starts = set(), set(), set()
    for day in range(1, 8):
        hole = p.pick(f"2026-12-0{day}")
        if hole is None:
            continue
        # The exact pair never repeats; targets never repeat (365d), starts never repeat (90d).
        assert (hole.start, hole.target) not in seen_pairs
        assert hole.target not in targets, graph.titles[hole.target]
        assert hole.start not in starts, graph.titles[hole.start]
        seen_pairs.add((hole.start, hole.target))
        targets.add(hole.target)
        starts.add(hole.start)


def test_start_window_shorter_than_target_window(graph):
    # A title used as a start 120 days ago is fresh again as a start (90d window), but a title used
    # as a target 120 days ago is still blocked as a target (365d window).
    p = picker(graph)
    p.history.add(
        "2026-08-09", graph.titles[idx(graph, "Octopus")], graph.titles[idx(graph, "Moon")]
    )
    assert p._fresh_start(idx(graph, "Octopus"), "2026-12-07")  # 120d > 90d start window
    assert not p._fresh_target(idx(graph, "Moon"), "2026-12-07")  # 120d < 365d target window


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
    tight = PickSettings(target_langlink_fraction=0.03, min_page_len=100)
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


def test_pick_skips_a_sensitive_target(graph):
    # Whatever target a normal pick lands on, flagging it sensitive makes the picker choose another.
    baseline = picker(graph, fetch=fake_fetch(graph)).pick("2026-12-07")
    assert baseline is not None
    banned = baseline.target
    p = picker(graph, fetch=fake_fetch(graph))
    p.sensitive = lambda i: "drug" if i == banned else None
    hole = p.pick("2026-12-07")
    assert hole is not None
    assert hole.target != banned
    assert p.sensitive_dropped >= 1


def test_pick_themed_ignores_sensitivity(graph):
    # A themed target is the owner's own choice, so the sensitive-topic filter must not drop it.
    p = picker(graph, fetch=fake_fetch(graph))
    p.sensitive = lambda i: "flagged"  # pretend everything is sensitive
    hole = p.pick_themed("2026-12-07", theme(["Apollo 11"]))
    assert hole is not None and hole.target == idx(graph, "Apollo_11")
    assert p.sensitive_dropped == 0
