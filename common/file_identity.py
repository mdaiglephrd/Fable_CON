"""Stable file identity and content-type sniffing for the tag ETL pipeline.

A document's identity for idempotency purposes is (file_path, file_hash), not
just its filename -- see DESIGN.md's tag-ETL module contracts. hash_file()
streams the file so large PDFs don't need to fit in memory at once.

sniff_type() exists because the real corpus is mostly extension-less (the
Laserfiche index shows 129,596 of 137,392 document names without one):
routing OCR by file extension alone would send extension-less PDFs to the
image path and guarantee failures. Magic bytes win over extensions; the
extension is only a fallback when the leading bytes are inconclusive.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB

# Content kinds sniff_type() can return.
KIND_PDF = "pdf"
KIND_IMAGE = "image"
KIND_HTML = "html"
KIND_TEXT = "text"
KIND_UNKNOWN = "unknown"

_IMAGE_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", KIND_IMAGE),
    (b"\xff\xd8\xff", KIND_IMAGE),  # JPEG
    (b"II*\x00", KIND_IMAGE),  # TIFF little-endian
    (b"MM\x00*", KIND_IMAGE),  # TIFF big-endian
    (b"BM", KIND_IMAGE),  # BMP
)

_TEXT_EXTENSIONS = frozenset({".txt", ".text", ".csv", ".log"})
_HTML_EXTENSIONS = frozenset({".htm", ".html"})
_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"})


def hash_file(path: Path) -> str:
    """sha256 hex digest of a file's bytes, read in streamed chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def hash_path(path: str) -> str:
    """sha256 hex digest of a path string.

    Used alongside hash_file() as the two halves of the tag ETL's stable file
    identity (path + content hash). A real file path can be arbitrarily long,
    which would blow past SQL Server's 900-byte index key limit if used
    directly in a primary key -- hashing it first keeps the ledger key
    (con.tag_source_file) a fixed, small size while still keying on both
    dimensions the spec calls for.
    """
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def sniff_type(path: Path) -> str:
    """Best-effort content kind: pdf | image | html | text | unknown.

    Magic bytes first (the corpus is mostly extension-less), then HTML
    markers, then the extension, then a printable-text heuristic. Reads at
    most 4 KiB.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return KIND_UNKNOWN

    if head.startswith(b"%PDF-"):
        return KIND_PDF
    for magic, kind in _IMAGE_MAGIC:
        if head.startswith(magic):
            return kind

    lowered = head.lstrip()[:256].lower()
    if lowered.startswith((b"<!doctype html", b"<html")) or b"<html" in lowered:
        return KIND_HTML

    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return KIND_PDF
    if suffix in _IMAGE_EXTENSIONS:
        return KIND_IMAGE
    if suffix in _HTML_EXTENSIONS:
        return KIND_HTML
    if suffix in _TEXT_EXTENSIONS:
        return KIND_TEXT

    if head and b"\x00" not in head:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return KIND_TEXT
    return KIND_UNKNOWN
