"""The sensitive-topic classifier (pure part). Cases mirror the real Wikidata data for the
examples the owner flagged: Charles Manson, Methamphetamine and the Illuminati."""

from wikigolf_builder.sensitive import (
    sensitive_by_claims,
    sensitive_by_description,
    sensitive_reason,
)


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
