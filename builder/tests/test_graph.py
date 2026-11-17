import numpy as np

from conftest import idx
from wikigolf_builder.graph import Graph


def edges(g: Graph) -> set[tuple[str, str]]:
    out = set()
    for u in range(g.n):
        for v in g.out_links(u):
            out.add((g.titles[u], g.titles[int(v)]))
    return out


def test_articles_only_namespace_zero_non_redirects(graph):
    assert graph.n == 20
    assert graph.titles[0] == "Octopus"  # ordered by page_id
    assert "Octopus" in graph.titles and graph.titles.count("Octopus") == 1  # talk page dropped
    assert "Octopi" not in graph.titles
    assert int(graph.rev_ids[idx(graph, "Moon")]) == 5011


def test_redirects_fold_into_targets(graph):
    t = graph.title_to_idx
    assert t["Octopi"] == t["Octopus"]
    assert t["Luna"] == t["Moon"]
    assert t["Verne's_Moon"] == t["Jules_Verne"]
    assert t["Cephalopoda"] == t["Cephalopod"]  # 1 hop
    assert t["Cephalopods"] == t["Cephalopod"]  # 2 hops
    assert "Triple_redirect" not in t  # 3 hops: dropped
    assert len(t) - graph.n == 6


def test_links(graph):
    e = edges(graph)
    assert graph.link_count == 53 == len(e)
    assert ("Octopus", "Cephalopod") in e  # via a 2-hop redirect
    assert ("Cephalopod", "Octopus") in e  # via a redirect
    assert ("Nautilus", "Jules_Verne") in e  # redirect title with an escaped quote
    assert ("Jules_Verne", "Jules_Verne") not in e  # self-link dropped
    assert ("Squid", "Cephalopod") in e
    assert ("From_the_Earth_to_the_Moon", "Moon") in e  # direct + via redirect: one edge


def test_csr_forward_and_reverse_agree(graph):
    fwd = {(u, int(v)) for u in range(graph.n) for v in graph.out_links(u)}
    rev = set()
    for v in range(graph.n):
        for u in graph.rev_tgt[graph.rev_off[v] : graph.rev_off[v + 1]]:
            rev.add((int(u), v))
    assert fwd == rev
    assert graph.fwd_off[-1] == graph.rev_off[-1] == 53
    assert np.all(np.diff(graph.fwd_off) >= 0)
    assert graph.in_degree()[idx(graph, "Moon")] == 6


def test_disambiguation_from_page_props(graph):
    assert graph.disambig[idx(graph, "Mercury_(planet,_element)")]
    assert int(graph.disambig.sum()) == 1


def test_remove_edge(graph):
    u, v = idx(graph, "Moon"), idx(graph, "Apollo_11")
    graph.remove_edge(u, v)
    assert v not in set(graph.out_links(u).tolist())
    assert u not in set(graph.rev_tgt[graph.rev_off[v] : graph.rev_off[v + 1]].tolist())
