"""Content policy for hole *endpoints* (starts and targets). See builder/CONTENT_GUIDE.md.

Fame signals happily rank murderers, hard drugs, conspiracy theories, modern politicians and
disputed territories highly, so the picker needs an explicit policy for what may be a start or a
target. This module holds the pure, offline-testable part; enrich.make_sensitivity wires in the
Wikidata fetch, and exclude.py applies the blocklist and title patterns.

The guide's tiers map to two role-aware checks here:

* `target_policy_reason` - everything a *target* (the day's shared headline) must not be: Tier A
  (never), the target half of Tier B (fine to start on, not to reach: modern politicians, disputed
  territories, …) and Tier C unaimable classes that Wikidata exposes.
* `start_policy_reason` - the Tier A subset a *start* must not be either (violence, abuse, drugs,
  sexual content, hate, a death in the last 12 months). Politicians and disputed territories are
  fine to begin on, so they are not here.

Both take already-extracted Wikidata fields (QID lists + the P570 death date) plus the short
description, so the network code stays in enrich.py and these stay unit-testable.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable

# ── Wikidata classes (instance-of P31 / subclass-of P279 / occupation P106) ──────────────────────
# Every id was confirmed against the live Wikidata API. Value is the human reason (local review
# only). Grouped by the content-guide tier they enforce.
SENSITIVE_QIDS: dict[str, str] = {
    # Tier A - murderers and criminals (usually P106 occupation).
    "Q484188": "serial killer",
    "Q931260": "murderer",
    "Q15883433": "mass murderer",
    "Q2159907": "criminal",
    "Q22962951": "rapist",
    "Q11075015": "war criminal",
    "Q20956402": "cult leader",
    # Tier A - drugs.
    "Q8386": "drug",
    "Q3706669": "psychoactive drug",
    # Tier A - conspiracy theories and secret societies.
    "Q159535": "conspiracy theory",
    "Q276548": "secret society",
    # Tier A - terrorism, organised crime, genocide, hate groups.
    "Q17127659": "terrorist organisation",
    "Q1260006": "drug cartel",
    "Q41397": "genocide",
    "Q3233801": "hate group",
    # ── Target-only classes (Tier B: fine to begin on and read, wrong as the shared headline) ──
    # Politics and conflict: disputed / occupied territories and states with limited recognition.
    "Q15239622": "disputed territory",
    "Q2577883": "occupied territory",
    "Q10711424": "state with limited recognition",
    # Historical wars, battles and uprisings (settled history, but an odd thing to "reach").
    "Q198": "war or armed conflict",
    "Q350604": "war or armed conflict",
    "Q178561": "war or armed conflict",
    "Q124734": "war or armed conflict",
    "Q8465": "war or armed conflict",
    "Q188055": "war or armed conflict",
    "Q831663": "war or armed conflict",
    "Q1006311": "war or armed conflict",
    # Weapons and military equipment; religious texts; diseases and medical conditions.
    "Q728": "weapon",
    "Q179461": "religious text",
    "Q12136": "disease",
}

# Classes that are only a problem for a *target* (a loaded or odd destination), fine as a start.
TARGET_ONLY_QIDS: frozenset[str] = frozenset(
    {
        "Q15239622",
        "Q2577883",
        "Q10711424",
        "Q198",
        "Q350604",
        "Q178561",
        "Q124734",
        "Q8465",
        "Q188055",
        "Q831663",
        "Q1006311",
        "Q728",
        "Q179461",
        "Q12136",
    }
)

# Wikidata claim properties whose values we test against SENSITIVE_QIDS.
CLAIM_PROPS = ("P31", "P279", "P106")

POLITICIAN_QID = "Q82955"  # occupation: politician
MODERN_POLITICS_CUTOFF_YEAR = (
    1950  # a politician active/alive from here on is "modern", not settled
)
RECENT_DEATH_DAYS = 365  # a death within the last 12 months is too raw for an endpoint

# ── Short-description signals (safety net; matched case-insensitively) ────────────────────────────
# Phrases avoid obvious false positives: "stimulant drug" not bare "stimulant"; "secret society"
# not "society". Each (pattern, reason, start_too) - start_too=False means target-only.
_DESC_RULES: list[tuple[str, str, bool]] = [
    (
        r"serial killer|mass murderer|\bmurderer\b|\bassassin\b|war criminal|\bgangster\b"
        r"|\bmobster\b|crime boss|drug lord|drug trafficker|drug kingpin|\brapist\b|sex offender",
        "murderer or criminal",
        True,
    ),
    (
        r"\bmassacre\b|\bgenocide\b|mass shooting|school shooting|ethnic cleansing|\bpogrom\b"
        r"|\bterroris|suicide bombing",
        "violence or atrocity",
        True,
    ),
    (
        r"hate group|neo-nazi|neo-fascist|white supremacis|white nationalis|extremist (group|organi)",
        "hate or extremist group",
        True,
    ),
    (
        r"\bdrug\b|psychoactive|narcotic|\bopioid\b|\bopiate\b|hallucinogen|psychedelic"
        r"|\bmethamphetamine\b|\bamphetamine\b|\bcocaine\b|\bheroin\b|\bcannabis\b|marijuana"
        r"|barbiturate|\becstasy\b|\bMDMA\b",
        "drug",
        True,
    ),
    (
        r"\bsuicide\b|self-harm|eating disorder",
        "suicide or self-harm",
        True,
    ),
    (r"conspiracy theor|secret society|\bcult\b", "conspiracy theory or secret society", True),
    (
        r"pornograph|\berotic|\bfetish\b|masturbat|sexual (intercourse|act|practice|position)"
        r"|sex position|\bprostitut",
        "sexual topic",
        True,
    ),
]
DESC_PATTERNS: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(p, re.I), reason, start_too) for p, reason, start_too in _DESC_RULES
]


def sensitive_by_claims(claim_qids: Iterable[str], *, target: bool = True) -> str | None:
    """Reason if any Wikidata claim value marks a sensitive class, else None.

    When target is False, the target-only classes (disputed territory, …) are ignored.
    """
    for qid in claim_qids:
        reason = SENSITIVE_QIDS.get(qid)
        if reason and (target or qid not in TARGET_ONLY_QIDS):
            return reason
    return None


def sensitive_by_description(desc: str, *, target: bool = True) -> str | None:
    """Reason if the short description reads as a sensitive topic, else None."""
    if not desc:
        return None
    for pattern, reason, start_too in DESC_PATTERNS:
        if (target or start_too) and pattern.search(desc):
            return reason
    return None


def sensitive_reason(desc: str, claim_qids: Iterable[str] = ()) -> str | None:
    """Combined claims-then-description check (target view). Kept for callers/tests."""
    return sensitive_by_claims(claim_qids) or sensitive_by_description(desc)


def _year(iso: str | None) -> int | None:
    """Year from a Wikidata time literal like '+1967-10-09T00:00:00Z' (or '-0044-…'), else None."""
    if not iso:
        return None
    m = re.match(r"([+-]?)(\d+)-", iso)
    if not m:
        return None
    year = int(m.group(2))
    return -year if m.group(1) == "-" else year


def is_modern_politician(
    occupations: Iterable[str], positions_held: Iterable[str], death_iso: str | None
) -> bool:
    """A politician (occupation or any position held) who is living or died in/after 1950.

    Settled historical figures (Lincoln, Disraeli, Napoleon, Vespasian) died well before the cutoff
    and pass; Che Guevara (d. 1967), Tony Blair (living) and Dilma Rousseff (living) do not.
    """
    is_pol = POLITICIAN_QID in set(occupations) or any(True for _ in positions_held)
    if not is_pol:
        return False
    year = _year(death_iso)
    return year is None or year >= MODERN_POLITICS_CUTOFF_YEAR


def died_recently(death_iso: str | None, today: dt.date, days: int = RECENT_DEATH_DAYS) -> bool:
    """True if the Wikidata death date is within `days` before today."""
    if not death_iso:
        return False
    m = re.match(r"\+(\d{4})-(\d{2})-(\d{2})", death_iso)
    if not m:
        return False
    y, mo, d = (int(x) for x in m.groups())
    if mo == 0 or d == 0:  # Wikidata uses 00 for unknown month/day; treat as year-only, not recent
        return False
    try:
        died = dt.date(y, mo, d)
    except ValueError:
        return False
    return dt.timedelta(0) <= (today - died) <= dt.timedelta(days=days)


def target_policy_reason(
    *,
    desc: str,
    instance_classes: Iterable[str],
    occupations: Iterable[str],
    positions_held: Iterable[str],
    convicted_of: Iterable[str],
    death_iso: str | None,
    today: dt.date,
) -> str | None:
    """Why this article must not be a *target*, or None if it is allowed. Cheapest checks first."""
    instance_classes = list(instance_classes)
    occupations = list(occupations)
    if any(True for _ in convicted_of):
        return "convicted of a crime (P1399)"
    by_class = sensitive_by_claims(instance_classes + occupations, target=True)
    if by_class:
        return by_class
    if is_modern_politician(occupations, positions_held, death_iso):
        return "modern politician (in office or active since 1950)"
    if died_recently(death_iso, today):
        return "died within the last 12 months"
    return sensitive_by_description(desc, target=True)


def start_policy_reason(
    *,
    desc: str,
    instance_classes: Iterable[str],
    occupations: Iterable[str],
    convicted_of: Iterable[str],
    death_iso: str | None,
    today: dt.date,
) -> str | None:
    """Why this article must not be a *start* either (the Tier A subset), or None if allowed.

    Politicians and disputed territories are fine to begin on, so the modern-politics and
    territory rules are not applied here.
    """
    instance_classes = list(instance_classes)
    occupations = list(occupations)
    if any(True for _ in convicted_of):
        return "convicted of a crime (P1399)"
    by_class = sensitive_by_claims(instance_classes + occupations, target=False)
    if by_class:
        return by_class
    if died_recently(death_iso, today):
        return "died within the last 12 months"
    return sensitive_by_description(desc, target=False)
