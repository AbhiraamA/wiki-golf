import datetime as dt

import pytest

from wikigolf_builder.themes import (
    Badge,
    easter_sunday,
    load_themes,
    nth_weekday,
    theme_for,
)


def test_easter_sunday_known_years():
    assert easter_sunday(2024) == dt.date(2024, 3, 31)
    assert easter_sunday(2025) == dt.date(2025, 4, 20)
    assert easter_sunday(2026) == dt.date(2026, 4, 5)


def test_nth_weekday():
    # US Thanksgiving: 4th Thursday of November.
    assert nth_weekday(2026, 11, 3, 4) == dt.date(2026, 11, 26)
    # Memorial Day: last Monday of May.
    assert nth_weekday(2026, 5, 0, -1) == dt.date(2026, 5, 25)
    # MLK Day 2027: 3rd Monday of January.
    assert nth_weekday(2027, 1, 0, 3) == dt.date(2027, 1, 18)


def test_load_and_match_fixed():
    themes = load_themes(
        {
            "themes": [
                {
                    "id": "xmas",
                    "when": {"type": "fixed", "month": 12, "day": 25},
                    "targets": ["Christmas"],
                    "badge": {"label": "Christmas", "emoji": "🎄"},
                }
            ]
        }
    )
    assert theme_for("2026-12-25", themes).id == "xmas"
    assert theme_for("2026-12-24", themes) is None


def test_match_nth_weekday_and_easter():
    themes = load_themes(
        {
            "themes": [
                {
                    "id": "thanks",
                    "when": {"type": "nth_weekday", "month": 11, "weekday": "Thursday", "n": 4},
                    "targets": ["Thanksgiving"],
                },
                {"id": "easter", "when": {"type": "easter"}, "targets": ["Easter"]},
            ]
        }
    )
    assert theme_for("2026-11-26", themes).id == "thanks"
    assert theme_for("2026-04-05", themes).id == "easter"
    assert theme_for("2026-04-04", themes) is None


def test_single_target_and_badge_optional():
    themes = load_themes(
        {
            "themes": [
                {"id": "x", "when": {"type": "fixed", "month": 1, "day": 1}, "target": "New Year"}
            ]
        }
    )
    assert themes[0].targets == ("New Year",) and themes[0].badge is None


def test_empty_and_invalid():
    assert load_themes(None) == []
    assert load_themes({}) == []
    with pytest.raises(ValueError):
        load_themes({"themes": [{"id": "bad", "when": {"type": "nope"}, "targets": ["X"]}]})
    with pytest.raises(ValueError):
        load_themes(
            {"themes": [{"id": "notarget", "when": {"type": "fixed", "month": 1, "day": 1}}]}
        )


def test_badge_to_json():
    assert Badge("Pi Day", "🥧").to_json() == {"label": "Pi Day", "emoji": "🥧"}
