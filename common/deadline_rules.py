"""Regulatory deadline rules for the CON research layer — single source of truth.

``DEADLINE_RULES`` is the canonical set of rows that seed ``con.deadline_rule``
(see schema/migrations/0009_deadline_rules.sql) AND back the API endpoint
``POST /deadlines/calculate``. Keep the two in sync: the migration's INSERTs
must match ``DEADLINE_RULES`` field-for-field.

Offsets are taken from the docket-engine copy (DESIGN.md):
    CON  — challenge window 30 days after the letter of determination;
           HO appointment within 30 days of the challenge;
           hearing window 60-120 days after appointment;
           HO decision within 30 days of hearing conclusion;
           judicial petition within 30 days of the final agency decision;
           120-day default finality on judicial review.
    DET  — sufficiency screen (~11 days, informational);
           letter of determination due ~60 days from filing;
           challenge window 30 days; same appeal mechanics as CON.

``basis_statute`` holds the statute id (bare O.C.G.A. section, subsection
stripped) matching the corpus convention: '31-6-2', '31-6-44', '31-6-44.1',
'50-13-19'. It is the FK target for con.deadline_rule.basis_statute.

The DET-family subtypes (DET-EQT, DET-ASC, LNR-ASC, LNR-EQT) share the base
'DET' rules; ``compute_deadlines`` folds them onto 'DET'. Pure: no I/O.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from common import vocab


@dataclass(frozen=True)
class DeadlineRule:
    """One regulatory deadline rule (mirrors a con.deadline_rule row)."""

    rule_id: str
    docket_family: str
    trigger_event: str
    offset_days: int
    basis_statute: str
    description: str


@dataclass(frozen=True)
class ComputedDeadline:
    """A deadline resolved against a concrete base date."""

    label: str
    due_date: date
    basis_statute: str
    description: str


DEADLINE_RULES: list[DeadlineRule] = [
    # --- CON family ---------------------------------------------------------
    DeadlineRule(
        "con-challenge-window",
        "CON",
        "Letter of determination",
        30,
        "31-6-44",
        "Request for an administrative hearing (challenge) is due within 30 "
        "days of the letter of determination.",
    ),
    DeadlineRule(
        "con-ho-appointment",
        "CON",
        "Challenge filed",
        30,
        "31-6-44",
        "Hearing officer appointment is due within 30 days of the challenge.",
    ),
    DeadlineRule(
        "con-hearing-window-open",
        "CON",
        "Hearing officer appointed",
        60,
        "31-6-44",
        "Hearing window opens 60 days after the hearing officer appointment.",
    ),
    DeadlineRule(
        "con-hearing-window-close",
        "CON",
        "Hearing officer appointed",
        120,
        "31-6-44",
        "Hearing window closes 120 days after the hearing officer appointment.",
    ),
    DeadlineRule(
        "con-ho-decision",
        "CON",
        "Hearing concluded",
        30,
        "31-6-44",
        "Hearing officer decision is due within 30 days of hearing conclusion.",
    ),
    DeadlineRule(
        "con-judicial-petition",
        "CON",
        "Final agency decision",
        30,
        "31-6-44.1",
        "Petition for judicial review is due within 30 days of the final "
        "agency decision.",
    ),
    DeadlineRule(
        "con-finality-default",
        "CON",
        "Superior court docketing",
        120,
        "50-13-19",
        "120-day default: if the superior court does not hear the case within "
        "120 days of docketing, the agency decision is affirmed by operation "
        "of law (O.C.G.A. § 50-13-19, as modified by § 31-6-44.1).",
    ),
    # --- DET family (subtypes fold onto DET) --------------------------------
    DeadlineRule(
        "det-sufficiency",
        "DET",
        "Request filed",
        11,
        "31-6-2",
        "Sufficiency screen (administrative, informational) — opens the "
        "~60-day review window.",
    ),
    DeadlineRule(
        "det-letter",
        "DET",
        "Request filed",
        60,
        "31-6-2",
        "Letter of determination is due ~60 days from filing.",
    ),
    DeadlineRule(
        "det-challenge-window",
        "DET",
        "Letter of determination",
        30,
        "31-6-44",
        "Challenge (request for an administrative hearing) is due within 30 "
        "days of the letter of determination.",
    ),
    DeadlineRule(
        "det-ho-appointment",
        "DET",
        "Challenge filed",
        30,
        "31-6-44",
        "Hearing officer appointment is due within 30 days of the appeal — "
        "same mechanics as the CON administrative appeal.",
    ),
    DeadlineRule(
        "det-hearing-window-open",
        "DET",
        "Hearing officer appointed",
        60,
        "31-6-44",
        "Hearing window opens 60 days after appointment — same mechanics as CON.",
    ),
    DeadlineRule(
        "det-hearing-window-close",
        "DET",
        "Hearing officer appointed",
        120,
        "31-6-44",
        "Hearing window closes 120 days after appointment — same mechanics as CON.",
    ),
    DeadlineRule(
        "det-ho-decision",
        "DET",
        "Hearing concluded",
        30,
        "31-6-44",
        "Hearing officer decision is due within 30 days of hearing conclusion; "
        "under HB 1339 the HO decision is the final agency decision.",
    ),
    DeadlineRule(
        "det-judicial-petition",
        "DET",
        "Final agency decision",
        30,
        "31-6-44.1",
        "Petition for judicial review is due within 30 days of the final "
        "agency decision.",
    ),
    DeadlineRule(
        "det-finality-default",
        "DET",
        "Superior court docketing",
        120,
        "50-13-19",
        "120-day default finality on judicial review (O.C.G.A. § 50-13-19, as "
        "modified by § 31-6-44.1).",
    ),
]

_ACRONYMS = {"ho": "HO", "dch": "DCH", "con": "CON", "det": "DET", "lnr": "LNR"}


def _base_family(family: str) -> str | None:
    """Fold a docket family onto the family that owns its deadline rules."""
    if family == "CON":
        return "CON"
    if family in ("DET", "DET-EQT", "DET-ASC", "LNR-ASC", "LNR-EQT"):
        return "DET"
    return None


def _humanize(rule_id: str) -> str:
    """Short human label derived from a rule id ('con-ho-appointment' -> 'HO Appointment')."""
    parts = rule_id.split("-")
    if parts and parts[0] in ("con", "det"):
        parts = parts[1:]
    return " ".join(_ACRONYMS.get(p, p.capitalize()) for p in parts)


def compute_deadlines(family: str, trigger_event: str, base: date) -> list[ComputedDeadline]:
    """Resolve every deadline rule for ``(family, trigger_event)`` against ``base``.

    DET subtypes reuse the base 'DET' rules. Returns an empty list for an
    unknown family or a trigger with no matching rules.
    """
    fam = _base_family(family)
    if fam is None:
        return []
    out: list[ComputedDeadline] = []
    for rule in DEADLINE_RULES:
        if rule.docket_family == fam and rule.trigger_event == trigger_event:
            out.append(
                ComputedDeadline(
                    label=_humanize(rule.rule_id),
                    due_date=base + timedelta(days=rule.offset_days),
                    basis_statute=rule.basis_statute,
                    description=rule.description,
                )
            )
    return out


# Sanity: every rule declares a valid docket family.
assert all(r.docket_family in vocab.DOCKET_FAMILIES for r in DEADLINE_RULES)
