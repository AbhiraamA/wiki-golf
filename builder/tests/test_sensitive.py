"""The content-policy classifier (pure part). Cases mirror the real Wikidata data for the examples
the owner flagged: Charles Manson, Methamphetamine, the Illuminati, Che Guevara, Tony Blair,
Abkhazia (see CONTENT_GUIDE.md)."""

import datetime as dt

from wikigolf_builder.sensitive import (
    died_recently,
    is_modern_politician,
    sensitive_by_claims,
    sensitive_by_description,
    sensitive_reason,
    start_policy_reason,
    target_policy_reason,
)

TODAY = dt.date(2026, 11, 19)
POLITICIAN = "Q82955"


def _target(**kw):
    base = dict(
        desc="",
        instance_classes=[],
        occupations=[],
        positions_held=[],
        convicted_of=[],
        death_iso=None,
        today=TODAY,
    )
    base.update(kw)
    return target_policy_reason(**base)


def _start(**kw):
    base = dict(
        desc="", instance_classes=[], occupations=[], convicted_of=[], death_iso=None, today=TODAY
    )
    base.update(kw)
    return start_policy_reason(**base)


def test_claims_flag_murderers_drugs_and_conspiracies():
    assert sensitive_by_claims(["Q484188"]) == "serial killer"
    assert sensitive_by_claims(["Q2159907"]) == "criminal"  # Charles Manson's occupation
    assert sensitive_by_claims(["Q8386"]) == "drug"
    assert sensitive_by_claims(["Q276548"]) == "secret society"  # the Illuminati's P31
    assert sensitive_by_claims(["Q17127659"]) == "terrorist organisation"
    # Mixed claims: a sensitive one anywhere in the list is enough.
    assert sensitive_by_claims(["Q5", "Q639669", "Q484188"]) == "serial killer"


def test_claims_pass_ordinary_topics():
    assert sensitive_by_claims(["Q5"]) is None  # human
    assert sensitive_by_claims(["Q515", "Q6256"]) is None  # city, country
    assert sensitive_by_claims([]) is None


def test_description_catches_what_claims_miss():
    # Charles Manson's Wikidata description.
    assert sensitive_by_description("American criminal and cult leader (1934–2017)") is not None
    # Cocaine: Wikidata gives no drug *claim*, but the description says so.
    assert sensitive_by_description("tropane alkaloid and stimulant drug") == "drug"
    # The Illuminati's description.
    assert sensitive_by_description("Enlightenment-era secret society founded in 1776") is not None


def test_description_avoids_common_false_positives():
    assert sensitive_by_description("natural satellite of Earth") is None
    assert sensitive_by_description("chemical element with symbol Na") is None
    assert sensitive_by_description("central nervous system stimulant") is None  # bare "stimulant"
    assert sensitive_by_description("learned society for mathematicians") is None  # not "secret"
    assert sensitive_by_description("") is None


def test_methamphetamine_is_not_caught_automatically():
    # Its real Wikidata item is just "group of stereoisomers" with an N-methylamphetamines subclass
    # and no drug claim, so neither signal fires. This is why hard drugs are in the blocklist.
    assert sensitive_reason("group of stereoisomers", ["Q59199015", "Q113813289"]) is None


def test_combined_prefers_a_claim_then_falls_back_to_text():
    assert sensitive_reason("", ["Q931260"]) == "murderer"
    assert sensitive_reason("a notorious drug lord", []) == "murderer or criminal"


# ── New content-guide rules ──────────────────────────────────────────────────────────────────────


def test_modern_politician_blocked_as_target_but_fine_as_start():
    # Che Guevara: politician, died 1967. Tony Blair: politician, living. Both modern.
    che = dict(occupations=[POLITICIAN, "Q49757"], death_iso="+1967-10-09T00:00:00Z")
    blair = dict(occupations=[POLITICIAN], positions_held=["Q14211"])
    assert "politician" in _target(**che)
    assert "politician" in _target(**blair)
    # P39 (held office) alone is enough even without the politician occupation.
    assert "politician" in _target(positions_held=["Q14211"])
    # Fine as a start - you just begin there.
    assert _start(occupations=[POLITICIAN], death_iso="+1967-10-09T00:00:00Z") is None


def test_settled_historical_politician_allowed():
    # Disraeli (d. 1881), Napoleon (d. 1821), Vespasian (d. AD 79) are settled history.
    assert _target(occupations=[POLITICIAN], death_iso="+1881-04-19T00:00:00Z") is None
    assert _target(occupations=[POLITICIAN], death_iso="+0079-06-23T00:00:00Z") is None
    assert is_modern_politician([POLITICIAN], [], "+1949-12-31T00:00:00Z") is False
    assert is_modern_politician([POLITICIAN], [], "+1950-01-01T00:00:00Z") is True


def test_convicted_of_any_crime_blocks_both_roles():
    assert _target(convicted_of=["Q123"]) == "convicted of a crime (P1399)"
    assert _start(convicted_of=["Q123"]) == "convicted of a crime (P1399)"


def test_disputed_territory_blocks_target_only():
    # Abkhazia: P31 disputed territory / occupied territory.
    assert _target(instance_classes=["Q15239622"]) == "disputed territory"
    assert _target(instance_classes=["Q2577883"]) == "occupied territory"
    assert _target(instance_classes=["Q10711424"]) == "state with limited recognition"
    # Fine to start on.
    assert _start(instance_classes=["Q15239622"]) is None


def test_hate_group_and_genocide_classes_block_both_roles():
    assert _target(instance_classes=["Q3233801"]) == "hate group"
    assert _start(instance_classes=["Q41397"]) == "genocide"


def test_recent_death_rule_twelve_months():
    recent = "+2026-09-01T00:00:00Z"  # ~11 weeks before TODAY
    old = "+2023-07-26T00:00:00Z"  # Sinéad O'Connor; years ago
    assert died_recently(recent, TODAY) is True
    assert died_recently(old, TODAY) is False
    assert _target(death_iso=recent) == "died within the last 12 months"
    assert _start(death_iso=recent) == "died within the last 12 months"
    assert _target(death_iso=old) is None
    # A year-only date (unknown month/day) is not treated as recent.
    assert died_recently("+2026-00-00T00:00:00Z", TODAY) is False


def test_murderer_and_drug_block_both_roles():
    assert _start(occupations=["Q2159907"]) == "criminal"
    assert _start(desc="tropane alkaloid and stimulant drug") == "drug"
