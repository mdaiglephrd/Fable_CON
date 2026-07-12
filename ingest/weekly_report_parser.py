"""Parser/loader for the GA DCH weekly "CON Tracking Report" PDF.

The report is organized by lifecycle section (Letters of Intent, New CON
Applications, ..., Requests for Extended Implementation); each entry carries a
docket/project number, applicant, project description, dates, site/county,
estimated cost, and opposition status. Empty sections print the single word
"none" and yield no events.

ALL layout assumptions live in the module-level tables below
(ARTIFACT_PATTERNS, REPORT_DATE_PATTERNS, SECTION_PATTERNS,
ENTRY_START_LABEL_PATTERNS, BARE_CON_DOCKET_RE, FIELD_PATTERNS,
UNKNOWN_LABEL_RE, SITE_COUNTY_PATTERNS, DATE_PATTERNS, cost regexes) so that
re-tuning against a new report layout is a table edit, not a rewrite.

Tuned against the real DCH sample of 2026-04-21. pdfplumber loses many spaces
in that PDF ("Letters ofIntent", "Deniedon12/6/2024", "30thDayDeadline:"), so
every word gap in these tables is \\s* rather than a literal space, and page
numbers glue onto the first line of each page (handled in _clean_lines).

CLI:
    python -m ingest.weekly_report_parser report.pdf [--apply] [--out events.json]
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from common.docket import DocketMatch, extract_dockets, normalize_docket
from common.vocab import REPORT_SECTIONS, match_county

# ---------------------------------------------------------------------------
# Layout assumption tables — edit these to re-tune against a new report layout.
# ---------------------------------------------------------------------------

# Lines that are page furniture, not content: standalone page numbers,
# "Page N of M" footers, "(continued)" running headers, decoration rows.
# Page numbers GLUED to the first line of a page are handled in _clean_lines.
ARTIFACT_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^\s*\d{1,3}\s*$"),  # bare page number on its own line
    re.compile(r"^\s*Page\s*\d+(?:\s*of\s*\d+)?\s*$", re.IGNORECASE),
    re.compile(r".*\(continued\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*[-=_~]{3,}\s*$"),
)

# Date token alternation: "June 22, 2026" | "06/22/2026" | "6/22/26" | ISO.
# \s* between month and day: the real PDF glues words ("onApril 15").
_DATE_TOKEN = r"([A-Za-z]{3,9}\.?\s*\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})"
# NB: \b does not fire between letters and digits ("Deniedon12/6/2024"), so
# the slash-date patterns below use explicit lookarounds instead.
_DATE_TOKEN_NC = _DATE_TOKEN.replace("(", "(?:", 1)  # non-capturing twin

# Tried in order over the first REPORT_DATE_SEARCH_LINES cleaned lines (the
# real report's page 1 is a TOC/notices page; the reporting period appears as
# a range "April 15, 2026 – April 21, 2026" — report_date is the END date).
# group(1) of each pattern is the date string to parse.
REPORT_DATE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(rf"{_DATE_TOKEN_NC}\s*[-–—]\s*{_DATE_TOKEN}", re.IGNORECASE),  # range: take end
    re.compile(rf"\bWeek\s*of\s*{_DATE_TOKEN}", re.IGNORECASE),
    re.compile(rf"\bReport\s*Date\s*:?\s*{_DATE_TOKEN}", re.IGNORECASE),
    re.compile(rf"\bfor\s*the\s*week\s*(?:of|ending)\s*{_DATE_TOKEN}", re.IGNORECASE),
    re.compile(rf"^\s*{_DATE_TOKEN}\s*$", re.IGNORECASE),  # bare date line near the top
)
REPORT_DATE_SEARCH_LINES = 60  # only look this far down for the report date

# Section headings. Ordered (pattern, section_code): first match wins, so the
# more specific headings ("Letters of Intent – Batching") precede the general
# ones. Patterns match the WHOLE line; word gaps are \s* (glued text) and the
# named group "h" captures the literal heading text for event.section_heading.
# The trailing OTHER entries are fences for the informational sections at the
# back of the real report so their prose cannot attach to real entries; any
# docket entries found under them are emitted with section OTHER.
_HDR_PREFIX = r"^\s*(?:IMPORTANT\s*NOTICES\s*)?(?:SECTION\s*)?(?:[IVX\d]+\s*[.):]\s*)?"
_HDR_SUFFIX = r"\s*:?\s*$"


def _hdr(words: str) -> re.Pattern:
    return re.compile(_HDR_PREFIX + rf"(?P<h>{words})" + _HDR_SUFFIX, re.IGNORECASE)


SECTION_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (_hdr(r"Letters?\s*of\s*Intent\s*[-–—]\s*Batching"), "LETTER_OF_INTENT"),
    (_hdr(r"(?:Expired\s*Letters?\s*of\s*Intent|Letters?\s*of\s*Intent\s*[-–—]\s*Expired)"), "LOI_EXPIRED"),
    (_hdr(r"Letters?\s*of\s*Intent(?:\s*Received|\s*Filed)?"), "LETTER_OF_INTENT"),
    (_hdr(r"(?:New\s*(?:CON\s*)?Applications?(?:\s*Received|\s*Filed)?|Applications?\s*Received)"), "NEW_APPLICATION"),
    (_hdr(r"Withdrawn\s*(?:CON\s*)?(?:Applications?|Projects?)?"), "WITHDRAWN_APPLICATION"),
    (_hdr(r"Pending\s*(?:Review\s*)?Applications?"), "PENDING_APPLICATION"),
    (_hdr(r"(?:Recently\s*)?Approved\s*(?:CON\s*)?(?:Applications?|Projects?)?"), "APPROVED"),
    (_hdr(r"(?:Recently\s*)?Denied\s*(?:CON\s*)?(?:Applications?|Projects?)?"), "DENIED"),
    (_hdr(r"Disqualified\s*(?:CON\s*)?Applications?"), "DISQUALIFIED"),
    (_hdr(r"Appealed\s*Determinations?"), "APPEALED_DETERMINATION"),
    (_hdr(r"Appealed\s*(?:CON\s*)?Projects?"), "APPEALED"),
    (_hdr(r"Requests?\s*for\s*Miscellaneous\s*Letters?\s*of\s*Determination"), "LETTER_OF_DETERMINATION"),
    (_hdr(r"Requests?\s*for\s*DET\s*[-–—]?\s*EQT\b.*"), "LETTER_OF_DETERMINATION"),
    (_hdr(r"Requests?\s*for\s*DET\s*[-–—]?\s*ASC\b.*"), "LETTER_OF_DETERMINATION"),
    (_hdr(r"Letters?\s*of\s*Determination(?:\s*,?\s*generally)?"), "LETTER_OF_DETERMINATION"),
    (_hdr(r"DET\s*Review\s*,?\s*generally"), "DET_REVIEW"),
    (_hdr(r"LNR\s*Conversion"), "LNR_CONVERSION"),
    (_hdr(r"Requests?\s*for\s*Extended\s*Implementation.*"), "EXTENDED_IMPLEMENTATION"),
    # Informational back-matter fences (real report pages 19-29).
    (_hdr(r"Need\s*Projection\s*Analyses.*"), "OTHER"),
    (_hdr(r"Non[-\s]*Filed\s*or\s*Incomplete.*"), "OTHER"),
    (_hdr(r"New\s*Certificate\s*of\s*Need\s*Filing\s*Requirements.*"), "OTHER"),
    (_hdr(r"Batching\s*(?:Review|Notifications?).*"), "OTHER"),
    (_hdr(r"(?:Non[-\s]*)?Batched\s*Applications.*"), "OTHER"),
    (_hdr(r"Office\s*of\s*Health\s*Planning\s*Contact\s*Information"), "OTHER"),
    (_hdr(r"Open\s*Record\s*Requests?"), "OTHER"),
    (_hdr(r"Web\s*Links"), "OTHER"),
    (_hdr(r"(?:Important\s*)?Notices?\s*(?:Regarding|Related\s*To).*"), "OTHER"),
    (_hdr(r"Certificate\s*of\s*Need\s*Appeal\s*Panel"), "OTHER"),
)
assert {code for _, code in SECTION_PATTERNS} == set(REPORT_SECTIONS)

# Empty sections contain just this word — they emit no events.
NONE_LINE_RE = re.compile(r"^\s*none\.?\s*$", re.IGNORECASE)

# Entry starts. Real reports lead each entry with the docket at the START of
# the line: bare year-seq CON project numbers ("2026-002", or already-compact
# "2023013" — the CON prefix is implied; repository form is CON{YYYY}{SEQ3}),
# or a prefixed docket (DET-EQT2024-073, DET2026004, LNR-...). A "Project
# No."-style label also starts an entry. Dockets appearing MID-line do not
# start entries (litigation narratives mention other dockets in passing).
BARE_CON_DOCKET_RE = re.compile(r"^\s*(20\d{2})(?:\s*-\s*(\d{1,4})|(\d{3}))(?!\d)")
ENTRY_START_LABEL_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^\s*(?:Project|Docket|File|Matter)\s*(?:No\.?|Number|#)", re.IGNORECASE),
)

# Field labels: ordered (field_name, label_pattern). Patterns match the LABEL
# only; a value runs from the end of its label to the next label on the line
# (several "Label: value" pairs may share a line). Word gaps are \s* because
# the real PDF glues words ("30thDayDeadline:"). Fields not stored on
# ReportEvent ("_"-prefixed) are consumed so their text cannot leak into the
# project description; "_determination" additionally feeds the decision_date
# fallback ("Determination: Approved, 4/9/2026").
FIELD_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("docket_label", re.compile(r"\b(?:Project|Docket|File|Matter)\s*(?:No\.?|Number|#)\s*:?", re.IGNORECASE)),
    # Litigation-narrative court lines must outrank the "County:" label below
    # ("Superior Court ofFulton County: Denies ..." is not a county field).
    ("_court", re.compile(
        r"\bSuperior\s*Court\s*of[A-Za-z\s]*?County(?:\s*Decision\s*on\s*Remand)?\s*:"
        r"|\bCourt\s*of\s*Appeals\s*:",
        re.IGNORECASE)),
    ("applicant", re.compile(r"\bApplicant\s*:", re.IGNORECASE)),
    ("project_description", re.compile(r"\bProject\s*(?:Description)?\s*:", re.IGNORECASE)),
    ("county", re.compile(r"\bCounty\s*:", re.IGNORECASE)),
    ("site", re.compile(r"\bSite\s*:", re.IGNORECASE)),
    ("cost", re.compile(
        r"\b(?:(?:Estimated|Approved|Total)\s*)?Cost\s*:|\bProject\s*costs?\s*as\s*submitted\s*:",
        re.IGNORECASE)),
    ("opposition", re.compile(r"\bOpposition\s*:", re.IGNORECASE)),
    ("filing_date", re.compile(r"\b(?:Date\s*Filed|Filing\s*Date|Filed|Request\s*Received)\s*:", re.IGNORECASE)),
    ("decision_deadline", re.compile(
        r"\b(?:Decision\s*Deadline|Decision\s*Due|Review\s*Period\s*Ends)\s*:", re.IGNORECASE)),
    ("decision_date", re.compile(
        r"\b(?:Agency\s*Decision|Determination\s*Date|Date\s*of\s*Withdrawal|Decision\s*Date)\s*:",
        re.IGNORECASE)),
    ("_determination", re.compile(r"\bDetermination\s*:", re.IGNORECASE)),
    ("_deemed", re.compile(r"\bDeemed\s*(?:Complete|Incomplete)\s*:", re.IGNORECASE)),
    ("_30th_day", re.compile(r"\b30th\s*Day\s*Deadline\s*:", re.IGNORECASE)),
    ("_contact", re.compile(r"\bContact\s*(?:Person)?\s*:", re.IGNORECASE)),
    ("_extended_completion", re.compile(r"\bExtended\s*Mandatory\s*Completion\s*:", re.IGNORECASE)),
)

# An unlabeled line that still LOOKS like "Some Label: value" (Hearing
# Officer:, Appealed By:, Superior Court of X County:, Number of OR's:, ...)
# is kept in raw_text only — it is not description prose.
UNKNOWN_LABEL_RE = re.compile(r"^\s*[A-Za-z][A-Za-z0-9 ./#()'’&–-]{0,45}:(\s|$)")

# Opposition marker appended to a project-description line.
OPPOSITION_MARKER_RE = re.compile(r"[\s\-–—]*OPPOSITION\s*FILED\s*$", re.IGNORECASE)
OPPOSITION_MARKER = "OPPOSITION FILED"

# County out of a Site line: "(Thomas County)" / "( Muscogee)" parenthetical,
# else a ", Bibb County" suffix. Validated via match_county either way.
SITE_COUNTY_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\(\s*([A-Za-z.' -]+?)\s*(?:County)?\s*\)", re.IGNORECASE),
    re.compile(r",\s*([A-Za-z.' -]+?)\s+County\b", re.IGNORECASE),
)

# Appealed CON Projects lead lines carry the county after the applicant:
# "2020-020 University Hospital (Columbia)".
APPLICANT_COUNTY_RE = re.compile(r"\(\s*([A-Za-z.' -]+?)\s*(?:County)?\s*\)\s*$")

# Appealed-determination narrative lead: "<docket> <applicant> Request for
# Letter of Determination received on <date>, regarding <clause>. ..."
APPEAL_REQUEST_RE = re.compile(
    r"^(?P<app>.{3,300}?)[\s,]*Request\s*for\s*(?:a\s*)?Letter\s*of\s*Determination", re.IGNORECASE
)
RECEIVED_ON_RE = re.compile(rf"\breceived\s*(?:on)?\s*:?\s*{_DATE_TOKEN}", re.IGNORECASE)
REGARDING_RE = re.compile(r"\bregarding\s*[:,]?\s*(.+?)(?:\.(?:\s|$)|$)", re.IGNORECASE)

# Date parsing: (token_pattern, strptime formats). parse_date collects every
# match, sorts by position, and returns the earliest one that parses — so
# "Approved, 4/9/2026 ... July 21, 2026" yields 4/9/2026. Month-name tokens
# tolerate a glued lowercase prefix ("onApril 15, 2026" -> "April 15, 2026").
DATE_PATTERNS: tuple[tuple[re.Pattern, tuple[str, ...]], ...] = (
    (re.compile(r"\b[A-Za-z]{3,9}\.?\s*\d{1,2},\s*\d{4}\b"), ("%B %d, %Y", "%b %d, %Y")),
    (re.compile(r"(?<![\d/])\d{1,2}/\d{1,2}/\d{4}(?![\d/])"), ("%m/%d/%Y",)),
    (re.compile(r"(?<![\d/])\d{1,2}/\d{1,2}/\d{2}(?![\d/])"), ("%m/%d/%y",)),
    (re.compile(r"(?<![\d/-])\d{4}-\d{2}-\d{2}(?![\d-])"), ("%Y-%m-%d",)),
)
_LOWER_PREFIX_RE = re.compile(r"^[a-z]+")

# Cost parsing: scaled word form first ("$4.5 million", "$1.2M"), then plain
# "$1,234,567.89", then a bare number when the whole value is numeric.
_COST_MULTIPLIERS: dict[str, Decimal] = {
    "K": Decimal(1_000),
    "THOUSAND": Decimal(1_000),
    "M": Decimal(1_000_000),
    "MILLION": Decimal(1_000_000),
    "B": Decimal(1_000_000_000),
    "BILLION": Decimal(1_000_000_000),
}
_COST_SCALED_RE = re.compile(
    r"\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|[KMB])(?![A-Za-z])", re.IGNORECASE
)
_COST_PLAIN_RE = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)")
_COST_BARE_RE = re.compile(r"^\s*(\d[\d,]*(?:\.\d+)?)\s*$")

_TWO_PLACES = Decimal("0.01")

STUB_COMPLETENESS_FLAGS = '["stub_from_weekly_report"]'

# ---------------------------------------------------------------------------
# Dataclasses (shapes per DESIGN.md)
# ---------------------------------------------------------------------------


@dataclass
class ReportEvent:
    section: str
    section_heading: str | None
    docket_raw: str | None
    docket_id: str | None
    applicant: str | None
    project_description: str | None
    county: str | None
    cost: Decimal | None
    opposition: str | None
    filing_date: date | None
    decision_deadline: date | None
    decision_date: date | None
    raw_text: str


@dataclass
class ReportParse:
    report_date: date | None
    events: list[ReportEvent]
    warnings: list[str]


@dataclass
class LoadStats:
    inserted: int
    skipped_duplicates: int
    stub_matters_created: int


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text(pdf_path: str) -> str:
    """Extract text from every page of the PDF, pages joined with form feed."""
    import pdfplumber  # lazy: pure parsing/tests must not require the PDF stack

    with pdfplumber.open(pdf_path) as pdf:
        return "\f".join((page.extract_text() or "") for page in pdf.pages)


# ---------------------------------------------------------------------------
# Scalar parsers (pure, unit-testable)
# ---------------------------------------------------------------------------


def parse_date(raw: str | None) -> date | None:
    """Parse the EARLIEST date in raw.

    Accepts "June 22, 2026", "06/22/2026", "6/22/26", ISO, and glued forms
    like "on7/27/2022" / "onApril 15, 2026".
    """
    if not raw:
        return None
    candidates: list[tuple[int, str, tuple[str, ...]]] = []
    for pattern, formats in DATE_PATTERNS:
        for m in pattern.finditer(raw):
            candidates.append((m.start(), m.group(0), formats))
    candidates.sort(key=lambda t: t[0])
    for _, token, formats in candidates:
        norm = " ".join(token.replace(".", "").split())
        for attempt in (norm, _LOWER_PREFIX_RE.sub("", norm).strip()):
            if not attempt:
                continue
            for fmt in formats:
                try:
                    return datetime.strptime(attempt, fmt).date()
                except ValueError:
                    continue
    return None


def parse_cost(raw: str | None) -> Decimal | None:
    """Parse "$1,234,567.89" or "$4.5 million" style amounts into Decimal."""
    if not raw:
        return None
    m = _COST_SCALED_RE.search(raw)
    if m:
        multiplier = _COST_MULTIPLIERS[m.group(2).upper()]
        try:
            return (Decimal(m.group(1).replace(",", "")) * multiplier).quantize(_TWO_PLACES)
        except InvalidOperation:
            return None
    m = _COST_PLAIN_RE.search(raw) or _COST_BARE_RE.match(raw)
    if m:
        try:
            return Decimal(m.group(1).replace(",", "")).quantize(_TWO_PLACES)
        except InvalidOperation:
            return None
    return None


def dedupe_hash(report_date: date | None, section: str, docket_raw: str | None, raw_text: str) -> str:
    """sha256 hex over (report_date|section|docket_raw|raw_text)."""
    key = "|".join(
        (
            report_date.isoformat() if report_date else "",
            section or "",
            docket_raw or "",
            raw_text or "",
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Docket helpers (parser-level bare year-seq rule; see DESIGN.md)
# ---------------------------------------------------------------------------


def bare_con_docket(line: str) -> DocketMatch | None:
    """Map a line-leading bare year-seq project number to its CON docket.

    Real reports print CON project numbers without a prefix ("2026-002", or
    already-compact "2023013"); the repository form is CON{YYYY}{SEQ} with the
    sequence zero-padded to 3 ("CON2026002"). This rule applies ONLY to
    entry-leading text — it is too ambiguous for generic extraction, so it
    lives here and not in common.docket.
    """
    m = BARE_CON_DOCKET_RE.match(line)
    if not m:
        return None
    year, seq = m.group(1), (m.group(2) or m.group(3))
    dm = normalize_docket(f"CON{year}{seq.zfill(3)}")
    if dm is None:
        return None
    raw = m.group(0).strip()
    variants = tuple(sorted(set(dm.variants) | {raw}))
    return DocketMatch(canonical=dm.canonical, kind="CON", variants=variants, raw=raw)


def _docket_at_line_start(line: str) -> DocketMatch | None:
    """The docket leading a line, or None. Mid-line dockets do not count."""
    stripped = line.strip()
    dm = bare_con_docket(stripped)
    if dm:
        return dm
    for found in extract_dockets(stripped):
        if stripped.startswith(found.raw):
            return found
    return None


# ---------------------------------------------------------------------------
# Report parsing (pure)
# ---------------------------------------------------------------------------


def _clean_lines(text: str) -> list[str]:
    """Split into lines, dropping page furniture.

    The real PDF's page number glues onto the first text line of each page
    ("2Recently Denied Applications", "72023-072 Bethlehem ASC"); strip it
    when the first line of page N starts with N and the remainder is
    plausible content (starts with a non-digit, or is itself docket-led).
    """
    lines: list[str] = []
    for page_index, page_text in enumerate(text.split("\f")):
        page_no = str(page_index + 1)
        first_content_seen = False
        for raw_line in page_text.splitlines():
            line = raw_line.rstrip()
            if line.strip() and not first_content_seen:
                first_content_seen = True
                stripped = line.strip()
                if stripped == page_no:
                    continue  # standalone page number line
                if stripped.startswith(page_no):
                    rest = stripped[len(page_no):]
                    if rest and (not rest[0].isdigit() or _docket_at_line_start(rest)):
                        line = rest
            if any(p.match(line) for p in ARTIFACT_PATTERNS):
                continue
            lines.append(line)
    return lines


def _match_section_header(line: str) -> tuple[str, str] | None:
    """(section_code, literal heading text) when the line is a section heading."""
    for pattern, code in SECTION_PATTERNS:
        m = pattern.match(line)
        if m:
            heading = " ".join(m.group("h").split()).rstrip(":").strip()
            return code, heading
    return None


def _find_report_date(lines: list[str]) -> date | None:
    """Report date from the top of the report.

    The real report's page 1 is a TOC/notices page whose entries look like
    section headings, so headings do NOT stop the search — only the line
    budget does. Patterns are tried in priority order across the region.
    """
    top = lines[:REPORT_DATE_SEARCH_LINES]
    for pattern in REPORT_DATE_PATTERNS:
        for line in top:
            m = pattern.search(line)
            if m:
                parsed = parse_date(m.group(1))
                if parsed:
                    return parsed
    return None


def _split_sections(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Split cleaned lines into (section_code, heading, body_lines) in order."""
    sections: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str] | None = None
    current_lines: list[str] = []
    for line in lines:
        header = _match_section_header(line)
        if header:
            if current is not None:
                sections.append((current[0], current[1], current_lines))
            current, current_lines = header, []
        elif current is not None:
            current_lines.append(line)
        # Lines before the first section header are report preamble; ignored.
    if current is not None:
        sections.append((current[0], current[1], current_lines))
    return sections


def _is_entry_start(line: str) -> bool:
    if any(p.match(line) for p in ENTRY_START_LABEL_PATTERNS):
        return True
    return _docket_at_line_start(line) is not None


def _split_entries(section_lines: list[str]) -> list[list[str]]:
    """Split a section body into entry blocks.

    An entry starts at a line LEADING with a docket (bare year-seq or
    prefixed) or a "Project No."-style label; other non-blank lines attach to
    the current entry. Lines before the first entry (column headings, "none",
    section notes) are ignored; "none" marks an empty section.
    """
    entries: list[list[str]] = []
    current: list[str] | None = None
    for line in section_lines:
        if not line.strip() or NONE_LINE_RE.match(line):
            continue
        if _is_entry_start(line):
            if current:
                entries.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current:
        entries.append(current)
    return entries


def _label_hits(line: str) -> list[tuple[int, int, str]]:
    """All non-overlapping field-label matches in a line, sorted by position."""
    hits: list[tuple[int, int, str]] = []
    for field_name, pattern in FIELD_PATTERNS:
        for m in pattern.finditer(line):
            hits.append((m.start(), m.end(), field_name))
    hits.sort(key=lambda t: (t[0], -t[1]))  # prefer the longer label on ties
    kept: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, name in hits:
        if start >= last_end:
            kept.append((start, end, name))
            last_end = end
    return kept


def _strip_opposition_marker(parts: list[str]) -> str | None:
    """Remove a trailing OPPOSITION FILED marker from description parts."""
    for i, part in enumerate(parts):
        m = OPPOSITION_MARKER_RE.search(part)
        if m:
            parts[i] = part[: m.start()].rstrip(" -–—")
            return OPPOSITION_MARKER
    return None


def _parse_entry(section: str, heading: str, entry_lines: list[str], warn) -> ReportEvent:
    raw_text = "\n".join(entry_lines).strip()
    flat = " ".join(raw_text.split())

    # --- docket + first-line remainder (applicant lives on the docket line) --
    first_line = entry_lines[0].strip()
    lead_docket = _docket_at_line_start(first_line)
    remainder: str | None = None
    rest_lines = entry_lines[1:]
    if lead_docket is not None:
        docket_id: str | None = lead_docket.canonical
        docket_raw: str | None = lead_docket.raw
        remainder = first_line[len(lead_docket.raw):].strip()
    else:
        # Label-led entry ("Project No.: ..."): docket from anywhere in it.
        found = extract_dockets(raw_text)
        docket_id = found[0].canonical if found else None
        docket_raw = found[0].raw if found else None
        rest_lines = entry_lines  # run the first line through the label loop
    if docket_id is None:
        warn(f"{section}: entry has no recognizable docket: {first_line!r}")

    # --- labeled fields + positional description ----------------------------
    values: dict[str, list[str]] = {}
    desc_parts: list[str] = []
    seen_label = False
    for line in rest_lines:
        stripped = line.strip()
        if not stripped:
            continue
        hits = _label_hits(stripped)
        if not hits:
            if UNKNOWN_LABEL_RE.match(stripped):
                continue  # unknown "Label: value" — raw_text only
            if not seen_label:
                desc_parts.append(stripped)
            # After the first label, unlabeled prose is a wrapped narrative
            # continuation; it stays in raw_text only.
            continue
        lead = stripped[: hits[0][0]].strip()
        if lead and not seen_label:
            desc_parts.append(lead)
        seen_label = True
        for idx, (start, end, name) in enumerate(hits):
            value_end = hits[idx + 1][0] if idx + 1 < len(hits) else len(stripped)
            values.setdefault(name, []).append(stripped[end:value_end].strip(" \t;,-–—"))

    def first(name: str) -> str | None:
        for v in values.get(name, []):
            if v.strip():
                return v.strip()
        return None

    # --- applicant -----------------------------------------------------------
    applicant: str | None = None
    county_from_applicant: str | None = None
    narrative = False
    if remainder:
        m = APPEAL_REQUEST_RE.match(remainder)
        if m:
            # "<applicant> Request for Letter of Determination received on ..."
            applicant = m.group("app").strip(" ,;")
            narrative = True
        else:
            applicant = remainder
            pm = APPLICANT_COUNTY_RE.search(applicant)
            if pm:
                matched_county = match_county(pm.group(1))
                if matched_county:
                    county_from_applicant = matched_county
                    applicant = applicant[: pm.start()].strip()
    if not applicant:
        applicant = first("applicant")

    # --- opposition (label, else OPPOSITION FILED marker on a desc line) -----
    labeled_desc = [v for v in values.get("project_description", []) if v.strip()]
    opposition = first("opposition")
    if opposition is None:
        opposition = _strip_opposition_marker(labeled_desc) or _strip_opposition_marker(desc_parts)

    # --- project description --------------------------------------------------
    if narrative:
        m = REGARDING_RE.search(flat)
        description = m.group(1).strip() if m else (desc_parts[0] if desc_parts else None)
    else:
        description = " ".join(p for p in labeled_desc + desc_parts if p).strip() or None

    # --- county: County: label > Site: > applicant parenthetical --------------
    county: str | None = None
    county_raw = first("county")
    if county_raw:
        county = match_county(county_raw.strip(" .;,"))
        if county is None:
            warn(f"{section}: unrecognized county {county_raw!r} ({docket_raw or 'no docket'})")
    if county is None:
        site_raw = first("site")
        if site_raw:
            for pattern in SITE_COUNTY_PATTERNS:
                m = pattern.search(site_raw)
                if m:
                    county = match_county(m.group(1))
                    if county:
                        break
    if county is None:
        county = county_from_applicant

    # --- cost ------------------------------------------------------------------
    cost_raw = first("cost")
    cost = parse_cost(cost_raw)
    if cost_raw and cost is None:
        warn(f"{section}: unparseable cost {cost_raw!r} ({docket_raw or 'no docket'})")

    # --- dates -------------------------------------------------------------------
    filing_raw = first("filing_date")
    filing_date = parse_date(filing_raw)
    if filing_date is None:
        m = RECEIVED_ON_RE.search(flat)  # narrative "received on 4/5/2022"
        if m:
            filing_date = parse_date(m.group(1))
    if filing_raw and filing_date is None:
        warn(f"{section}: unparseable filing date {filing_raw!r} ({docket_raw or 'no docket'})")

    deadline_raw = first("decision_deadline")
    decision_deadline = parse_date(deadline_raw)
    if deadline_raw and decision_deadline is None:
        warn(f"{section}: unparseable decision deadline {deadline_raw!r} ({docket_raw or 'no docket'})")

    decision_date = parse_date(first("decision_date"))
    if decision_date is None:
        # "Determination: Approved, 4/9/2026" (or "... Pending" -> None).
        decision_date = parse_date(first("_determination"))

    return ReportEvent(
        section=section,
        section_heading=heading or None,
        docket_raw=docket_raw,
        docket_id=docket_id,
        applicant=applicant or None,
        project_description=description,
        county=county,
        cost=cost,
        opposition=opposition,
        filing_date=filing_date,
        decision_deadline=decision_deadline,
        decision_date=decision_date,
        raw_text=raw_text,
    )


def parse_report_text(text: str, report_file: str = "") -> ReportParse:
    """Parse extracted report text into ReportParse. Pure — no I/O, no DB."""
    warnings: list[str] = []
    prefix = f"{report_file}: " if report_file else ""

    def warn(message: str) -> None:
        warnings.append(prefix + message)

    lines = _clean_lines(text or "")

    report_date = _find_report_date(lines)
    if report_date is None:
        warn("report date not found near the top of the report")

    sections = _split_sections(lines)
    if not sections:
        warn("no report sections recognized")

    events: list[ReportEvent] = []
    for code, heading, section_lines in sections:
        for entry_lines in _split_entries(section_lines):
            events.append(_parse_entry(code, heading, entry_lines, warn))

    return ReportParse(report_date=report_date, events=events, warnings=warnings)


# ---------------------------------------------------------------------------
# Loading (DB writes; parameterized T-SQL only)
# ---------------------------------------------------------------------------

_MATTER_EXISTS_SQL = "SELECT 1 FROM con.matter WHERE docket_id = ?"
_MATTER_STUB_INSERT_SQL = (
    "INSERT INTO con.matter (docket_id, completeness_flags) "
    "SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM con.matter WHERE docket_id = ?)"
)
_VARIANT_EXISTS_SQL = "SELECT 1 FROM con.matter_docket_variant WHERE docket_id = ? AND variant = ?"
_VARIANT_INSERT_SQL = (
    "INSERT INTO con.matter_docket_variant (docket_id, variant) "
    "SELECT ?, ? WHERE NOT EXISTS ("
    "SELECT 1 FROM con.matter_docket_variant WHERE docket_id = ? AND variant = ?)"
)
_EVENT_EXISTS_SQL = "SELECT 1 FROM con.weekly_report_event WHERE dedupe_hash = ?"
_EVENT_INSERT_SQL = (
    "INSERT INTO con.weekly_report_event ("
    "report_date, report_file, section, section_heading, docket_id, docket_raw, "
    "applicant, project_description, county, cost, opposition, filing_date, "
    "decision_deadline, decision_date, raw_text, dedupe_hash) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _docket_variants(event: ReportEvent) -> tuple[str, ...]:
    """Variants for the event's docket (re-derived from the printed form)."""
    dm = normalize_docket(event.docket_raw or "")
    if dm is None:
        dm = bare_con_docket(event.docket_raw or "")  # bare "2026-002" form
    if dm:
        return dm.variants
    return tuple(sorted({v for v in (event.docket_raw, event.docket_id) if v}))


def load_events(conn, parse: ReportParse, report_file: str) -> LoadStats:
    """Insert parsed events; create stub matters for unknown canonical dockets.

    - Stub matters are INSERT ... WHERE NOT EXISTS only; existing matters are
      never updated. Docket variants are insert-if-missing.
    - Events are skipped on dedupe_hash match (guard SELECT, not exception
      parsing). Events without a docket insert with docket_id NULL.
    - Raises ValueError when parse.report_date is None (column is NOT NULL).
    """
    if parse.report_date is None:
        raise ValueError("cannot load events: report_date was not found in the report")

    inserted = 0
    skipped_duplicates = 0
    stub_matters_created = 0
    ensured_matters: set[str] = set()
    cur = conn.cursor()

    for event in parse.events:
        event_hash = dedupe_hash(parse.report_date, event.section, event.docket_raw, event.raw_text)
        cur.execute(_EVENT_EXISTS_SQL, event_hash)
        if cur.fetchone() is not None:
            skipped_duplicates += 1
            continue

        if event.docket_id and event.docket_id not in ensured_matters:
            ensured_matters.add(event.docket_id)
            cur.execute(_MATTER_EXISTS_SQL, event.docket_id)
            if cur.fetchone() is None:
                cur.execute(
                    _MATTER_STUB_INSERT_SQL,
                    event.docket_id,
                    STUB_COMPLETENESS_FLAGS,
                    event.docket_id,
                )
                stub_matters_created += 1
            for variant in _docket_variants(event):
                cur.execute(_VARIANT_EXISTS_SQL, event.docket_id, variant)
                if cur.fetchone() is None:
                    cur.execute(_VARIANT_INSERT_SQL, event.docket_id, variant, event.docket_id, variant)

        cur.execute(
            _EVENT_INSERT_SQL,
            parse.report_date,
            report_file or None,
            event.section,
            event.section_heading,
            event.docket_id,
            event.docket_raw,
            event.applicant,
            event.project_description,
            event.county,
            event.cost,
            event.opposition,
            event.filing_date,
            event.decision_deadline,
            event.decision_date,
            event.raw_text,
            event_hash,
        )
        inserted += 1

    conn.commit()
    return LoadStats(
        inserted=inserted,
        skipped_duplicates=skipped_duplicates,
        stub_matters_created=stub_matters_created,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _event_to_jsonable(event: ReportEvent) -> dict:
    out = asdict(event)
    for key, value in out.items():
        if isinstance(value, date):
            out[key] = value.isoformat()
        elif isinstance(value, Decimal):
            out[key] = str(value)
    return out


def _print_summary(parse: ReportParse, report_file: str) -> None:
    print(f"report_file:  {report_file}")
    print(f"report_date:  {parse.report_date.isoformat() if parse.report_date else 'NOT FOUND'}")
    print(f"events:       {len(parse.events)}")
    counts: dict[str, int] = {}
    for event in parse.events:
        counts[event.section] = counts.get(event.section, 0) + 1
    for section in REPORT_SECTIONS:
        if section in counts:
            print(f"  {section:<24} {counts[section]}")
    no_docket = sum(1 for e in parse.events if e.docket_id is None)
    if no_docket:
        print(f"events without docket: {no_docket}")
    if parse.warnings:
        print(f"warnings ({len(parse.warnings)}):")
        for warning in parse.warnings:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m ingest.weekly_report_parser",
        description="Parse a GA DCH weekly CON Tracking Report PDF (and optionally load it).",
    )
    ap.add_argument("pdf", help="path to the weekly CON Tracking Report PDF")
    ap.add_argument("--apply", action="store_true", help="load events into the database")
    ap.add_argument("--out", help="write parsed events to this JSON file")
    args = ap.parse_args(argv)

    report_file = os.path.basename(args.pdf)
    text = extract_text(args.pdf)
    parse = parse_report_text(text, report_file=report_file)
    _print_summary(parse, report_file)

    if args.out:
        payload = {
            "report_file": report_file,
            "report_date": parse.report_date.isoformat() if parse.report_date else None,
            "warnings": parse.warnings,
            "events": [_event_to_jsonable(e) for e in parse.events],
        }
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        print(f"wrote {len(parse.events)} events to {args.out}")

    if args.apply:
        from common.db import get_connection  # lazy: pyodbc only needed with --apply

        try:
            stats = load_events(get_connection(), parse, report_file)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(
            f"loaded: inserted={stats.inserted} "
            f"skipped_duplicates={stats.skipped_duplicates} "
            f"stub_matters_created={stats.stub_matters_created}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
