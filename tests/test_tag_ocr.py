import pytest
from reportlab.pdfgen import canvas

from ingest.tag_ocr import NativeTextEngine, OpenOcrEngine, _flatten_result


def _make_pdf(path, pages_text):
    c = canvas.Canvas(str(path))
    for text in pages_text:
        if text:
            c.drawString(100, 700, text)
        c.showPage()
    c.save()


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


# --- OpenOcrEngine (mocked -- no real model load in tests) -----------------


class _FakeOpenOcrModel:
    """Stands in for the lazily-imported openocr-python engine callable."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, image_or_path):
        self.calls.append(image_or_path)
        return self._responses.pop(0)


def test_extract_image_uses_engine_and_flattens_result(monkeypatch):
    fake = _FakeOpenOcrModel([[{"text": "line one", "score": 0.9}, {"text": "line two", "score": 0.8}]])
    engine = OpenOcrEngine()
    monkeypatch.setattr(engine, "_engine_instance", lambda: fake)

    result = engine.extract(_ImagePath("scan.jpg"))
    assert result.text_source == "ocr"
    assert result.engine == "openocr-python"
    assert result.page_count == 1
    assert result.text == "line one\nline two"
    assert result.confidence == pytest.approx(0.85)
    assert fake.calls == [_ImagePath("scan.jpg")]


def test_extract_pdf_rasterizes_each_page(monkeypatch, tmp_path):
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


class _ImagePath:
    """Minimal stand-in for a Path with a .suffix, used only in the image test."""

    def __init__(self, name):
        self.name = name
        self.suffix = "." + name.rsplit(".", 1)[-1]

    def __eq__(self, other):
        return isinstance(other, _ImagePath) and self.name == other.name

    def __repr__(self):
        return f"_ImagePath({self.name!r})"
