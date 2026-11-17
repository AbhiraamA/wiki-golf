import numpy as np

from conftest import idx
from wikigolf_builder.bfs import distances_to
from wikigolf_builder.config import PickSettings
from wikigolf_builder.exclude import excluded_mask
from wikigolf_builder.pick import History, Picker, route_stats, shortest_route
from wikigolf_builder.verify import link_titles, linked_indices

SMALL = PickSettings(
    target_min_in=1,
    target_max_in=100,
    start_min_in=1,
    min_page_len=100,
    hub_count=3,
    candidates_per_day=20,
    starts_per_target=20,
    repeat_window_days=365,
    max_verify_attempts=6,
)


def parsoid(links: list[str]) -> str:
    """Minimal Parsoid-like HTML linking to `links`."""
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


def picker(g, fetch=None, history=None):
    ex = excluded_mask(g.titles, g.disambig, g.page_len, SMALL.min_page_len, set())
    return Picker(
        g, ex, SMALL, history or History(used={}, pairs=set()), fetch, log=lambda *_: None
    )


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


def test_route_stats_counts_shortest_routes(graph):
    dist = distances_to(idx(graph, "Apollo_11"), graph.rev_off, graph.rev_tgt, graph.n)
    hubs = np.zeros(graph.n, dtype=bool)
    routes, hub_share = route_stats(graph, idx(graph, "Octopus"), dist, hubs)
    # Octopus -> Ocean -> Earth -> Moon -> Apollo 11 is the only 4-click route.
    assert routes == 1 and hub_share == 0
    routes, _ = route_stats(graph, idx(graph, "Jules_Verne"), dist, hubs)
    assert routes == 2  # via Science fiction or From the Earth to the Moon, then Moon
    route = shortest_route(graph, idx(graph, "Octopus"), dist)
    assert [graph.titles[i] for i in route] == ["Octopus", "Ocean", "Earth", "Moon", "Apollo_11"]


def test_pick_gives_valid_verified_hole(graph):
    fetch = fake_fetch(graph)
    p = picker(graph, fetch)
    hole = p.pick("2026-12-07")  # Monday: par 3-4
    assert hole is not None
    assert 3 <= hole.par <= 4 and hole.shortest == hole.par - 1
    assert hole.dist[hole.start] == hole.shortest and hole.dist[hole.target] == 0
    assert hole.route[0] == hole.start and hole.route[-1] == hole.target
    assert len(hole.route) == hole.shortest + 1
    for a, b in zip(hole.route, hole.route[1:], strict=False):
        assert b in set(graph.out_links(a).tolist())
    assert graph.titles[hole.start] not in {"List_of_cephalopods", "1969", "July_20", "Stub"}
    assert fetch.calls  # the route was checked against HTML


def test_pick_is_deterministic(graph, source):
    from wikigolf_builder.graph import build_graph

    a = picker(graph).pick("2026-12-09")
    b = picker(build_graph(source, log=lambda *_: None)).pick("2026-12-09")
    assert (a.start, a.target, a.par) == (b.start, b.target, b.par)


def test_missing_link_in_html_is_dropped_and_search_retries(graph):
    first = picker(graph, fake_fetch(graph)).pick("2026-12-07")
    u, v = first.route[0], first.route[1]
    broken = {(graph.titles[u], graph.titles[v])}
    p = picker(graph, fake_fetch(graph, broken))
    hole = p.pick("2026-12-07")
    assert p.removed_edges == [(u, v)]
    assert hole is not None
    assert (u, v) not in set(zip(hole.route, hole.route[1:], strict=False))


def test_no_repeats(graph):
    p = picker(graph)
    seen_pairs = set()
    titles_by_date = {}
    for day in range(1, 8):
        hole = p.pick(f"2026-12-0{day}")
        if hole is None:
            continue
        pair = (hole.start, hole.target)
        assert pair not in seen_pairs
        seen_pairs.add(pair)
        for t in (hole.start, hole.target):
            assert t not in titles_by_date, graph.titles[t]
            titles_by_date[t] = day


def test_history_blocks_recent_titles():
    h = History.from_index([{"date": "2026-01-01", "start": "A", "target": "B"}])
    assert h.recent("A", "2026-12-31", 365)
    assert not h.recent("A", "2027-01-01", 365)
    assert ("A", "B") in h.pairs
