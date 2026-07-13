import csv
import io

import pytest
from reportlab.pdfgen import canvas

from common.file_identity import hash_file, hash_path
from ingest.tag_crosswalk import CrosswalkIndex, IndexRow
from ingest.tag_orchestrate import run
from ingest.tag_ocr import OpenOcrEngine
from tests.fakes import FakeConnection

CON_PATH = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\A Main Application\CON2005029 Main Application"
)


class _FakeEngine:
    def extract(self, path):
        raise AssertionError("OCR engine should not be called for a native-text PDF")


def _make_native_pdf(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    c.drawString(100, 700, text)
    c.save()


def _index_with_one_row():
    return CrosswalkIndex(
        [IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=1)]
    )


def test_dry_run_does_not_touch_db_or_read_file_contents(tmp_path, monkeypatch):
    pdf = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf, "Application text for CON2005029.")

    def forbidden_hash(path):
        raise AssertionError("dry run must not read file contents")

    monkeypatch.setattr("ingest.tag_orchestrate.hash_file", forbidden_hash)

    conn = FakeConnection()
    stats = run(conn, tmp_path, _index_with_one_row(), _FakeEngine(), apply=False)

    assert stats.seen == 1
    assert stats.total_bytes > 0
    assert stats.loaded == 0
    assert conn.executed == []
    assert conn.committed == 0


def test_apply_loads_a_resolved_document(tmp_path):
    pdf = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf, "Application text long enough to count as real content for CON2005029.")

    conn = FakeConnection()
    stats = run(conn, tmp_path, _index_with_one_row(), _FakeEngine(), apply=True, batch_size=500)

    assert stats.seen == 1
    assert stats.loaded == 1
    assert stats.unresolved == 0
    assert conn.committed == 1  # final flush of a partial batch
    assert any("MERGE con.document AS t" in s for s in conn.executed_sql())


def test_apply_skips_already_succeeded_files_via_preloaded_keys(tmp_path):
    pdf = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf, "Application text for CON2005029, already loaded previously.")

    conn = FakeConnection()
    # The preload query returns this exact file's ledger key.
    conn.script(
        "SELECT path_hash, file_hash FROM con.tag_source_file",
        rows=[(hash_path(str(pdf)), hash_file(pdf))],
    )

    stats = run(conn, tmp_path, _index_with_one_row(), _FakeEngine(), apply=True)

    assert stats.skipped_already_done == 1
    assert stats.loaded == 0
    assert not any("MERGE con.document AS t" in s for s in conn.executed_sql())
    # Exactly one ledger query for the whole run (the preload), not one per file.
    ledger_queries = [s for s in conn.executed_sql() if "con.tag_source_file" in s]
    assert len(ledger_queries) == 1


def test_apply_writes_unresolved_files_to_rejects(tmp_path):
    pdf = tmp_path / "misc" / "unrelated_file.pdf"
    _make_native_pdf(pdf, "Content with no docket id anywhere in this path or text.")

    conn = FakeConnection()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["file_path", "docket_id", "detail", "confidence"])

    stats = run(conn, tmp_path, CrosswalkIndex([]), _FakeEngine(), apply=True, rejects_writer=writer)

    assert stats.unresolved == 1
    lines = buf.getvalue().splitlines()
    assert "unrelated_file.pdf" in lines[1]
    assert "crosswalk unresolved" in lines[1]


def test_commits_happen_every_batch_size_documents(tmp_path):
    for i in range(3):
        pdf = tmp_path / f"CON200500{i}" / "A Main Application" / f"CON200500{i} Main Application.pdf"
        _make_native_pdf(pdf, f"Application text {i} that is long enough to be real content.")

    index = CrosswalkIndex(
        [
            IndexRow(
                path=CON_PATH.replace("2005029", f"200500{i}"),
                name=f"CON200500{i} Main Application",
                entry_id=1000 + i,
                page_count=1,
            )
            for i in range(3)
        ]
    )
    conn = FakeConnection()
    stats = run(conn, tmp_path, index, _FakeEngine(), apply=True, batch_size=1)

    assert stats.loaded == 3
    assert stats.commits == 3


# --- --workers (multiprocessing) ----------------------------------------------


def test_workers_requires_index_path(tmp_path):
    conn = FakeConnection()
    with pytest.raises(ValueError, match="index_path"):
        run(conn, tmp_path, _index_with_one_row(), OpenOcrEngine(), apply=True, workers=2)


def test_workers_requires_openocr_engine(tmp_path):
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OpenOCR engine"):
        run(
            conn, tmp_path, _index_with_one_row(), _FakeEngine(),
            apply=True, workers=2, index_path=tmp_path / "index.xlsx",
        )


def test_workers_parallel_run_loads_native_pdfs(tmp_path):
    # Real spawn-context pool: 3 native-text PDFs (no OCR model needed) and a
    # real xlsx index each worker loads in its initializer. The parent's
    # FakeConnection stays the single writer.
    import openpyxl

    for i in range(3):
        pdf = tmp_path / "ssd" / f"CON200500{i}" / "A Main Application" / f"CON200500{i} Main Application"
        _make_native_pdf(pdf, f"Application text {i} long enough to count as real page content.")

    index_path = tmp_path / "index.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Path", "Name", "Type", "Entry ID", "Page Count"])
    for i in range(3):
        ws.append(
            [
                CON_PATH.replace("2005029", f"200500{i}"),
                f"CON200500{i} Main Application",
                "document",
                1000 + i,
                1,
            ]
        )
    wb.save(index_path)

    conn = FakeConnection()
    stats = run(
        conn,
        tmp_path / "ssd",
        CrosswalkIndex([]),  # parent copy unused by workers; they load index_path
        OpenOcrEngine(),
        apply=True,
        batch_size=500,
        workers=2,
        index_path=index_path,
    )

    assert stats.seen == 3
    assert stats.loaded == 3
    assert stats.failed == 0
    assert conn.committed == 1
    doc_merges = [s for s in conn.executed_sql() if "MERGE con.document AS t" in s]
    assert len(doc_merges) == 3
