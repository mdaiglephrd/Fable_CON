"""Crosswalk between real on-disk SSD files and the Laserfiche document index.

The operator-supplied index spreadsheet (Path, Name, Type, Entry ID, Page
Count) predates and does not exactly match the real on-disk file layout --
confirmed with the operator: real folders mirror the index's hierarchy
loosely (renamed/flattened segments, drift). Resolving a physical file back
to its Laserfiche Entry ID therefore needs a fuzzy match, not an exact path
join. con.document.entry_id is a NOT NULL primary key, so a file that cannot
be resolved with reasonable confidence is never assigned an invented id --
see MatchResult.unresolved and ingest/tag_load.py.

This module also carries the folder-position -> doc_type/phase mapping
(infer_doc_type_phase), grounded in the real folder names found in the index
during discovery (e.g. "A Main Application", "B Appendices", "1 Determination
File"). It is isolated as an editable table so recalibrating against more
real data is a table edit, not a rewrite -- the same pattern
ingest/weekly_report_parser.py already uses for its section-header tables.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from common.docket import DocketMatch, extract_dockets

# --- index rows --------------------------------------------------------------


@dataclass(frozen=True)
class IndexRow:
    path: str  # Laserfiche virtual path, backslash-separated, as given in the index
    name: str  # Laserfiche document title/name
    entry_id: int
    page_count: int | None


@dataclass(frozen=True)
class MatchCandidate:
    entry_id: int
    score: float
    index_row: IndexRow


@dataclass(frozen=True)
class MatchResult:
    entry_id: int | None
    docket_id: str | None
    docket_variants: tuple[str, ...]
    doc_type: str | None
    phase: str | None
    confidence: float
    candidates: tuple[MatchCandidate, ...]  # top candidates considered; for the rejects report

    @property
    def unresolved(self) -> bool:
        return self.entry_id is None


# --- index loading ------------------------------------------------------------


class CrosswalkIndex:
    """In-memory lookup of IndexRow grouped by docket id for fast narrowing.

    137K rows is trivial to hold in memory -- the same budget precedent
    ingest/index_diff.py already sets by holding a full ~1M-row Laserfiche
    snapshot in memory on its OLD side.
    """

    def __init__(self, rows: list[IndexRow]):
        self._by_docket: dict[str, list[IndexRow]] = {}
        self._all = rows
        for row in rows:
            docket = _docket_of_row(row)
            if docket:
                self._by_docket.setdefault(docket, []).append(row)

    def candidates_for_docket(self, docket_id: str) -> list[IndexRow]:
        return self._by_docket.get(docket_id, [])

    def __len__(self) -> int:
        return len(self._all)


def _docket_of_row(row: IndexRow) -> str | None:
    matches = extract_dockets(row.path)
    return matches[0].canonical if matches else None


def load_index(index_path: Path) -> CrosswalkIndex:
    """Load the operator-supplied Path/Name/Type/Entry ID/Page Count index (.xlsx)."""
    import openpyxl  # lazy: only this one-time load needs it

    workbook = openpyxl.load_workbook(index_path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows: list[IndexRow] = []
    row_iter = worksheet.iter_rows(values_only=True)
    next(row_iter, None)  # header: Path, Name, Type, Entry ID, Page Count
    for path, name, _doc_type, entry_id, page_count in row_iter:
        if entry_id is None or path is None:
            continue
        rows.append(
            IndexRow(
                path=str(path),
                name=str(name) if name is not None else "",
                entry_id=int(entry_id),
                page_count=int(page_count) if isinstance(page_count, (int, float)) else None,
            )
        )
    return CrosswalkIndex(rows)


# --- doc_type / phase inference from folder position --------------------------

# Folder name (case-insensitive, ordering-prefix-stripped) two levels above a
# file -> (doc_type, phase). doc_type values are con.vocab_doc_type codes;
# phase values are con.vocab_phase codes -- both already exist in the schema.
_FOLDER_DOC_TYPE_PHASE: dict[str, tuple[str, str]] = {
    "main application": ("Application/Request", "Initial Application"),
    "appendices": ("Application/Request", "Initial Application"),
    "acknowledgement & completeness": ("Notice", "Initial Application"),
    "60 day meeting": ("Notice", "Initial Application"),
    "additional info & amendment": ("Application/Request", "Initial Application"),
    "letters of support": ("Correspondence", "Initial Application"),
    "letters of opposition": ("Correspondence", "Initial Application"),
    "extension of review": ("Notice", "Initial Application"),
    "withdrawal correspondence": ("Correspondence", "Initial Application"),
    "decision": ("Decision/Determination", "Initial Application"),
    "public notices": ("Notice", "Initial Application"),
    "other": ("Other", "Initial Application"),
    "evaluation": ("Decision/Determination", "Initial Application"),
    "determination file": ("Decision/Determination", "Initial Application"),
    "initial hearing officer appeal": ("Hearing Officer Decision", "Administrative Appeal"),
    "apa appeal": ("Hearing Officer Decision", "Administrative Appeal"),
    "commissioner review": ("Final Agency Decision", "Administrative Appeal"),
    "judicial review": ("Court Order/Opinion", "Judicial Review – Superior Court"),
    "post-approval files": ("Correspondence", "Initial Application"),
    "status reporting": ("Correspondence", "Initial Application"),
    "review board": ("Hearing Officer Decision", "Administrative Appeal"),
    "challenger correspondence": ("Correspondence", "Administrative Appeal"),
    "department correspondence": ("Correspondence", "Initial Application"),
    "respondent correspondence": ("Correspondence", "Administrative Appeal"),
}

_ORDERING_PREFIX_RE = re.compile(r"^(?:[\dA-Za-z](?:\.\d+)*)\s+")


def _strip_ordering_prefix(name: str) -> str:
    return _ORDERING_PREFIX_RE.sub("", name).strip()


def infer_doc_type_phase(path_parts: Sequence[str]) -> tuple[str | None, str | None]:
    """Best-effort (doc_type, phase) from the folder two levels above a file.

    path_parts is the sequence of folder names from root to (and excluding)
    the file itself. Matching strips a leading ordering prefix ("1 ", "A ",
    "2.1 ", etc.) and is case-insensitive. Returns (None, None) when the
    folder isn't in the table -- callers must treat that as "unknown," not
    "Other" (only a human, or a future recalibration of this table, decides
    that).
    """
    if len(path_parts) < 2:
        return (None, None)
    candidate = _strip_ordering_prefix(path_parts[-2]).lower()
    return _FOLDER_DOC_TYPE_PHASE.get(candidate, (None, None))


# --- filename-level OCR refinement --------------------------------------------
#
# infer_doc_type_phase's folder-position gate is necessarily broad -- a whole
# folder gets one doc_type. For several folders that's too broad for OCR
# purposes specifically: "A Main Application" also picks up combined
# Master File/Bates-numbered bundles that happen to sit in that same folder
# position, "B Appendices" is part of the application but explicitly not
# wanted for OCR, and the appeal-stage folders (Hearing Officer/Commissioner/
# Judicial Review/Review Board) are mostly litigation support material
# (discovery, briefs, exhibits, depositions) with the actual order/decision
# buried among a few hundred other files.
#
# This does NOT relabel doc_type -- an appendix file is still tagged
# Application/Request for search/browse purposes, it just doesn't get the
# expensive OCR call. tag_process.OCR_QUALIFYING_DOC_TYPES remains the first
# gate; this is a second, finer one applied only within that already-
# qualifying set.

_DECISION_KEYWORDS_RE = re.compile(
    r"(order|decision|findings of fact|opinion|final order|certificate)", re.IGNORECASE
)
_EXCLUDE_MARKER_RE = re.compile(r"(duplicate|proposed|draft)", re.IGNORECASE)

_APPEAL_STAGE_FOLDERS = frozenset(
    {
        "initial hearing officer appeal",
        "apa appeal",
        "commissioner review",
        "judicial review",
        "review board",
    }
)


def should_attempt_ocr(path_parts: Sequence[str]) -> bool:
    """Filename-level refinement on top of the doc_type gate, for folders
    where folder position alone over- or under-includes relative to what's
    actually wanted for OCR. Returns True (no additional restriction) for any
    folder not explicitly listed here -- this only narrows within folders
    known to need it, it never widens beyond infer_doc_type_phase's gate.
    """
    if len(path_parts) < 2:
        return True
    folder = _strip_ordering_prefix(path_parts[-2]).lower()
    fname = path_parts[-1].lower()

    if folder == "main application":
        return "main application" in fname and "master file" not in fname and "bates" not in fname
    if folder == "appendices":
        return False
    if folder == "decision":
        return ("decision" in fname or "letter" in fname) and "certificate" not in fname
    if folder == "evaluation":
        return "request" in fname or "response" in fname or "additional info" in fname
    if folder in _APPEAL_STAGE_FOLDERS:
        if _EXCLUDE_MARKER_RE.search(fname):
            return False
        return bool(_DECISION_KEYWORDS_RE.search(fname))
    return True


# --- fuzzy resolution ----------------------------------------------------------

MATCH_THRESHOLD = 0.55
AMBIGUITY_MARGIN = 0.08
# Deliberately larger than AMBIGUITY_MARGIN: a confirmed page-count match must
# be able to decisively break a near-tie between two similarly-named
# candidates, not just nudge it. Confidence scores can exceed 1.0 when this
# bonus stacks on an already-high name-similarity score -- it's an internal
# ranking value, not a probability.
_PAGE_COUNT_BONUS = 0.15
_MAX_CANDIDATES = 5


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _strip_docket(text: str, variants: tuple[str, ...]) -> str:
    """Remove the docket id from a name before similarity scoring.

    Every file and index row inside one docket's subtree shares the docket id
    in its name, which inflates similarity between otherwise-unrelated names
    ("DET2005018 Notes" vs "DET2005018 Determin Request" scores high purely
    on the shared prefix). Scoring the distinctive remainder prevents that
    false-positive class; when stripping leaves nothing (a file named exactly
    the docket id), the caller falls back to the unstripped strings.
    """
    for variant in sorted(variants, key=len, reverse=True):
        text = text.replace(variant.lower(), " ")
    return " ".join(text.split())


def _score(
    file_stem: str, row: IndexRow, actual_page_count: int | None, variants: tuple[str, ...]
) -> float:
    stem_stripped = _strip_docket(file_stem, variants)
    name_stripped = _strip_docket(row.name.lower(), variants)
    if stem_stripped and name_stripped:
        score = _similarity(stem_stripped, name_stripped)
    else:
        score = _similarity(file_stem, row.name.lower())
    if actual_page_count is not None and row.page_count is not None and row.page_count == actual_page_count:
        score += _PAGE_COUNT_BONUS
    return score


def resolve_entry_id(
    file_path: Path,
    index: CrosswalkIndex,
    *,
    docket: DocketMatch | None = None,
    actual_page_count: int | None = None,
) -> MatchResult:
    """Resolve a real on-disk file to its Laserfiche Entry ID via the crosswalk.

    Narrows to the candidate's docket subtree (from `docket`, or extracted
    from `file_path` when not given), then scores each candidate index row's
    Name against the real file's stem with difflib, with a small bonus when
    an already-known actual page count matches the index row's. Returns the
    top match only when its score clears MATCH_THRESHOLD and isn't a
    near-tie with the runner-up (within AMBIGUITY_MARGIN); otherwise
    unresolved, with the top candidates attached for a --rejects report.
    """
    if docket is None:
        found = extract_dockets(str(file_path))
        docket = found[0] if found else None

    doc_type, phase = infer_doc_type_phase(file_path.parts)

    if docket is None:
        return MatchResult(None, None, (), doc_type, phase, 0.0, ())

    rows = index.candidates_for_docket(docket.canonical)
    if not rows:
        return MatchResult(None, docket.canonical, docket.variants, doc_type, phase, 0.0, ())

    stem = file_path.stem.lower()
    scored = sorted(
        (
            MatchCandidate(
                entry_id=row.entry_id,
                score=_score(stem, row, actual_page_count, docket.variants),
                index_row=row,
            )
            for row in rows
        ),
        key=lambda c: c.score,
        reverse=True,
    )
    top = tuple(scored[:_MAX_CANDIDATES])

    if not top or top[0].score < MATCH_THRESHOLD:
        confidence = top[0].score if top else 0.0
        return MatchResult(None, docket.canonical, docket.variants, doc_type, phase, confidence, top)

    if len(top) > 1 and (top[0].score - top[1].score) < AMBIGUITY_MARGIN:
        return MatchResult(None, docket.canonical, docket.variants, doc_type, phase, top[0].score, top)

    best = top[0]
    return MatchResult(
        entry_id=best.entry_id,
        docket_id=docket.canonical,
        docket_variants=docket.variants,
        doc_type=doc_type,
        phase=phase,
        confidence=best.score,
        candidates=top,
    )
