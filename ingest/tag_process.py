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

from common.file_identity import hash_file
from common.json_logging import configure_json_logging
from ingest.tag_crosswalk import CrosswalkIndex, MatchCandidate, resolve_entry_id
from ingest.tag_enumerate import CandidateFile
from ingest.tag_ocr import NativeTextEngine, OcrEngine, OcrResult

log = configure_json_logging(__name__)

OCR_STATUS_SUCCEEDED = "Succeeded"
OCR_STATUS_FAILED = "Failed"


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

    ocr_status, ocr_result, error = _extract_text(candidate.path, engine)

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


def _extract_text(path: Path, engine: OcrEngine) -> tuple[str, OcrResult | None, str | None]:
    try:
        if path.suffix.lower() == ".pdf" and NativeTextEngine.has_native_text(path):
            result = NativeTextEngine().extract(path)
        else:
            result = engine.extract(path)
    except Exception as exc:  # one bad file must never abort the run
        log.warning("ocr failed", extra={"file_path": str(path), "error": str(exc)})
        return OCR_STATUS_FAILED, None, f"{type(exc).__name__}: {exc}"
    return OCR_STATUS_SUCCEEDED, result, None
