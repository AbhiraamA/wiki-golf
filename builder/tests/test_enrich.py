import datetime as dt

from conftest import idx
from wikigolf_builder.enrich import latest_complete_month, make_describe, make_view_lookup


def test_latest_complete_month():
    assert latest_complete_month(dt.date(2026, 11, 18)) == ("20261001", "20261031")
    assert latest_complete_month(dt.date(2026, 1, 1)) == ("20251201", "20251231")  # year rollover
    assert latest_complete_month(dt.date(2026, 3, 31)) == ("20260201", "20260228")


def test_describe_prefers_local_shortdesc_without_network(graph):
    describe = make_describe(graph, session=None, lang="simple")
    assert describe(idx(graph, "Octopus")) == "Eight-limbed sea mollusc"
    # No local short description and no session: nothing to fall back to, so empty.
    assert describe(idx(graph, "Moon")) == ""


def test_view_lookup_parses_and_caches(graph, monkeypatch):
    import wikigolf_builder.enrich as enrich

    calls = []

    class FakeResp:
        def json(self):
            return {"items": [{"views": 1200}, {"views": 300}]}

    def fake_get(session, url, **kw):
        calls.append(url)
        return FakeResp()

    monkeypatch.setattr(enrich.net, "get", fake_get)
    lookup = make_view_lookup(session=None, today=dt.date(2026, 11, 18))
    assert lookup("Moon") == 1500  # summed across access methods
    assert lookup("Moon") == 1500  # cached: no second request
    assert len(calls) == 1
    assert "/en.wikipedia.org/" in calls[0] and "/monthly/20261001/20261031" in calls[0]
