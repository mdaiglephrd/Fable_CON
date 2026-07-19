from pathlib import Path

from reportlab.pdfgen import canvas

from ingest.tag_crosswalk import CrosswalkIndex, IndexRow
from ingest.tag_enumerate import CandidateFile
from ingest.tag_ocr import OcrResult
from ingest.tag_process import (
    OCR_STATUS_FAILED,
    OCR_STATUS_SKIPPED,
    OCR_STATUS_SUCCEEDED,
    process_one_file,
)

CON_PATH = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\A Main Application\CON2005029 Main Application"
)


class _FakeEngine:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc
        self.calls = []

    def extract(self, path):
        self.calls.append(path)
        if self._exc is not None:
            raise self._exc
        return self._result


def _candidate(path: Path) -> CandidateFile:
    stat = path.stat()
    return CandidateFile(path=path, size_bytes=stat.st_size, modified_at=stat.st_mtime, created_at=stat.st_ctime)


def _make_native_pdf(path: Path, text: str) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(100, 700, text)
    c.save()


def _make_fake_jpeg(path: Path) -> None:
    # JPEG magic bytes so sniff_type routes it to the OCR engine.
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)


def test_resolves_and_extracts_native_pdf(tmp_path):
    pdf_dir = tmp_path / "CON2005029" / "A Main Application"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "CON2005029 Main Application.pdf"
    _make_native_pdf(pdf_path, "Application body text, plenty of it, for CON2005029 review purposes.")

    index = CrosswalkIndex(
        [IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=1)]
    )
    fake_engine = _FakeEngine()  # should not be called: native text wins
    doc = process_one_file(_candidate(pdf_path), fake_engine, index)

    assert doc.resolved
    assert doc.entry_id == 1043
    assert doc.docket_id == "CON-2005029"
    assert doc.ocr_status == OCR_STATUS_SUCCEEDED
    assert doc.ocr_result.text_source == "native"
    assert fake_engine.calls == []  # native path never touched the injected engine


def test_falls_back_to_injected_engine_for_image(tmp_path):
    image_dir = tmp_path / "CON2005029" / "A Main Application"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "CON2005029 Main Application.jpg"
    _make_fake_jpeg(image_path)

    index = CrosswalkIndex(
        [IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=1)]
    )
    fake_result = OcrResult(text="ocr'd text", confidence=0.9, engine="fake", page_count=1, text_source="ocr")
    fake_engine = _FakeEngine(result=fake_result)

    doc = process_one_file(_candidate(image_path), fake_engine, index)

    assert doc.resolved
    assert doc.ocr_status == OCR_STATUS_SUCCEEDED
    assert doc.ocr_result is fake_result
    assert fake_engine.calls == [image_path]


def test_unresolved_when_no_docket_in_path(tmp_path):
    path = tmp_path / "misc" / "unrelated_file.pdf"
    path.parent.mkdir(parents=True)
    _make_native_pdf(path, "some unrelated content")

    index = CrosswalkIndex([])
    doc = process_one_file(_candidate(path), _FakeEngine(), index)

    assert not doc.resolved
    assert doc.entry_id is None
    assert doc.ocr_status == OCR_STATUS_SUCCEEDED  # extraction itself still worked


def test_ocr_failure_is_captured_not_raised(tmp_path):
    # Under a qualifying folder+filename ("Main Application" -> allowed by
    # both the doc_type gate and should_attempt_ocr) so this exercises the
    # engine actually being invoked and failing, not either OCR-scope gate.
    # ("B Appendices" no longer works here -- appendices never get OCR'd now,
    # see test_appendices_never_get_ocr_regardless_of_filename.)
    image_path = tmp_path / "CON2005029" / "A Main Application" / "CON2005029 Main Application.jpg"
    image_path.parent.mkdir(parents=True)
    _make_fake_jpeg(image_path)

    index = CrosswalkIndex([])
    fake_engine = _FakeEngine(exc=RuntimeError("model exploded"))

    doc = process_one_file(_candidate(image_path), fake_engine, index)

    assert doc.ocr_status == OCR_STATUS_FAILED
    assert doc.ocr_result is None
    assert "model exploded" in doc.error


def test_ocr_skipped_for_non_qualifying_doc_type(tmp_path):
    # A folder position that isn't in _FOLDER_DOC_TYPE_PHASE at all (doc_type
    # resolves to None) must skip the expensive engine call rather than
    # attempt it -- OCR is scoped to precedential docs + Applications only.
    image_path = tmp_path / "CON2005029" / "broken.jpg"
    image_path.parent.mkdir(parents=True)
    _make_fake_jpeg(image_path)

    index = CrosswalkIndex([])
    fake_engine = _FakeEngine(exc=RuntimeError("should never be called"))

    doc = process_one_file(_candidate(image_path), fake_engine, index)

    assert doc.ocr_status == OCR_STATUS_SKIPPED
    assert doc.ocr_result is None
    assert fake_engine.calls == []  # the gate must prevent the engine from being invoked at all


def test_page_count_retry_resolves_ambiguous_match(tmp_path):
    # Moved off "B Appendices" -- that folder never gets OCR'd now (see
    # should_attempt_ocr), so the page-count retry this test exercises would
    # never fire there. "D Additional Info & Amendment" still allows OCR
    # unconditionally, keeping this test focused on the crosswalk retry
    # mechanism rather than entangling it with the filename gate.
    a_dir = tmp_path / "CON2005029" / "D Additional Info & Amendment"
    a_dir.mkdir(parents=True)
    file_path = a_dir / "CON2005029 Additional Info.jpg"
    _make_fake_jpeg(file_path)

    index = CrosswalkIndex(
        [
            IndexRow(
                path=CON_PATH.replace("A Main Application", "D Additional Info & Amendment").replace(
                    "CON2005029 Main Application", "CON2005029 Additional Info 1"
                ),
                name="CON2005029 Additional Info 1",
                entry_id=1044,
                page_count=3,
            ),
            IndexRow(
                path=CON_PATH.replace("A Main Application", "D Additional Info & Amendment").replace(
                    "CON2005029 Main Application", "CON2005029 Additional Info 2"
                ),
                name="CON2005029 Additional Info 2",
                entry_id=1045,
                page_count=83,
            ),
        ]
    )
    fake_result = OcrResult(text="ocr text", confidence=0.9, engine="fake", page_count=83, text_source="ocr")
    fake_engine = _FakeEngine(result=fake_result)

    doc = process_one_file(_candidate(file_path), fake_engine, index)

    assert doc.resolved
    assert doc.entry_id == 1045


# --- sniff-based routing (the real corpus is mostly extension-less) ----------


def test_extensionless_native_pdf_routes_to_native_text(tmp_path):
    pdf_dir = tmp_path / "CON2005029" / "A Main Application"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "CON2005029 Main Application"  # no .pdf extension
    _make_native_pdf(pdf_path, "Plenty of real extractable application text lives on this page.")

    index = CrosswalkIndex(
        [IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=1)]
    )
    fake_engine = _FakeEngine()  # must not be called
    doc = process_one_file(_candidate(pdf_path), fake_engine, index)

    assert doc.ocr_status == OCR_STATUS_SUCCEEDED
    assert doc.ocr_result.text_source == "native"
    assert fake_engine.calls == []


def test_plain_text_file_is_read_directly(tmp_path):
    txt_dir = tmp_path / "CON2005029" / "L Other"
    txt_dir.mkdir(parents=True)
    txt_path = txt_dir / "CON2005029 Notes.txt"
    txt_path.write_text("Reviewer notes about the application.")

    index = CrosswalkIndex([])
    fake_engine = _FakeEngine()  # must not be called
    doc = process_one_file(_candidate(txt_path), fake_engine, index)

    assert doc.ocr_status == OCR_STATUS_SUCCEEDED
    assert doc.ocr_result.text == "Reviewer notes about the application."
    assert doc.ocr_result.text_source == "native"
    assert fake_engine.calls == []


def test_html_file_is_read_with_tags_stripped(tmp_path):
    htm_dir = tmp_path / "CON2005029" / "K Public Notices"
    htm_dir.mkdir(parents=True)
    htm_path = htm_dir / "CON2005029 Notice.htm"
    htm_path.write_text("<html><body><p>Public notice of the CON application.</p></body></html>")

    index = CrosswalkIndex([])
    doc = process_one_file(_candidate(htm_path), _FakeEngine(), index)

    assert doc.ocr_status == OCR_STATUS_SUCCEEDED
    assert "Public notice" in doc.ocr_result.text
    assert "<p>" not in doc.ocr_result.text


def test_unknown_binary_fails_cleanly_without_ocr_attempt(tmp_path):
    bin_dir = tmp_path / "CON2005029"
    bin_dir.mkdir(parents=True)
    bin_path = bin_dir / "mystery"
    bin_path.write_bytes(b"\x00\x01\x02\x03" * 32)

    index = CrosswalkIndex([])
    fake_engine = _FakeEngine(exc=AssertionError("engine must not be called for unknown kinds"))
    doc = process_one_file(_candidate(bin_path), fake_engine, index)

    assert doc.ocr_status == OCR_STATUS_FAILED
    assert "unsupported file type" in doc.error
    assert fake_engine.calls == []
