"""Process one candidate file: resolve its identity via the crosswalk and
extract its text -- the second of the three independently-testable stages
(enumerate / process / load; see docs/07-tag-etl-runbook.md).

Pure given an OcrEngine + CrosswalkIndex: no DB. Always returns a
ProcessedDocument (OCR success or failure, crosswalk resolved or not) rather
than raising -- one bad or unmatched file must never abort a
150,000-document run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from common.file_identity import (
    KIND_HTML,
    KIND_IMAGE,
    KIND_PDF,
    KIND_TEXT,
    hash_file,
    sniff_type,
)
from common.json_logging import configure_json_logging
from ingest.tag_crosswalk import CrosswalkIndex, MatchCandidate, resolve_entry_id, should_attempt_ocr
from ingest.tag_enumerate import CandidateFile
from ingest.tag_ocr import (
    NativeTextEngine,
    OcrEngine,
    OcrResult,
    extract_html_text,
    extract_plain_text,
)

log = configure_json_logging(__name__)

OCR_STATUS_SUCCEEDED = "Succeeded"
OCR_STATUS_FAILED = "Failed"
OCR_STATUS_SKIPPED = "Skipped"

# doc_type values (from ingest.tag_crosswalk._FOLDER_DOC_TYPE_PHASE) that get
# full OCR: precedential authority documents plus Applications. Everything
# else still gets a con.document row (entry_id, docket, doc_type, phase --
# the crosswalk match doesn't depend on this), just no con.document_text from
# the expensive OCR engine call. A PDF that already has a native text layer
# still gets that text for free regardless of doc_type -- this only gates
# the OpenOCR call itself, not the free native-text check.
OCR_QUALIFYING_DOC_TYPES = frozenset(
    {
        "Application/Request",
        "Decision/Determination",
        "Hearing Officer Decision",
        "Final Agency Decision",
        "Court Order/Opinion",
    }
)


@dataclass(frozen=True)
class ProcessedDocument:
    candidate: CandidateFile
    file_hash: str
    entry_id: int | None
    docket_id: str | None
    docket_variants: tuple[str, ...]
    doc_type: str | None
    phase: str | None
    match_confidence: float
    match_candidates: tuple[MatchCandidate, ...]
    ocr_status: str
    ocr_result: OcrResult | None
    error: str | None

    @property
    def resolved(self) -> bool:
        return self.entry_id is not None


def process_one_file(
    candidate: CandidateFile, engine: OcrEngine, index: CrosswalkIndex
) -> ProcessedDocument:
    """Extract text and resolve Laserfiche identity for one file. Never raises."""
    file_hash = hash_file(candidate.path)
    match = resolve_entry_id(candidate.path, index)

    # match.doc_type is set from the real on-disk folder position regardless
    # of whether the crosswalk itself resolved an entry_id -- so this gate is
    # available even for files that end up Unresolved. should_attempt_ocr
    # applies a finer filename-level rule within that already-qualifying set
    # (see ingest.tag_crosswalk for why: Master File bundles, appendices,
    # and litigation-support material in appeal-stage folders all share a
    # doc_type with content that genuinely should be OCR'd).
    allow_ocr = match.doc_type in OCR_QUALIFYING_DOC_TYPES and should_attempt_ocr(candidate.path.parts)
    ocr_status, ocr_result, error = _extract_text(candidate.path, engine, allow_ocr=allow_ocr)

    if match.unresolved and ocr_result is not None and ocr_result.page_count is not None:
        # A "soft cross-check" retry: the operator-supplied index's Page
        # Count column can break an otherwise-ambiguous near-tie once the
        # real page count is known. This never blocks loading on its own --
        # it only helps resolve_entry_id decide between close candidates.
        match = resolve_entry_id(candidate.path, index, actual_page_count=ocr_result.page_count)

    if match.unresolved:
        log.warning(
            "crosswalk unresolved",
            extra={
                "file_path": str(candidate.path),
                "docket_id": match.docket_id,
                "confidence": match.confidence,
                "candidate_count": len(match.candidates),
            },
        )

    return ProcessedDocument(
        candidate=candidate,
        file_hash=file_hash,
        entry_id=match.entry_id,
        docket_id=match.docket_id,
        docket_variants=match.docket_variants,
        doc_type=match.doc_type,
        phase=match.phase,
        match_confidence=match.confidence,
        match_candidates=match.candidates,
        ocr_status=ocr_status,
        ocr_result=ocr_result,
        error=error,
    )


def _extract_text(
    path: Path, engine: OcrEngine, *, allow_ocr: bool = True
) -> tuple[str, OcrResult | None, str | None]:
    """Route by sniffed content kind (the corpus is mostly extension-less):
    pdf -> native text layer when present, else OCR (if allow_ocr); image ->
    OCR (if allow_ocr); text/html -> direct read; unknown -> Failed, no OCR
    attempt. allow_ocr=False only skips the expensive engine.extract() call --
    a PDF with a native text layer is still extracted for free either way."""
    try:
        kind = sniff_type(path)
        if kind == KIND_PDF:
            native = NativeTextEngine.extract_if_native(path)
            if native is not None:
                result = native
            elif not allow_ocr:
                return OCR_STATUS_SKIPPED, None, "doc_type not in OCR scope"
            else:
                result = engine.extract(path)
        elif kind == KIND_IMAGE:
            if not allow_ocr:
                return OCR_STATUS_SKIPPED, None, "doc_type not in OCR scope"
            result = engine.extract(path)
        elif kind == KIND_TEXT:
            result = extract_plain_text(path)
        elif kind == KIND_HTML:
            result = extract_html_text(path)
        else:
            log.warning("unsupported file type", extra={"file_path": str(path), "kind": kind})
            return OCR_STATUS_FAILED, None, f"unsupported file type (sniffed: {kind})"
    except Exception as exc:  # one bad file must never abort the run
        log.warning("ocr failed", extra={"file_path": str(path), "error": str(exc)})
        return OCR_STATUS_FAILED, None, f"{type(exc).__name__}: {exc}"
    return OCR_STATUS_SUCCEEDED, result, None
