"""Docket normalization for GA DCH CON records.

Dockets appear in the wild as CON#######, CON-#######, DET..., LNR-...,
legacy GA-####### embedded in file names, and county-based legacy ids like
FULTON-213. This module produces a canonical docket_id plus the list of
variants under which the same docket may appear.

Canonical forms:
    CON-1234567        (CON application; also the target for legacy GA-1234567)
    DET-2020-014       (determination; internal digit groups joined by hyphens)
    LNR-2023-008       (letter of non-reviewability / LOI-series ids)
    FULTON-213         (county legacy; multi-word counties hyphenated: BEN-HILL-45)

ASSUMPTION: legacy GA-####### ids share the CON numbering space, so GA-1234567
canonicalizes to CON-1234567 (the GA form is kept as a variant). Flip
GA_MAPS_TO_CON if real data disproves this.
"""

import re
from dataclasses import dataclass

from common.vocab import COUNTIES

GA_MAPS_TO_CON = True

_SEP = r"[\s\-_.–]"  # separators seen between prefix and digits (incl. en-dash)

# Digit tail: 1-3 groups, e.g. "1234567" or "2020-014" or "04-21-003"
_TAIL = rf"(\d{{2,8}}(?:{_SEP}\d{{1,6}}){{0,2}})"

_CON_RE = re.compile(rf"(?<![A-Za-z0-9])CON{_SEP}?{_TAIL}(?!\d)", re.IGNORECASE)
# Determinations carry an optional subtype in the wild: DET-EQT2024-073 (equipment),
# DET-ASC2025-001 (physician-owned ambulatory surgery). Canonical keeps it:
# DET-EQT-2024-073.
_DET_RE = re.compile(
    rf"(?<![A-Za-z0-9])DET(?:{_SEP}?(EQT|ASC))?{_SEP}?{_TAIL}(?!\d)", re.IGNORECASE
)
# Letters of non-reviewability carry the same optional ASC/EQT subtype DET
# does (pre-2019 naming for what's now DET-ASC/DET-EQT): LNR-ASC2005006,
# LNR-EQT2005004. Canonical keeps it: LNR-ASC-2005006.
_LNR_RE = re.compile(
    rf"(?<![A-Za-z0-9])LNR(?:{_SEP}?(ASC|EQT))?{_SEP}?{_TAIL}(?!\d)", re.IGNORECASE
)
# Legacy GA ids: hyphen/underscore/period or directly attached (never a bare space,
# and 6-8 digits, so "Atlanta, GA 30303" style state+zip text can't match).
_GA_RE = re.compile(r"(?<![A-Za-z0-9])GA[\-_.]?(\d{6,8})(?!\d)", re.IGNORECASE)

# County alternation, longest first so CLAYTON wins over CLAY.
_COUNTY_ALT = "|".join(
    re.escape(c.upper()).replace(r"\ ", r"[\s\-_]") for c in sorted(COUNTIES, key=len, reverse=True)
)
# In free text a county docket needs a hard separator (FULTON-213); a bare space
# would false-positive on prose. normalize_docket() additionally tolerates spaces.
_COUNTY_EXTRACT_RE = re.compile(
    rf"(?<![A-Za-z0-9])({_COUNTY_ALT})[\-_.]+(\d{{1,4}})(?!\d)", re.IGNORECASE
)
_COUNTY_NORMALIZE_RE = re.compile(
    rf"(?<![A-Za-z0-9])({_COUNTY_ALT})[\s\-_.]+(\d{{1,4}})(?!\d)", re.IGNORECASE
)

_LABEL_NOISE_RE = re.compile(
    r"^(?:DOCKET|PROJECT|FILE|MATTER|CASE|NO\.?|NUMBER|NUM|ID|#|:|\s)+", re.IGNORECASE
)


@dataclass(frozen=True)
class DocketMatch:
    canonical: str
    kind: str  # 'CON' | 'DET' | 'LNR' | 'COUNTY'
    variants: tuple[str, ...]
    raw: str


def _canonical_tail(tail: str) -> str:
    """Join the digit groups of a matched tail with single hyphens."""
    return "-".join(re.split(_SEP + "+", tail.strip()))


def _prefix_match(
    prefix: str, tail: str, raw: str, *, kind: str | None = None, from_ga: bool = False
) -> DocketMatch | None:
    groups = re.split(_SEP + "+", tail.strip())
    is_det_or_lnr = prefix.startswith("DET") or prefix.startswith("LNR")
    # A single short digit group ("CON 21") is more likely prose than a docket.
    if len(groups) == 1 and len(groups[0]) < 4 and not is_det_or_lnr:
        return None
    if len(groups) == 1 and len(groups[0]) < 3:
        return None
    canon_tail = "-".join(groups)
    canonical = f"{prefix}-{canon_tail}"
    variants = {raw.strip(), canonical, f"{prefix}{canon_tail}"}
    if from_ga:
        variants.update({f"GA-{canon_tail}", f"GA{canon_tail}"})
    return DocketMatch(
        canonical=canonical,
        kind=kind or prefix,
        variants=tuple(sorted(variants)),
        raw=raw.strip(),
    )


def _county_match(county_raw: str, number: str, raw: str) -> DocketMatch:
    county_canon = re.sub(r"[\s_]+", "-", county_raw.strip().upper())
    canonical = f"{county_canon}-{number}"
    variants = {raw.strip(), canonical, f"{county_canon.replace('-', ' ')}-{number}"}
    return DocketMatch(
        canonical=canonical,
        kind="COUNTY",
        variants=tuple(sorted(variants)),
        raw=raw.strip(),
    )


def _match_at(text: str, county_re: re.Pattern) -> list[tuple[int, DocketMatch]]:
    """All docket matches in text with their start offsets."""
    out: list[tuple[int, DocketMatch]] = []
    for m in _CON_RE.finditer(text):
        dm = _prefix_match("CON", m.group(1), m.group(0))
        if dm:
            out.append((m.start(), dm))
    for m in _DET_RE.finditer(text):
        subtype = (m.group(1) or "").upper()
        prefix = f"DET-{subtype}" if subtype else "DET"
        dm = _prefix_match(prefix, m.group(2), m.group(0), kind="DET")
        if dm:
            out.append((m.start(), dm))
    for m in _LNR_RE.finditer(text):
        subtype = (m.group(1) or "").upper()
        prefix = f"LNR-{subtype}" if subtype else "LNR"
        dm = _prefix_match(prefix, m.group(2), m.group(0), kind="LNR")
        if dm:
            out.append((m.start(), dm))
    for m in _GA_RE.finditer(text):
        target = "CON" if GA_MAPS_TO_CON else "GA"
        dm = _prefix_match(target, m.group(1), m.group(0), from_ga=True)
        if dm:
            out.append((m.start(), dm))
    for m in county_re.finditer(text):
        out.append((m.start(), _county_match(m.group(1), m.group(2), m.group(0))))
    return out


def extract_dockets(text: str) -> list[DocketMatch]:
    """Scan free text (file names, report text) for docket references.

    Returns matches in order of first appearance, deduplicated by canonical id
    (variants merged across occurrences).
    """
    if not text:
        return []
    found = _match_at(text, _COUNTY_EXTRACT_RE)
    found.sort(key=lambda t: t[0])
    by_canonical: dict[str, DocketMatch] = {}
    for _, dm in found:
        prev = by_canonical.get(dm.canonical)
        if prev is None:
            by_canonical[dm.canonical] = dm
        else:
            merged = tuple(sorted(set(prev.variants) | set(dm.variants)))
            by_canonical[dm.canonical] = DocketMatch(prev.canonical, prev.kind, merged, prev.raw)
    return list(by_canonical.values())


def normalize_docket(raw: str) -> DocketMatch | None:
    """Normalize a string that is expected to BE a docket id.

    Tolerates label noise ("Docket No. CON-1234567") and trailing punctuation.
    Returns None when the string does not contain exactly one recognizable docket.
    """
    if not raw or not raw.strip():
        return None
    cleaned = _LABEL_NOISE_RE.sub("", raw.strip())
    cleaned = cleaned.strip(" \t:;,.()[]")
    if not cleaned:
        return None
    # Anchored attempt: the whole cleaned string is one docket.
    matches = _match_at(cleaned, _COUNTY_NORMALIZE_RE)
    for start, dm in matches:
        if start == 0 and dm.raw == cleaned:
            # Keep the original raw string as a variant too.
            variants = tuple(sorted(set(dm.variants) | {raw.strip()}))
            return DocketMatch(dm.canonical, dm.kind, variants, raw.strip())
    # Fallback: the string embeds exactly one docket (e.g. a file name).
    embedded = extract_dockets(cleaned)
    if len(embedded) == 1:
        dm = embedded[0]
        variants = tuple(sorted(set(dm.variants) | {raw.strip()}))
        return DocketMatch(dm.canonical, dm.kind, variants, raw.strip())
    return None
