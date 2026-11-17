"""`show` and `approve` against an in-memory fake R2, and the no-spoiler guarantee."""

import json

import pytest

import wikigolf_builder.upload as upload_mod
from conftest import FIXTURES
from wikigolf_builder.cli import main


class FakeR2:
    """Same surface as upload.R2, backed by a dict. No network."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)
        self.puts = 0

    def exists(self, key: str) -> bool:
        return key in self.objects

    def get_json(self, key: str):
        return json.loads(self.objects[key]) if key in self.objects else None

    def put_json(self, key: str, data) -> None:
        self.objects[key] = json.dumps(data).encode()
        self.puts += 1

    def put_file(self, key: str, path) -> None:
        self.objects[key] = __import__("pathlib").Path(path).read_bytes()
        self.puts += 1


def seed(records: list[dict]) -> dict[str, bytes]:
    index = {"holes": []}
    objs: dict[str, bytes] = {}
    for r in records:
        objs[f"holes/{r['date']}.json"] = json.dumps(r).encode()
        index["holes"].append(
            {
                "date": r["date"],
                "holeNo": r["holeNo"],
                "status": r["status"],
                "snap": r["snap"],
                "par": r["par"],
                "start": r["start"]["title"],
                "target": r["target"]["title"],
            }
        )
    objs["holes/index.json"] = json.dumps(index).encode()
    return objs


def record(date, status="queued"):
    return {
        "holeNo": 1,
        "date": date,
        "snap": "simplewiki-20261001",
        "wiki": "simplewiki",
        "par": 4,
        "pickUp": 8,
        "shortest": 3,
        "start": {"idx": 0, "title": "Octopus", "revId": 5001},
        "target": {"idx": 11, "title": "Apollo_11", "revId": 5012},
        "difficulty": 0.42,
        "status": status,
    }


@pytest.fixture
def fake(monkeypatch):
    store = FakeR2(seed([record("2026-12-07"), record("2026-12-08", "approved")]))
    monkeypatch.setattr(upload_mod, "R2", lambda *a, **k: store)
    return store


def test_show_prints_titles_and_links(fake, capsys):
    assert main(["show", "--status", "queued"]) == 0
    out = capsys.readouterr().out
    assert "2026-12-07" in out and "Apollo 11" in out and "Octopus" in out
    assert "oldid=5012" in out  # pinned-revision link for the owner
    assert "2026-12-08" not in out  # filtered out by --status queued


def test_approve_flips_status(fake):
    assert main(["approve", "--dates", "2026-12-07"]) == 0
    assert json.loads(fake.objects["holes/2026-12-07.json"])["status"] == "approved"
    index = json.loads(fake.objects["holes/index.json"])
    assert {e["date"]: e["status"] for e in index["holes"]}["2026-12-07"] == "approved"


def test_approve_dry_run_changes_nothing(fake):
    before = dict(fake.objects)
    assert main(["approve", "--through", "2026-12-31", "--dry-run"]) == 0
    assert fake.objects == before


def test_summary_never_contains_titles():
    """The public job summary must not leak article titles or routes."""
    import numpy as np

    from wikigolf_builder.cli import render_summary
    from wikigolf_builder.dumps import LocalDumps
    from wikigolf_builder.graph import build_graph
    from wikigolf_builder.pick import Hole

    g = build_graph(LocalDumps(FIXTURES, "simplewiki", "20261001"), log=lambda *_: None)
    oct_i, apollo_i = g.title_to_idx["Octopus"], g.title_to_idx["Apollo_11"]
    hole = Hole(
        date="2026-12-07",
        hole_no=7,
        par=4,
        shortest=3,
        start=oct_i,
        target=apollo_i,
        difficulty=0.4,
        routes=2,
        route=[oct_i, apollo_i],
        dist=np.zeros(g.n, np.uint8),
    )
    text = render_summary(g, [hole], [], [], verified=True, timings={}, uploaded="no")
    for title in g.titles:
        pretty = title.replace("_", " ")
        assert pretty not in text, f"summary leaked a title: {pretty}"
