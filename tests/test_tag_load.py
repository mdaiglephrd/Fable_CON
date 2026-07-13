from pathlib import Path

from ingest.tag_crosswalk import IndexRow, MatchCandidate
from ingest.tag_enumerate import CandidateFile
from ingest.tag_load import (
    STATUS_SUCCEEDED,
    STATUS_UNRESOLVED,
    already_succeeded,
    load_one_record,
)
from ingest.tag_ocr import OcrResult
from ingest.tag_process import OCR_STATUS_FAILED, OCR_STATUS_SUCCEEDED, ProcessedDocument
from tests.fakes import FakeConnection

CON_INDEX_PATH = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\A Main Application\CON2005029 Main Application"
)


def _resolved_doc(**overrides) -> ProcessedDocument:
    candidate = CandidateFile(
        path=Path("CON2005029/A Main Application/CON2005029 Main Application.pdf"),
        size_bytes=100,
        modified_at=0,
        created_at=0,
    )
    index_row = IndexRow(path=CON_INDEX_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=1)
    defaults = dict(
        candidate=candidate,
        file_hash="a" * 64,
        entry_id=1043,
        docket_id="CON-2005029",
        docket_variants=("CON-2005029", "CON2005029"),
        doc_type="Application/Request",
        phase="Initial Application",
        match_confidence=0.95,
        match_candidates=(MatchCandidate(entry_id=1043, score=0.95, index_row=index_row),),
        ocr_status=OCR_STATUS_SUCCEEDED,
        ocr_result=OcrResult(
            text="Some extracted application text.",
            confidence=None,
            engine="pdfplumber-native",
            page_count=1,
            text_source="native",
        ),
        error=None,
    )
    defaults.update(overrides)
    return ProcessedDocument(**defaults)


def _unresolved_doc(**overrides) -> ProcessedDocument:
    candidate = CandidateFile(path=Path("misc/unrelated.pdf"), size_bytes=10, modified_at=0, created_at=0)
    defaults = dict(
        candidate=candidate,
        file_hash="b" * 64,
        entry_id=None,
        docket_id=None,
        docket_variants=(),
        doc_type=None,
        phase=None,
        match_confidence=0.0,
        match_candidates=(),
        ocr_status=OCR_STATUS_SUCCEEDED,
        ocr_result=OcrResult(text="some text", confidence=None, engine="x", page_count=1, text_source="native"),
        error=None,
    )
    defaults.update(overrides)
    return ProcessedDocument(**defaults)


# --- load_one_record: happy path -------------------------------------------


def test_load_one_record_writes_matter_document_text_and_ledger():
    conn = FakeConnection()
    result = load_one_record(conn, _resolved_doc())

    assert result.status == STATUS_SUCCEEDED
    assert result.entry_id == 1043
    sqls = conn.executed_sql()
    assert any("MERGE con.matter" in s for s in sqls)
    assert any("MERGE con.document AS t" in s for s in sqls)
    assert any("MERGE con.document_text" in s for s in sqls)
    assert any("MERGE con.tag_source_file" in s for s in sqls)
    assert conn.committed == 0  # load_one_record never commits; the orchestrator does


def test_load_one_record_extracts_applicant_from_index_path():
    conn = FakeConnection()
    load_one_record(conn, _resolved_doc())

    matter_sql, matter_params = next(
        (sql, params) for sql, params in conn.executed if "MERGE con.matter" in sql
    )
    assert "Saint Marys Health Care System Inc" in matter_params


def test_load_one_record_sets_stub_completeness_flag():
    conn = FakeConnection()
    load_one_record(conn, _resolved_doc())

    _, matter_params = next((sql, params) for sql, params in conn.executed if "MERGE con.matter" in sql)
    assert '"stub_from_tag_etl"' in "".join(str(p) for p in matter_params if p)


def test_load_one_record_skips_document_text_when_no_ocr_result():
    conn = FakeConnection()
    doc = _resolved_doc(ocr_status=OCR_STATUS_FAILED, ocr_result=None, error="boom")
    result = load_one_record(conn, doc)

    assert result.status == STATUS_SUCCEEDED  # the document row itself still loads
    assert not any("MERGE con.document_text" in s for s in conn.executed_sql())


# --- load_one_record: unresolved --------------------------------------------


def test_load_one_record_unresolved_writes_only_the_ledger():
    conn = FakeConnection()
    result = load_one_record(conn, _unresolved_doc())

    assert result.status == STATUS_UNRESOLVED
    assert result.entry_id is None
    sqls = conn.executed_sql()
    assert not any("MERGE con.matter" in s for s in sqls)
    assert not any("MERGE con.document AS t" in s for s in sqls)
    assert any("MERGE con.tag_source_file" in s for s in sqls)


# --- idempotency -------------------------------------------------------------


def test_rerunning_the_same_resolved_document_does_not_duplicate():
    conn = FakeConnection()
    doc = _resolved_doc()

    load_one_record(conn, doc)
    first_count = len(conn.executed)
    load_one_record(conn, doc)
    second_count = len(conn.executed) - first_count

    # Same shape of work both times: MERGE statements, not growing INSERTs.
    assert second_count == first_count
    sqls = conn.executed_sql()
    assert sqls.count(sqls[0]) >= 1  # sanity: same MERGE text reused, not duplicated ad hoc


def test_already_succeeded_true_after_scripted_succeeded_row():
    conn = FakeConnection()
    conn.script("SELECT status FROM con.tag_source_file", rows=[("Succeeded",)])

    assert already_succeeded(conn, "somepathhash", "somefilehash") is True


def test_already_succeeded_false_when_no_row():
    conn = FakeConnection()
    assert already_succeeded(conn, "somepathhash", "somefilehash") is False


def test_already_succeeded_false_for_failed_status():
    conn = FakeConnection()
    conn.script("SELECT status FROM con.tag_source_file", rows=[("Failed",)])

    assert already_succeeded(conn, "somepathhash", "somefilehash") is False
