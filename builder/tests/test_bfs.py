from conftest import idx
from wikigolf_builder.bfs import distances_to

EXPECTED = {
    0: ["Apollo_11"],
    1: ["Moon", "1969", "July_20"],
    2: ["Science_fiction", "From_the_Earth_to_the_Moon", "Earth", "Mercury_(planet,_element)"],
    3: ["Jules_Verne", "Ocean", "Stub"],
    4: ["Nautilus", "Twenty_Thousand_Leagues_Under_the_Seas", "Octopus", "Mollusca"],
    5: ["Cephalopod", "Giant_squid", "Camouflage", "List_of_cephalopods"],
    6: ["Squid"],
}


def test_distances_to_apollo(graph):
    dist = distances_to(idx(graph, "Apollo_11"), graph.rev_off, graph.rev_tgt, graph.n)
    assert dist.dtype.name == "uint8" and len(dist) == 20
    for d, titles in EXPECTED.items():
        for t in titles:
            assert dist[idx(graph, t)] == d, t


def test_no_route_is_255(graph):
    # Nothing links to Stub, so it is unreachable from everywhere else.
    dist = distances_to(idx(graph, "Stub"), graph.rev_off, graph.rev_tgt, graph.n)
    assert dist[idx(graph, "Stub")] == 0
    assert dist[idx(graph, "Moon")] == 255


def test_removed_edge_changes_distance(graph):
    graph.remove_edge(idx(graph, "Moon"), idx(graph, "Apollo_11"))
    dist = distances_to(idx(graph, "Apollo_11"), graph.rev_off, graph.rev_tgt, graph.n)
    assert dist[idx(graph, "Moon")] == 2  # Moon -> 1969 -> Apollo 11
