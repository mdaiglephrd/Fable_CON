"""Load one processed file into con.matter/con.document/con.document_text --
the third of the three independently-testable stages (enumerate / process /
load; see docs/07-tag-etl-runbook.md).

Reuses the existing loaders' shaping + MERGE logic directly rather than
reimplementing it: ingest.load_tags.shape_row/_write_shaped for
con.matter/con.document, ingest.load_document_text.shape_record/_write_shaped
for con.document_text. This module calls their private _write_shaped helpers
(not the public load_rows/load_texts wrappers) because those wrappers commit
on their own --batch-size, which doesn't fit "load one record, the caller
controls commit cadence" -- ingest/tag_orchestrate.py owns batching here, the
same way ingest/load_tags.py's own outer loop does for the tag export.

Idempotency ledger: con.tag_source_file, keyed by (path_hash, file_hash) --
mirrors the con.processed_blob pattern in functions/processing.py. Only a
'Succeeded' row blocks reprocessing; 'Failed'/'Unresolved' stay retryable
(a fixed bug, or an improved crosswalk match, should get another chance).

A file that the crosswalk could not resolve to an entry_id is never inserted
with an invented id -- con.document.entry_id is a NOT NULL primary key. It is
recorded in the ledger as 'Unresolved' and reported, never loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.file_identity import hash_path
from common.json_logging import configure_json_logging
from ingest import load_document_text, load_tags
from ingest.tag_process import ProcessedDocument

log = configure_json_logging(__name__)

STATUS_SUCCEEDED = "Succeeded"
STATUS_FAILED = "Failed"
STATUS_UNRESOLVED = "Unresolved"


@dataclass(frozen=True)
class LoadResult:
    status: str  # STATUS_SUCCEEDED | STATUS_FAILED | STATUS_UNRESOLVED
    entry_id: int | None
    docket_id: str | None
    detail: str | None


# --------------------------------------------------------------------------
# Idempotency ledger (con.tag_source_file)
# --------------------------------------------------------------------------


def already_succeeded(conn: Any, path_hash: str, file_hash: str) -> bool:
    """True when this exact (path, content) pair already loaded successfully."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM con.tag_source_file WHERE path_hash = ? AND file_hash = ?",
        (path_hash, file_hash),
    )
    row = cursor.fetchone()
    return row is not None and row[0] == STATUS_SUCCEEDED


def succeeded_source_keys(conn: Any) -> set[tuple[str, str]]:
    """All (path_hash, file_hash) pairs already loaded successfully.

    Preloaded once per orchestrator run so the resume skip-check is a set
    lookup instead of ~150K serial SELECTs (the same preload pattern as
    functions/processing.py::succeeded_keys)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT path_hash, file_hash FROM con.tag_source_file WHERE status = ?",
        (STATUS_SUCCEEDED,),
    )
    return {(row[0], row[1]) for row in cursor.fetchall()}


_RECORD_PROCESSED_SQL = """
MERGE con.tag_source_file AS t
USING (SELECT ? AS path_hash, ? AS file_hash) AS s
   ON t.path_hash = s.path_hash AND t.file_hash = s.file_hash
WHEN MATCHED THEN UPDATE SET
    file_path = ?, entry_id = ?, status = ?, detail = ?, processed_at = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT (path_hash, file_hash, file_path, entry_id, status, detail)
    VALUES (s.path_hash, s.file_hash, ?, ?, ?, ?);
"""


def record_processed(
    conn: Any,
    path_hash: str,
    file_hash: str,
    file_path: str,
    entry_id: int | None,
    status: str,
    detail: str | None,
) -> None:
    """Upsert the ledger row for one file. Caller commits."""
    conn.cursor().execute(
        _RECORD_PROCESSED_SQL,
        (
            path_hash, file_hash,
            file_path, entry_id, status, detail,
            file_path, entry_id, status, detail,
        ),
    )


def _warn_if_entry_id_already_loaded_from_other_file(
    conn: Any, doc: ProcessedDocument, path_hash: str
) -> None:
    """Fuzzy resolution can map two distinct files onto one entry_id; the
    later one silently last-wins on con.document. Surface it in the JSON log
    (one indexed query on IX_tag_source_file_entry_id) so a systematic
    crosswalk mis-match is visible instead of silent."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM con.tag_source_file"
        " WHERE entry_id = ? AND status = ? AND (path_hash <> ? OR file_hash <> ?)",
        (doc.entry_id, STATUS_SUCCEEDED, path_hash, doc.file_hash),
    )
    row = cursor.fetchone()
    if row is not None and row[0]:
        log.warning(
            "entry_id already loaded from a different file; this load overwrites it",
            extra={
                "entry_id": doc.entry_id,
                "file_path": str(doc.candidate.path),
                "prior_source_files": int(row[0]),
            },
        )


# --------------------------------------------------------------------------
# Shaping ProcessedDocument -> the existing loaders' row/record contracts
# --------------------------------------------------------------------------


def _applicant_from_index_path(index_path: str, docket_variants: tuple[str, ...]) -> str | None:
    """Best-effort applicant name from the matched index row's own path.

    The real on-disk SSD path is not reliable for this (paths don't fully
    match the index -- see ingest/tag_crosswalk.py), but the *matched index
    row's* Laserfiche path segment does reliably look like "<docket>
    <Applicant Name>" (e.g. "CON2005029 Saint Marys Health Care System Inc").
    """
    for segment in index_path.replace("/", "\\").split("\\"):
        upper = segment.upper()
        for variant in docket_variants:
            v = variant.upper()
            if upper.startswith(v):
                rest = segment[len(variant):].strip()
                return rest or None
    return None


def _to_tag_export_row(doc: ProcessedDocument) -> dict:
    """Shape a ProcessedDocument into the row shape ingest.load_tags.shape_row expects."""
    applicant = None
    if doc.match_candidates:
        applicant = _applicant_from_index_path(
            doc.match_candidates[0].index_row.path, doc.docket_variants
        )
    # OcrResult.confidence is 0-1 (OCR-engine score); con.document.ocr_confidence
    # is the repo's 0-100 scale (see docs/03: values like 97.5). document_text's
    # di_confidence keeps the 0-1 scale (docs/05: 0.98) -- see _to_text_record.
    ocr_confidence = None
    if doc.ocr_result is not None and doc.ocr_result.confidence is not None:
        ocr_confidence = round(doc.ocr_result.confidence * 100, 2)
    return {
        "entry_id": doc.entry_id,
        "docket_id": doc.docket_id,
        "docket_variants": list(doc.docket_variants),
        "applicant": applicant,
        "completeness_flags": ["stub_from_tag_etl"],
        "file_name": doc.candidate.path.name,
        "doc_type": doc.doc_type,
        "phase": doc.phase,
        "page_count": doc.ocr_result.page_count if doc.ocr_result else None,
        "source_path": str(doc.candidate.path),
        "ocr_status": doc.ocr_status,
        "ocr_confidence": ocr_confidence,
        "text_source": doc.ocr_result.text_source if doc.ocr_result else None,
    }


def _to_text_record(doc: ProcessedDocument) -> dict:
    """Shape a ProcessedDocument into the object ingest.load_document_text.shape_record expects."""
    assert doc.ocr_result is not None
    return {
        "entry_id": doc.entry_id,
        "full_text": doc.ocr_result.text,
        "text_source": doc.ocr_result.text_source,
        "di_model": doc.ocr_result.engine,
        "di_confidence": doc.ocr_result.confidence,
    }


# --------------------------------------------------------------------------
# load_one_record
# --------------------------------------------------------------------------


def load_one_record(conn: Any, doc: ProcessedDocument) -> LoadResult:
    """Upsert one processed document. Never raises; failures are captured and
    recorded in the ledger so the batch keeps going.

    Does not call conn.commit() -- ingest/tag_orchestrate.py commits every
    --batch-size records, the same convention ingest/load_tags.py's own
    load_rows() uses.
    """
    path_hash = hash_path(str(doc.candidate.path))

    if not doc.resolved:
        record_processed(
            conn, path_hash, doc.file_hash, str(doc.candidate.path), None,
            STATUS_UNRESOLVED, "crosswalk did not resolve an entry_id",
        )
        return LoadResult(STATUS_UNRESOLVED, None, doc.docket_id, "crosswalk unresolved")

    _warn_if_entry_id_already_loaded_from_other_file(conn, doc, path_hash)

    try:
        shaped = load_tags.shape_row(_to_tag_export_row(doc), row_number=1)
    except load_tags.RowRejected as exc:
        detail = str(exc)
        log.warning("tag export row rejected", extra={"file_path": str(doc.candidate.path), "error": detail})
        record_processed(
            conn, path_hash, doc.file_hash, str(doc.candidate.path), doc.entry_id,
            STATUS_FAILED, detail,
        )
        return LoadResult(STATUS_FAILED, doc.entry_id, doc.docket_id, detail)

    cursor = conn.cursor()
    load_tags._write_shaped(cursor, shaped, default_status="Unvalidated")

    text_note = None
    if doc.ocr_result is not None and doc.ocr_result.text.strip():
        try:
            shaped_text = load_document_text.shape_record(_to_text_record(doc), line_number=1)
        except load_document_text.RowRejected as exc:
            text_note = f"document_text not written: {exc}"
            log.warning(
                "document_text rejected", extra={"file_path": str(doc.candidate.path), "error": str(exc)}
            )
        else:
            load_document_text._write_shaped(cursor, shaped_text)

    record_processed(
        conn, path_hash, doc.file_hash, str(doc.candidate.path), doc.entry_id,
        STATUS_SUCCEEDED, text_note,
    )
    return LoadResult(STATUS_SUCCEEDED, doc.entry_id, doc.docket_id, text_note)
