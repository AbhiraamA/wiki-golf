from pathlib import Path

import pytest

from wikigolf_builder.dumps import LocalDumps
from wikigolf_builder.graph import build_graph

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def source() -> LocalDumps:
    return LocalDumps(FIXTURES, "simplewiki", "20261001")


@pytest.fixture
def graph(source):
    return build_graph(source, log=lambda *_: None)


def idx(g, title: str) -> int:
    return g.title_to_idx[title]
