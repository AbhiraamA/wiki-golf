import json

import numpy as np

from conftest import FIXTURES
from wikigolf_builder.cli import main
from wikigolf_builder.fnv import title_shard

PICK = [
    "target_min_in=1",
    "target_max_in=100",
    "start_min_in=1",
    "min_page_len=100",
    "hub_count=3",
    "candidates_per_day=20",
    "starts_per_target=20",
]


def run(tmp_path, *extra):
    args = [
        "build",
        "--wiki",
        "simplewiki",
        "--dumps-dir",
        str(FIXTURES),
        "--dump-date",
        "20261001",
    ]
    args += ["--out", str(tmp_path), "--no-verify", "--start", "2026-12-07", *extra]
    for p in PICK:
        args += ["--pick", p]
    return main(args)


def test_build_writes_r2_layout(tmp_path):
    assert run(tmp_path, "--days", "2") == 0
    snap = tmp_path / "snapshots" / "simplewiki-20261001"
    meta = json.loads((snap / "meta.json").read_text())
    assert meta["articleCount"] == 20 and meta["linkCount"] == 53 and meta["shardCount"] == 64

    shard = json.loads((snap / "titles" / f"{title_shard('Luna', 64)}.json").read_text())
    moon = json.loads((snap / "titles" / f"{title_shard('Moon', 64)}.json").read_text())
    assert shard["Luna"] == moon["Moon"]
    pages = json.loads((snap / "pages" / "0.json").read_text())
    assert pages[0] == ["Octopus", 5001] and len(pages) == 20

    hole = json.loads((tmp_path / "holes" / "2026-12-07.json").read_text())
    assert hole["status"] == "queued" and hole["snap"] == "simplewiki-20261001"
    assert hole["pickUp"] == hole["par"] * 2 and hole["shortest"] == hole["par"] - 1
    assert set(hole["start"]) == {"idx", "title", "revId"}
    dist = np.frombuffer((tmp_path / "distances" / "2026-12-07.bin").read_bytes(), dtype=np.uint8)
    assert len(dist) == 20 and dist[hole["target"]["idx"]] == 0
    assert dist[hole["start"]["idx"]] == hole["shortest"]

    index = json.loads((tmp_path / "holes" / "index.json").read_text())
    assert [e["date"] for e in index["holes"]] == ["2026-12-07", "2026-12-08"]


def test_existing_dates_are_skipped(tmp_path):
    index = tmp_path / "existing.json"
    index.write_text(
        json.dumps(
            {
                "holes": [
                    {
                        "date": "2026-12-07",
                        "holeNo": 7,
                        "status": "approved",
                        "snap": "x",
                        "par": 4,
                        "start": "A",
                        "target": "B",
                    }
                ]
            }
        )
    )
    assert run(tmp_path, "--days", "2", "--index", str(index)) == 0
    assert not (tmp_path / "holes" / "2026-12-07.json").exists()
    out = json.loads((tmp_path / "holes" / "index.json").read_text())
    assert [(e["date"], e["status"]) for e in out["holes"]] == [
        ("2026-12-07", "approved"),
        ("2026-12-08", "queued"),
    ]
