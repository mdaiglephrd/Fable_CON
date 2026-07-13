"""Docket-family classification for the CON research layer.

Maps a docket id (or any of its variants) onto one of the controlled
``vocab.DOCKET_FAMILIES`` codes used across the research console:

    CON, DET, DET-EQT, DET-ASC, LNR-ASC, LNR-EQT

Rules (DESIGN.md, RESEARCH LAYER -> common/docket_family.py):
    * LNR-ASC / LNR-EQT   -> by prefix.
    * DET-EQT / DET-ASC   -> by determination subtype (see docket.DocketMatch).
    * plain DET           -> 'DET'.
    * CON-* / county / GA-legacy -> 'CON'.

A bare ``LNR`` with no subtype is a Letter of Non-Reviewability routed through
the determination workflow, so it classifies as the generic 'DET' family (the
family vocabulary has no plain 'LNR' code). Pure: no I/O.
"""

import re

from common.docket import normalize_docket

# Collapse any run of docket separators (space, underscore, period, hyphen,
# en-dash) into a single hyphen so prefix tests work on raw and canonical forms.
_SEP_RUN = re.compile(r"[\s._–\-]+")

# Generic DET/LNR prefix: the token must be followed by a separator, a digit,
# or end-of-string so plain words like "DETROIT" do not match.
_GENERIC_DET = re.compile(r"^(?:DET|LNR)(?:-|\d|$)")

_SUBTYPE_PREFIXES = ("LNR-ASC", "LNR-EQT", "DET-ASC", "DET-EQT")


def classify_family(docket_like: str) -> str:
    """Classify a docket id / variant into one of ``vocab.DOCKET_FAMILIES``.

    Accepts canonical ids ("DET-EQT-2024-073"), raw forms ("DET-EQT2024-073",
    "LNR-ASC2026002"), CON ids, county-legacy ids, and GA-legacy ids. Anything
    unrecognized falls back to 'CON'.
    """
    if not docket_like or not docket_like.strip():
        return "CON"

    compact = _SEP_RUN.sub("-", docket_like.strip().upper())

    # Prefer the shared normalizer's canonical form (it preserves DET/LNR
    # subtypes and folds GA-legacy into CON); fall back to the compacted raw
    # string in case normalization fails for some other reason.
    candidates = [compact]
    dm = normalize_docket(docket_like)
    if dm is not None:
        candidates.insert(0, dm.canonical.upper())

    for cand in candidates:
        for prefix in _SUBTYPE_PREFIXES:
            if cand.startswith(prefix):
                return prefix

    for cand in candidates:
        if _GENERIC_DET.match(cand):
            return "DET"

    return "CON"
