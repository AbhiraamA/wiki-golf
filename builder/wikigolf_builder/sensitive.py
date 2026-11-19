"""Sensitive-topic classification for hole *targets*.

A target is the destination a player is told to reach and is shown by name on the tee, so it must
not be a distressing or unsavoury topic even when it is famous and well-connected. Fame signals
(interlanguage links, pageviews) happily rank murderers, hard drugs and conspiracy theories highly,
so this filter removes them. Three signals combine (plan.md 5.4, owner decision 2026-11-18):

1. **Wikidata claims** - the item's `instance of` (P31), `subclass of` (P279) and `occupation`
   (P106) values, checked against `SENSITIVE_QIDS`. Catches well-modelled cases: Charles Manson is
   occupation=criminal/serial killer, Cocaine subclass-of drug, the Illuminati a secret society.
2. **Description text** - the local short description or the Wikidata description, matched against
   `DESC_PATTERNS`. Catches topics Wikidata models poorly (e.g. "...stimulant drug").
3. **The blocklist** (exclude.py) - the reliable backstop for named articles whose Wikidata item is
   unhelpful. Methamphetamine's item is merely "group of stereoisomers" with no drug claim, so hard
   drugs are also listed by name in blocklist.txt.

This module holds the pure, offline-testable part (signals 1 and 2); enrich.make_sensitivity wires
in the network fetch, and the blocklist is applied in exclude.py.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Wikidata item ids that make their subject a sensitive *topic* when they appear as `instance of`
# (P31), `subclass of` (P279) or `occupation` (P106). Every id here was confirmed against the live
# Wikidata API; extend during review. Value is the human reason, used for local review only.
SENSITIVE_QIDS: dict[str, str] = {
    # Murderers and criminals (usually P106 occupation, sometimes P31).
    "Q484188": "serial killer",
    "Q931260": "murderer",
    "Q15883433": "mass murderer",
    "Q2159907": "criminal",
    "Q22962951": "rapist",
    "Q11075015": "war criminal",
    "Q20956402": "cult leader",
    # Drugs.
    "Q8386": "drug",
    "Q3706669": "psychoactive drug",
    # Conspiracy theories and secret societies.
    "Q159535": "conspiracy theory",
    "Q276548": "secret society",
    # Terrorism / organised crime.
    "Q17127659": "terrorist organisation",
    "Q1260006": "drug cartel",
}

# Wikidata claim properties whose values we test against SENSITIVE_QIDS.
CLAIM_PROPS = ("P31", "P279", "P106")

# Description-text signals, each (compiled pattern, reason). Matched case-insensitively against the
# short description. Phrases are chosen to avoid obvious false positives: "stimulant drug" rather
# than bare "stimulant" (caffeine is a stimulant), "secret society" rather than "society".
_DESC_RULES: list[tuple[str, str]] = [
    (
        r"serial killer|mass murderer|\bmurderer\b|\bassassin\b|war criminal|\bgangster\b"
        r"|\bmobster\b|crime boss|drug lord|drug trafficker|drug kingpin|\brapist\b|sex offender",
        "murderer or criminal",
    ),
    (
        r"\bdrug\b|psychoactive|narcotic|\bopioid\b|\bopiate\b|hallucinogen|psychedelic"
        r"|\bmethamphetamine\b|\bamphetamine\b|\bcocaine\b|\bheroin\b|\bcannabis\b|marijuana"
        r"|barbiturate|\becstasy\b|\bMDMA\b",
        "drug",
    ),
    (r"conspiracy theor|secret society|\bcult\b", "conspiracy theory or secret society"),
    (r"terroris|jihadist|extremist (group|organi)", "terrorism"),
    (
        r"pornograph|\berotic|\bfetish\b|masturbat|sexual (intercourse|act|practice|position)"
        r"|sex position|\bprostitut",
        "sexual topic",
    ),
]
DESC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), reason) for p, reason in _DESC_RULES
]


def sensitive_by_claims(claim_qids: Iterable[str]) -> str | None:
    """Reason if any Wikidata claim value marks a sensitive topic, else None."""
    for qid in claim_qids:
        reason = SENSITIVE_QIDS.get(qid)
        if reason:
            return reason
    return None


def sensitive_by_description(desc: str) -> str | None:
    """Reason if the short description reads as a sensitive topic, else None."""
    if not desc:
        return None
    for pattern, reason in DESC_PATTERNS:
        if pattern.search(desc):
            return reason
    return None


def sensitive_reason(desc: str, claim_qids: Iterable[str] = ()) -> str | None:
    """Combined check: Wikidata claims first (most precise), then description text."""
    return sensitive_by_claims(claim_qids) or sensitive_by_description(desc)
