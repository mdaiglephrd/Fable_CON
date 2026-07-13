import csv
import io

from reportlab.pdfgen import canvas

from ingest.tag_crosswalk import CrosswalkIndex, IndexRow
from ingest.tag_orchestrate import run
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


def test_dry_run_does_not_touch_db_or_run_ocr(tmp_path):
    pdf = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf, "Application text for CON2005029.")

    conn = FakeConnection()
    stats = run(conn, tmp_path, _index_with_one_row(), _FakeEngine(), apply=False)

    assert stats.seen == 1
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


def test_apply_skips_already_succeeded_files(tmp_path):
    pdf = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf, "Application text for CON2005029, already loaded previously.")

    conn = FakeConnection()
    conn.script("SELECT status FROM con.tag_source_file", rows=[("Succeeded",)])

    stats = run(conn, tmp_path, _index_with_one_row(), _FakeEngine(), apply=True)

    assert stats.skipped_already_done == 1
    assert stats.loaded == 0
    assert not any("MERGE con.document AS t" in s for s in conn.executed_sql())


def test_apply_writes_unresolved_files_to_rejects(tmp_path):
    pdf = tmp_path / "misc" / "unrelated_file.pdf"
    _make_native_pdf(pdf, "Content with no docket id anywhere in this path or text.")

    conn = FakeConnection()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["file_path", "docket_id", "detail_or_confidence"])

    stats = run(conn, tmp_path, CrosswalkIndex([]), _FakeEngine(), apply=True, rejects_writer=writer)

    assert stats.unresolved == 1
    assert "unrelated_file.pdf" in buf.getvalue()


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
