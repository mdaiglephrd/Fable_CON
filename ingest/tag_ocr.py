"""Swappable OCR/text-extraction engines for the tag ETL pipeline.

NativeTextEngine tries pdfplumber's existing text layer first -- a real
cost/time win over 150,000 documents, since many PDFs already carry
extractable text and never need real OCR. OpenOcrEngine (openocr-python,
github.com/Topdu/OpenOCR) is the fallback for scanned/image-only PDFs and
image files. Both implement the OcrEngine protocol so ingest/tag_process.py
can be handed either (or a test double) without caring which.

OpenOcrEngine is written against the verified openocr-python API
(github.com/Topdu/OpenOCR docs/openocr.md):
    engine = OpenOCR(mode='mobile'|'server', backend='onnx'|'torch')
    results, time_dicts = engine(image_path)      # input is a FILE PATH
    # results is per-image; each item is a list of line dicts with
    # 'text' and 'score' keys.
Scanned-PDF pages are therefore rasterized to temp image files (the engine
takes paths, not in-memory images), using the same tempfile+remove-quietly
pattern as functions/processing.py.

File-kind routing (pdf vs image vs text) uses common.file_identity.sniff_type
-- magic bytes, not extensions -- because the real corpus is mostly
extension-less. Plain-text and HTML files are read directly
(extract_plain_text / extract_html_text); they never go through OCR.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

from common.file_identity import KIND_PDF, sniff_type

# Minimum average characters per page below which a PDF's "native" text
# layer is considered absent/unusable (an image-only scan), not real text.
MIN_CHARS_PER_PAGE = 20

# OCR page cap: one pathological file (the index's largest document is 9,794
# pages) must not stall a multi-week run. Past the cap the file fails fast
# with a clear error and lands in the rejects report for manual handling.
# Native-text extraction (cheap) is NOT capped -- only rasterize+OCR is.
MAX_OCR_PAGES = 2000

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"})


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float | None
    engine: str
    page_count: int | None
    text_source: str  # "native" | "ocr"


class OcrEngine(Protocol):
    def extract(self, path: Path) -> OcrResult: ...


class PageCapExceeded(ValueError):
    """Raised when a scanned PDF exceeds MAX_OCR_PAGES (fails fast, no stall)."""


# --------------------------------------------------------------------------
# Native text layer (pdfplumber)
# --------------------------------------------------------------------------


class NativeTextEngine:
    """Extracts a PDF's existing text layer via pdfplumber; runs no OCR model."""

    name = "pdfplumber-native"

    def extract(self, path: Path) -> OcrResult:
        return self._result(self._page_texts(path))

    @classmethod
    def extract_if_native(cls, path: Path) -> OcrResult | None:
        """One-parse fast path: the extracted result when the PDF's own text
        layer looks real, else None (caller falls back to OCR). Avoids the
        parse-twice cost of has_native_text() + extract() over 150K files."""
        texts = cls._page_texts(path)
        if not cls._looks_native(texts):
            return None
        return cls._result(texts)

    @staticmethod
    def has_native_text(path: Path) -> bool:
        """True when the PDF's own text layer looks real, not an image-only scan."""
        return NativeTextEngine._looks_native(NativeTextEngine._page_texts(path))

    @staticmethod
    def _looks_native(texts: list[str]) -> bool:
        if not texts:
            return False
        return (sum(len(t) for t in texts) / len(texts)) >= MIN_CHARS_PER_PAGE

    @classmethod
    def _result(cls, texts: list[str]) -> OcrResult:
        return OcrResult(
            text="\f".join(texts),
            confidence=None,
            engine=cls.name,
            page_count=len(texts),
            text_source="native",
        )

    @staticmethod
    def _page_texts(path: Path) -> list[str]:
        import pdfplumber  # lazy: pure logic/tests must not require the PDF stack

        with pdfplumber.open(path) as pdf:
            return [(page.extract_text() or "") for page in pdf.pages]


# --------------------------------------------------------------------------
# OpenOCR (openocr-python)
# --------------------------------------------------------------------------


class OpenOcrEngine:
    """Wraps openocr-python for scanned/image-only PDFs and image files."""

    name = "openocr-python"

    def __init__(self, mode: str = "mobile", backend: str = "onnx") -> None:
        self._mode = mode
        self._backend = backend
        self._engine = None  # lazy-constructed on first use (loads model weights)

    def extract(self, path: Path) -> OcrResult:
        if sniff_type(path) == KIND_PDF:
            return self._extract_pdf(path)
        return self._extract_image(path)

    def _extract_image(self, path: Path) -> OcrResult:
        text, confidence = self._run(path)
        return OcrResult(
            text=text, confidence=confidence, engine=self.name, page_count=1, text_source="ocr"
        )

    def _extract_pdf(self, path: Path) -> OcrResult:
        # Scanned PDFs have no text layer to lift directly, so each page is
        # rasterized via pdfplumber (already a repo dependency), saved to a
        # temp image file (the OpenOCR engine takes file paths, not in-memory
        # images), OCR'd, and cleaned up.
        import pdfplumber

        texts: list[str] = []
        confidences: list[float] = []
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) > MAX_OCR_PAGES:
                raise PageCapExceeded(
                    f"OCR page cap exceeded ({len(pdf.pages)} pages > {MAX_OCR_PAGES}); "
                    "handle this file manually"
                )
            for page in pdf.pages:
                image = page.to_image(resolution=200).original
                fd, temp_path = tempfile.mkstemp(suffix=".png")
                try:
                    with os.fdopen(fd, "wb") as fh:
                        image.save(fh, format="PNG")
                    text, confidence = self._run(temp_path)
                finally:
                    _remove_quietly(temp_path)
                texts.append(text)
                if confidence is not None:
                    confidences.append(confidence)
        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        return OcrResult(
            text="\f".join(texts),
            confidence=avg_confidence,
            engine=self.name,
            page_count=len(texts),
            text_source="ocr",
        )

    def _engine_instance(self):
        if self._engine is None:
            from openocr import OpenOCR  # lazy: heavy model-loading dependency

            self._engine = OpenOCR(mode=self._mode, backend=self._backend)
        return self._engine

    def _run(self, image_path) -> tuple[str, float | None]:
        returned = self._engine_instance()(str(image_path))
        # Verified API: a (results, time_dicts) tuple, results per-image.
        # Tolerate a bare results return defensively (older/newer versions).
        if isinstance(returned, tuple) and len(returned) == 2:
            results = returned[0]
        else:
            results = returned
        if results and not isinstance(results[0], (dict, tuple)):
            # results is a list-per-image; take the first (only) image's lines.
            results = results[0]
        return _flatten_result(results)


def _remove_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _flatten_result(result) -> tuple[str, float | None]:
    """Normalize one image's OCR line list into (joined_text, avg_confidence).

    Each line is a dict with 'text'/'score' keys per the verified
    openocr-python result format; tuple-shaped lines (box, text, score) are
    tolerated for robustness across versions.
    """
    if not result:
        return "", None
    lines: list[str] = []
    scores: list[float] = []
    for item in result:
        if isinstance(item, dict):
            line_text = item.get("text", "")
            score = item.get("score")
        else:
            line_text = item[-2] if len(item) >= 2 else ""
            score = item[-1] if len(item) >= 2 else None
        lines.append(str(line_text))
        if isinstance(score, (int, float)):
            scores.append(float(score))
    text = "\n".join(lines)
    confidence = sum(scores) / len(scores) if scores else None
    return text, confidence


# --------------------------------------------------------------------------
# Direct text/HTML extraction (no OCR)
# --------------------------------------------------------------------------


class _HtmlTextExtractor(HTMLParser):
    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._chunks)


def extract_plain_text(path: Path) -> OcrResult:
    """Direct read of a plain-text file (no OCR)."""
    raw = Path(path).read_bytes().decode("utf-8", errors="replace")
    return OcrResult(
        text=raw, confidence=None, engine="plain-text", page_count=None, text_source="native"
    )


def extract_html_text(path: Path) -> OcrResult:
    """Direct read of an HTML file, tags stripped via stdlib html.parser (no OCR)."""
    raw = Path(path).read_bytes().decode("utf-8", errors="replace")
    parser = _HtmlTextExtractor()
    parser.feed(raw)
    return OcrResult(
        text=parser.text(), confidence=None, engine="html-text", page_count=None,
        text_source="native",
    )
