"""Swappable OCR/text-extraction engines for the tag ETL pipeline.

NativeTextEngine tries pdfplumber's existing text layer first -- a real
cost/time win over 150,000 documents, since many PDFs already carry
extractable text and never need real OCR. OpenOcrEngine (openocr-python,
github.com/Topdu/OpenOCR) is the fallback for scanned/image-only PDFs and
image files. Both implement the OcrEngine protocol so ingest/tag_process.py
can be handed either (or a test double) without caring which.

No existing swappable-engine pattern exists elsewhere in this repo to copy
structurally, but pdfplumber is already a repo dependency (used today by
ingest/weekly_report_parser.py) -- reusing it for the native-text fast path
is a direct reuse, not a new dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Minimum average characters per page below which a PDF's "native" text
# layer is considered absent/unusable (an image-only scan), not real text.
MIN_CHARS_PER_PAGE = 20

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


class NativeTextEngine:
    """Extracts a PDF's existing text layer via pdfplumber; runs no OCR model."""

    name = "pdfplumber-native"

    def extract(self, path: Path) -> OcrResult:
        texts = self._page_texts(path)
        return OcrResult(
            text="\f".join(texts),
            confidence=None,
            engine=self.name,
            page_count=len(texts),
            text_source="native",
        )

    @staticmethod
    def has_native_text(path: Path) -> bool:
        """True when the PDF's own text layer looks real, not an image-only scan."""
        texts = NativeTextEngine._page_texts(path)
        if not texts:
            return False
        return (sum(len(t) for t in texts) / len(texts)) >= MIN_CHARS_PER_PAGE

    @staticmethod
    def _page_texts(path: Path) -> list[str]:
        import pdfplumber  # lazy: pure logic/tests must not require the PDF stack

        with pdfplumber.open(path) as pdf:
            return [(page.extract_text() or "") for page in pdf.pages]


class OpenOcrEngine:
    """Wraps openocr-python for scanned/image-only PDFs and image files.

    The exact call/response shape of the installed openocr-python version
    should be confirmed against real sample documents before the first
    production run -- _run() and _flatten_result() below are the only two
    places that would need adjusting.
    """

    name = "openocr-python"

    def __init__(self) -> None:
        self._engine = None  # lazy-constructed on first use (loads model weights)

    def extract(self, path: Path) -> OcrResult:
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf(path)
        return self._extract_image(path)

    def _extract_image(self, path: Path) -> OcrResult:
        text, confidence = self._run(path)
        return OcrResult(
            text=text, confidence=confidence, engine=self.name, page_count=1, text_source="ocr"
        )

    def _extract_pdf(self, path: Path) -> OcrResult:
        # Scanned PDFs have no text layer to lift directly, so each page is
        # rasterized via pdfplumber (already a repo dependency) and handed to
        # the OCR engine as an image.
        import pdfplumber

        texts: list[str] = []
        confidences: list[float] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                image = page.to_image(resolution=200).original
                text, confidence = self._run(image)
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

            self._engine = OpenOCR()
        return self._engine

    def _run(self, image_or_path) -> tuple[str, float | None]:
        result = self._engine_instance()(image_or_path)
        return _flatten_result(result)


def _flatten_result(result) -> tuple[str, float | None]:
    """Normalize an openocr-python result into (joined_text, avg_confidence).

    Assumes the common OCR-toolkit convention of a sequence of per-line
    detections, each carrying recognized text and a confidence score --
    confirm against the installed version's actual return shape.
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
