"""Controlled vocabularies for the GA DCH CON database.

These constants mirror the seed data in schema/migrations/. The codes stored in
the database are these exact strings.
"""

import re
from collections.abc import Sequence

SERVICE_TYPES: tuple[str, ...] = (
    "Acute-care/general hospital beds",
    "Psychiatric inpatient beds",
    "Substance-abuse beds",
    "Skilled nursing/LTC beds",
    "Comprehensive inpatient rehabilitation beds",
    "Ambulatory surgery — single-specialty",
    "Ambulatory surgery — multi-specialty",
    "Open-heart/cardiac surgery",
    "Cardiac catheterization",
    "Megavoltage radiation therapy",
    "PET",
    "MRI",
    "CT",
    "Other diagnostic imaging",
    "Obstetrical services",
    "NICU/perinatal",
    "Organ transplant",
    "Lithotripsy",
    "Renal dialysis/ESRD",
    "Home health",
    "Hospice/palliative",
    "New/replacement hospital",
    "Freestanding ED",
    "Birthing center",
    "Major medical equipment",
    "Capital expenditure / new institutional health service (catch-all)",
)

MATTER_TYPES: tuple[str, ...] = (
    "CON Application",
    "Determination/Reviewability (DET)",
    "Administrative Appeal",
    "Judicial Review",
    "Other/Administrative",
)

ACTION_TYPES: tuple[str, ...] = (
    "New service/facility",
    "Bed or capacity addition",
    "Relocation",
    "Replacement",
    "Change of ownership (CHOW)",
    "Cost overrun/capital amendment",
    "Determination request",
    "Other",
)

DOC_TYPES: tuple[str, ...] = (
    "Application/Request",
    "Decision/Determination",
    "Hearing Officer Decision",
    "Final Agency Decision",
    "Order",
    "Notice",
    "Transcript",
    "Exhibit",
    "Brief/Memorandum",
    "Correspondence",
    "HFR Opinion",
    "Court Order/Opinion",
    "Settlement/Withdrawal",
    "Other",
)

PHASES: tuple[str, ...] = (
    "Initial Application",
    "Administrative Appeal",
    "Judicial Review – Superior Court",
    "Judicial Review – Court of Appeals",
    "Judicial Review – Supreme Court of GA",
)

OUTCOMES: tuple[str, ...] = (
    "Approved",
    "Approved with conditions",
    "Partially approved",
    "Denied",
    "Withdrawn",
    "Dismissed",
    "Remanded",
    "Settled",
    "Affirmed (appeal)",
    "Reversed (appeal)",
    "Vacated (appeal)",
    "Pending",
    "Unknown",
)

DECISION_LEVELS: dict[int, str] = {
    1: "Desk Decision",
    2: "Hearing Officer Decision",
    3: "Superior Court Decision",
    4: "Appellate Court Decision",
    5: "Initial Application",
}

VALIDATION_STATUSES: tuple[str, ...] = ("Unvalidated", "Validated", "Corrected", "Rejected")

# Lifecycle-event section codes for the weekly CON Tracking Report. The real
# report has more section headings than codes; each event also stores the
# literal heading (section_heading). Batching-cycle LOI headings map into
# LETTER_OF_INTENT; the misc/EQT/ASC determination-request headings map into
# LETTER_OF_DETERMINATION; informational sections map to OTHER.
REPORT_SECTIONS: tuple[str, ...] = (
    "LETTER_OF_INTENT",
    "LOI_EXPIRED",
    "NEW_APPLICATION",
    "WITHDRAWN_APPLICATION",
    "PENDING_APPLICATION",
    "APPROVED",
    "DENIED",
    "DISQUALIFIED",
    "APPEALED",
    "APPEALED_DETERMINATION",
    "LETTER_OF_DETERMINATION",
    "DET_REVIEW",
    "LNR_CONVERSION",
    "EXTENDED_IMPLEMENTATION",
    "OTHER",
)

# --- Research layer (v2) controlled vocabularies -----------------------------
# These mirror the research-layer vocab tables in DESIGN.md ("RESEARCH LAYER
# (v2)") and are seeded by schema/migrations/0007. Codes are the exact strings
# stored in the database. Order matches the DESIGN tables.

# con.vocab_treatment — citator treatment verbs.
TREATMENTS: tuple[str, ...] = (
    "Followed",
    "Distinguished",
    "Criticized",
    "Reversed",
    "Overruled",
    "Cited",
    "Neutral",
)

# con.vocab_docket_family — docket family classification (common/docket_family.py).
DOCKET_FAMILIES: tuple[str, ...] = (
    "CON",
    "DET",
    "DET-EQT",
    "DET-ASC",
    "LNR-ASC",
    "LNR-EQT",
)

# con.vocab_event_type — docket_event timeline event types.
EVENT_TYPES: tuple[str, ...] = (
    "Filing",
    "Order",
    "Opinion",
    "Hearing",
    "Brief",
    "Notice",
)

# con.vocab_counsel_side — party side for counsel / briefs.
COUNSEL_SIDES: tuple[str, ...] = (
    "Applicant",
    "Petitioner",
    "Respondent",
    "Appellant",
    "Appellee",
    "Intervenor",
    "Amicus",
    "Agency",
)

# con.vocab_treatment_level — good-law banner level.
TREATMENT_LEVELS: tuple[str, ...] = (
    "positive",
    "caution",
    "negative",
    "neutral",
)

# The 159 Georgia counties, Title Case as conventionally written.
COUNTIES: tuple[str, ...] = (
    "Appling", "Atkinson", "Bacon", "Baker", "Baldwin", "Banks", "Barrow", "Bartow",
    "Ben Hill", "Berrien", "Bibb", "Bleckley", "Brantley", "Brooks", "Bryan", "Bulloch",
    "Burke", "Butts", "Calhoun", "Camden", "Candler", "Carroll", "Catoosa", "Charlton",
    "Chatham", "Chattahoochee", "Chattooga", "Cherokee", "Clarke", "Clay", "Clayton",
    "Clinch", "Cobb", "Coffee", "Colquitt", "Columbia", "Cook", "Coweta", "Crawford",
    "Crisp", "Dade", "Dawson", "Decatur", "DeKalb", "Dodge", "Dooly", "Dougherty",
    "Douglas", "Early", "Echols", "Effingham", "Elbert", "Emanuel", "Evans", "Fannin",
    "Fayette", "Floyd", "Forsyth", "Franklin", "Fulton", "Gilmer", "Glascock", "Glynn",
    "Gordon", "Grady", "Greene", "Gwinnett", "Habersham", "Hall", "Hancock", "Haralson",
    "Harris", "Hart", "Heard", "Henry", "Houston", "Irwin", "Jackson", "Jasper",
    "Jeff Davis", "Jefferson", "Jenkins", "Johnson", "Jones", "Lamar", "Lanier",
    "Laurens", "Lee", "Liberty", "Lincoln", "Long", "Lowndes", "Lumpkin", "Macon",
    "Madison", "Marion", "McDuffie", "McIntosh", "Meriwether", "Miller", "Mitchell",
    "Monroe", "Montgomery", "Morgan", "Murray", "Muscogee", "Newton", "Oconee",
    "Oglethorpe", "Paulding", "Peach", "Pickens", "Pierce", "Pike", "Polk", "Pulaski",
    "Putnam", "Quitman", "Rabun", "Randolph", "Richmond", "Rockdale", "Schley",
    "Screven", "Seminole", "Spalding", "Stephens", "Stewart", "Sumter", "Talbot",
    "Taliaferro", "Tattnall", "Taylor", "Telfair", "Terrell", "Thomas", "Tift",
    "Toombs", "Towns", "Treutlen", "Troup", "Turner", "Twiggs", "Union", "Upson",
    "Walker", "Walton", "Ware", "Warren", "Washington", "Wayne", "Webster", "Wheeler",
    "White", "Whitfield", "Wilcox", "Wilkes", "Wilkinson", "Worth",
)

_COUNTY_LOOKUP = {c.upper().replace(" ", "").replace("-", ""): c for c in COUNTIES}


def match_county(raw: str) -> str | None:
    """Match a raw county string to the canonical Title Case name.

    Tolerates case, whitespace, hyphens, and a trailing "County" suffix.
    Returns None when the value is not one of the 159 counties.
    """
    if not raw:
        return None
    key = raw.strip().upper()
    if key.endswith(" COUNTY"):
        key = key[: -len(" COUNTY")]
    return _COUNTY_LOOKUP.get(key.replace(" ", "").replace("-", ""))


def _vocab_norm(value: str) -> str:
    norm = " ".join(value.split()).casefold().replace("—", "-").replace("–", "-")
    # Real DCH exports write "Application / Request" where the vocabulary has
    # "Application/Request" — spacing around slashes is not significant.
    return re.sub(r"\s*/\s*", "/", norm)


def match_vocab(value: str, allowed: Sequence[str]) -> str | None:
    """Match a raw value against a controlled vocabulary.

    Exact match after trimming, case-folding, dash unification (ASCII hyphen
    matches en/em dash), and slash-spacing normalization. No fuzzy guessing:
    unmatched values return None and belong in a rejects report.
    """
    if not value:
        return None
    norm = _vocab_norm(value)
    for a in allowed:
        if norm == _vocab_norm(a):
            return a
    return None
