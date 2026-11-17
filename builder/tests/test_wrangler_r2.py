"""WranglerR2 builds the right CLI calls and parses output. subprocess is faked (no network)."""

import json
import subprocess
from types import SimpleNamespace

import pytest

import wikigolf_builder.wrangler_r2 as wr


@pytest.fixture
def no_path_wrangler(monkeypatch):
    # Pretend `wrangler` is not on PATH, so the npx form is used.
    monkeypatch.setattr(wr.shutil, "which", lambda _: None)


def test_get_json_builds_remote_pipe_call(monkeypatch, no_path_wrangler):
    seen = {}

    def fake_run(args, cwd, input, capture_output, check):
        seen["args"] = args
        return SimpleNamespace(returncode=0, stdout=b'{"holes": [1]}', stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    r2 = wr.WranglerR2()
    assert r2.get_json("simplewiki/holes/index.json") == {"holes": [1]}
    assert seen["args"] == [
        "npx",
        "--yes",
        "wrangler",
        "r2",
        "object",
        "get",
        "wiki-golf/simplewiki/holes/index.json",
        "--pipe",
        "--remote",
    ]


def test_get_json_missing_returns_none(monkeypatch, no_path_wrangler):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"The object does not exist"
        ),
    )
    assert wr.WranglerR2().get_json("simplewiki/holes/x.json") is None


def test_get_json_other_error_raises(monkeypatch, no_path_wrangler):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout=b"", stderr=b"Authentication error"),
    )
    with pytest.raises(RuntimeError):
        wr.WranglerR2().get_json("simplewiki/holes/x.json")


def test_put_json_writes_temp_file_and_calls_put(monkeypatch, no_path_wrangler):
    captured = {}

    def fake_run(args, cwd, input, capture_output, check):
        # The --file argument points at a temp file holding the JSON body.
        i = args.index("--file")
        captured["args"] = args
        with open(args[i + 1], "rb") as fh:
            captured["body"] = json.loads(fh.read())
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    r2 = wr.WranglerR2()
    r2.put_json("simplewiki/holes/index.json", {"holes": ["a"]})
    assert captured["body"] == {"holes": ["a"]}
    assert captured["args"][:7] == [
        "npx",
        "--yes",
        "wrangler",
        "r2",
        "object",
        "put",
        "wiki-golf/simplewiki/holes/index.json",
    ]
    assert "--remote" in captured["args"] and r2.puts == 1
