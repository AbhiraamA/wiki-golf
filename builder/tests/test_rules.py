import datetime as dt
import json

import numpy as np

from wikigolf_builder.config import PAR_RANGES, SHARED_CONFIG_PATH
from wikigolf_builder.exclude import excluded_mask, title_excluded
from wikigolf_builder.fnv import fnv1a32, title_shard
from wikigolf_builder.pick import hole_number, par_for


def test_par_follows_schedule_and_is_deterministic():
    d0 = dt.date(2026, 11, 30)  # a Monday
    for i in range(70):
        date = (d0 + dt.timedelta(days=i)).isoformat()
        lo, hi = PAR_RANGES[(d0 + dt.timedelta(days=i)).weekday()]
        assert lo <= par_for(date) <= hi
        assert par_for(date) == par_for(date)
    assert {par_for((d0 + dt.timedelta(days=7 * w + 6)).isoformat()) for w in range(10)} <= {6, 7}


def test_hole_number():
    assert hole_number("2026-12-01", "2026-12-01") == 1
    assert hole_number("2026-12-31", "2026-12-01") == 31


def test_title_exclusions():
    for t in [
        "List_of_cephalopods",
        "Lists_of_animals",
        "1999",
        "44_BC",
        "1990s",
        "March_3",
        "March",
        "3_March",
        "21st_century",
        "Mercury_(disambiguation)",
        "Germany_at_the_2008_Summer_Olympics",
        "Athletics_at_the_2012_Summer_Paralympics",
        "ISO_4217",
        "ISO/IEC_27001",
        "Wikiquote",
        "Wikimedia_Foundation",
        "MediaWiki",
        # "X in Y" / "topic of place" index pages and single works (CONTENT_GUIDE Tier C).
        "1999_in_film",
        "2020_in_science",
        "Sport_in_Brazil",
        "Economy_of_France",
        "Pilot_(Lost_episode)",
    ]:
        assert title_excluded(t, set()), t
    for t in [
        "Octopus",
        "Apollo_11",
        "Marching_band",
        "Mayor",
        "Isolation",
        "WikiLeaks",  # not a Wikimedia project
        "Fin_whale",  # a plain topic, not "X in/of Y"
    ]:
        assert not title_excluded(t, set()), t
    assert title_excluded("Some_Topic", {"some_topic"})


def test_excluded_mask():
    titles = ["Octopus", "1969", "Short", "Disambig"]
    mask = excluded_mask(
        titles,
        disambig=np.array([False, False, False, True]),
        page_len=np.array([5000, 5000, 10, 5000]),
        min_page_len=100,
        blocklist=set(),
    )
    assert mask.tolist() == [False, True, True, True]


def test_fnv_shared_vectors():
    path = SHARED_CONFIG_PATH.parent / "test-vectors" / "fnv1a.json"
    for v in json.loads(path.read_text(encoding="utf-8"))["vectors"]:
        assert fnv1a32(v["input"]) == v["fnv1a32"], v["input"]
        assert title_shard(v["input"], 64) == v["shard64"]
        assert title_shard(v["input"], 1024) == v["shard1024"]
