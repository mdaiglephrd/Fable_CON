import pytest
from reportlab.pdfgen import canvas

from ingest.tag_ocr import (
    MAX_OCR_PAGES,
    NativeTextEngine,
    OpenOcrEngine,
    PageCapExceeded,
    _flatten_result,
    extract_html_text,
    extract_plain_text,
)


def _make_pdf(path, pages_text):
    c = canvas.Canvas(str(path))
    for text in pages_text:
        if text:
            c.drawString(100, 700, text)
        c.showPage()
    c.save()


def _make_fake_jpeg(path):
    # JPEG magic bytes so sniff_type routes it as an image.
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)


# --- NativeTextEngine -----------------------------------------------------


def test_extracts_text_from_native_pdf(tmp_path):
    pdf_path = tmp_path / "native.pdf"
    _make_pdf(pdf_path, ["Hello CON2005029 world"])

    result = NativeTextEngine().extract(pdf_path)
    assert "CON2005029" in result.text
    assert result.text_source == "native"
    assert result.engine == "pdfplumber-native"
    assert result.page_count == 1
    assert result.confidence is None


def test_multi_page_pdf_joins_pages_with_form_feed(tmp_path):
    pdf_path = tmp_path / "multi.pdf"
    _make_pdf(pdf_path, ["page one content here", "page two content here"])

    result = NativeTextEngine().extract(pdf_path)
    assert result.page_count == 2
    assert "\f" in result.text


def test_has_native_text_true_for_real_text(tmp_path):
    pdf_path = tmp_path / "native.pdf"
    _make_pdf(pdf_path, ["This page has plenty of real extractable text content."])

    assert NativeTextEngine.has_native_text(pdf_path) is True


def test_has_native_text_false_for_blank_pdf(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _make_pdf(pdf_path, [""])

    assert NativeTextEngine.has_native_text(pdf_path) is False


def test_extract_if_native_returns_result_in_one_parse(tmp_path):
    pdf_path = tmp_path / "native.pdf"
    _make_pdf(pdf_path, ["This page has plenty of real extractable text content."])

    result = NativeTextEngine.extract_if_native(pdf_path)
    assert result is not None
    assert result.text_source == "native"
    assert "extractable text" in result.text


def test_extract_if_native_returns_none_for_scan_like_pdf(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _make_pdf(pdf_path, [""])

    assert NativeTextEngine.extract_if_native(pdf_path) is None


# --- OpenOcrEngine (mocked -- no real model load in tests) -----------------
#
# The fake encodes the VERIFIED openocr-python API (Topdu/OpenOCR
# docs/openocr.md): the engine is called with a file-path string and returns
# a (results, time_dicts) tuple, where results is per-image and each image's
# entry is a list of {'text': ..., 'score': ...} line dicts.


class _FakeOpenOcrModel:
    def __init__(self, line_lists):
        self._line_lists = list(line_lists)  # one list of line dicts per expected call
        self.calls = []

    def __call__(self, image_path):
        self.calls.append(image_path)
        lines = self._line_lists.pop(0)
        return [lines], {"detection_time": 0.01, "recognition_time": 0.02}


def test_extract_image_uses_engine_and_flattens_result(monkeypatch, tmp_path):
    image_path = tmp_path / "scan.jpg"
    _make_fake_jpeg(image_path)

    fake = _FakeOpenOcrModel([[{"text": "line one", "score": 0.9}, {"text": "line two", "score": 0.8}]])
    engine = OpenOcrEngine()
    monkeypatch.setattr(engine, "_engine_instance", lambda: fake)

    result = engine.extract(image_path)
    assert result.text_source == "ocr"
    assert result.engine == "openocr-python"
    assert result.page_count == 1
    assert result.text == "line one\nline two"
    assert result.confidence == pytest.approx(0.85)
    assert fake.calls == [str(image_path)]  # called with a path string, not an image object


def test_extract_pdf_rasterizes_each_page_to_temp_files(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scanned.pdf"
    _make_pdf(pdf_path, ["", ""])  # blank pages: OpenOcrEngine doesn't care about native text

    fake = _FakeOpenOcrModel(
        [
            [{"text": "page 1 ocr text", "score": 1.0}],
            [{"text": "page 2 ocr text", "score": 0.5}],
        ]
    )
    engine = OpenOcrEngine()
    monkeypatch.setattr(engine, "_engine_instance", lambda: fake)

    result = engine.extract(pdf_path)
    assert result.page_count == 2
    assert "page 1 ocr text" in result.text
    assert "page 2 ocr text" in result.text
    assert result.confidence == pytest.approx(0.75)
    assert len(fake.calls) == 2
    # Pages are handed over as temp image FILE PATHS (the engine takes paths).
    assert all(isinstance(call, str) and call.endswith(".png") for call in fake.calls)


def test_extract_extensionless_pdf_routes_by_magic_bytes(monkeypatch, tmp_path):
    pdf_path = tmp_path / "CON2005029 Main Application"  # no extension, like the real corpus
    _make_pdf(pdf_path, [""])

    fake = _FakeOpenOcrModel([[{"text": "ocr text", "score": 0.9}]])
    engine = OpenOcrEngine()
    monkeypatch.setattr(engine, "_engine_instance", lambda: fake)

    result = engine.extract(pdf_path)
    assert result.page_count == 1  # went down the PDF path, not the single-image path


def test_page_cap_exceeded_raises(monkeypatch, tmp_path):
    pdf_path = tmp_path / "huge.pdf"
    _make_pdf(pdf_path, ["", ""])  # 2 pages

    monkeypatch.setattr("ingest.tag_ocr.MAX_OCR_PAGES", 1)
    engine = OpenOcrEngine()

    with pytest.raises(PageCapExceeded, match="page cap exceeded"):
        engine.extract(pdf_path)
    assert MAX_OCR_PAGES  # module default untouched for other tests


def test_run_tolerates_bare_results_without_tuple(monkeypatch, tmp_path):
    image_path = tmp_path / "scan.jpg"
    _make_fake_jpeg(image_path)

    class BareModel:
        def __call__(self, image_path):
            return [[{"text": "just results", "score": 0.6}]]  # no time_dicts tuple

    engine = OpenOcrEngine()
    monkeypatch.setattr(engine, "_engine_instance", lambda: BareModel())

    result = engine.extract(image_path)
    assert result.text == "just results"


# --- _flatten_result ---------------------------------------------------------


def test_flatten_result_handles_empty_result():
    assert _flatten_result([]) == ("", None)
    assert _flatten_result(None) == ("", None)


def test_flatten_result_handles_tuple_shape():
    text, confidence = _flatten_result([("box", "recognized text", 0.7)])
    assert text == "recognized text"
    assert confidence == 0.7


def test_flatten_result_handles_dict_shape():
    text, confidence = _flatten_result([{"text": "a"}, {"text": "b", "score": 0.4}])
    assert text == "a\nb"
    assert confidence == 0.4


# --- direct text/HTML extraction ----------------------------------------------


def test_extract_plain_text_reads_file_directly(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("Determination request received on 3/1/2005.")

    result = extract_plain_text(path)
    assert result.text == "Determination request received on 3/1/2005."
    assert result.text_source == "native"
    assert result.engine == "plain-text"


def test_extract_html_text_strips_tags_and_scripts(tmp_path):
    path = tmp_path / "letter.htm"
    path.write_text(
        "<html><head><script>var x = 1;</script></head>"
        "<body><h1>Notice</h1><p>The application was <b>approved</b>.</p></body></html>"
    )

    result = extract_html_text(path)
    assert "Notice" in result.text
    assert "approved" in result.text
    assert "var x" not in result.text
    assert "<p>" not in result.text
