import hashlib

from common.file_identity import (
    KIND_HTML,
    KIND_IMAGE,
    KIND_PDF,
    KIND_TEXT,
    KIND_UNKNOWN,
    hash_file,
    hash_path,
    sniff_type,
)


def test_hash_file_matches_stdlib_sha256(tmp_path):
    path = tmp_path / "sample.txt"
    content = b"CON2005029 Main Application" * 100
    path.write_bytes(content)

    assert hash_file(path) == hashlib.sha256(content).hexdigest()


def test_hash_file_is_stable_across_calls(tmp_path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"\x00\x01\x02" * 10000)

    assert hash_file(path) == hash_file(path)


def test_hash_file_differs_for_different_content(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"content A")
    b.write_bytes(b"content B")

    assert hash_file(a) != hash_file(b)


def test_hash_file_handles_empty_file(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    assert hash_file(path) == hashlib.sha256(b"").hexdigest()


def test_hash_file_larger_than_chunk_size(tmp_path):
    path = tmp_path / "big.bin"
    content = b"x" * (1024 * 1024 + 12345)  # spans multiple 1 MiB chunks
    path.write_bytes(content)

    assert hash_file(path) == hashlib.sha256(content).hexdigest()


def test_hash_path_matches_stdlib_sha256():
    path_str = r"CON2005029\1 Master File\A Main Application\CON2005029 Main Application"
    assert hash_path(path_str) == hashlib.sha256(path_str.encode("utf-8")).hexdigest()


def test_hash_path_differs_for_different_paths():
    assert hash_path("a/b/c") != hash_path("a/b/d")


def test_hash_path_is_fixed_length_regardless_of_input_length():
    short = hash_path("x")
    long = hash_path("x" * 5000)
    assert len(short) == len(long) == 64


# --- sniff_type -------------------------------------------------------------


def test_sniff_pdf_by_magic_bytes_without_extension(tmp_path):
    path = tmp_path / "CON2005029 Main Application"  # extension-less, like the real corpus
    path.write_bytes(b"%PDF-1.7\n...rest of pdf...")
    assert sniff_type(path) == KIND_PDF


def test_sniff_jpeg_and_png_and_tiff_by_magic_bytes(tmp_path):
    jpeg = tmp_path / "scan1"
    jpeg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 16)
    png = tmp_path / "scan2"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    tiff = tmp_path / "scan3"
    tiff.write_bytes(b"II*\x00" + b"\x00" * 16)
    assert sniff_type(jpeg) == KIND_IMAGE
    assert sniff_type(png) == KIND_IMAGE
    assert sniff_type(tiff) == KIND_IMAGE


def test_sniff_html_by_content(tmp_path):
    path = tmp_path / "letter"
    path.write_bytes(b"<!DOCTYPE html><html><body>Notice</body></html>")
    assert sniff_type(path) == KIND_HTML


def test_sniff_extension_fallback_for_text(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_bytes(b"plain notes")
    assert sniff_type(path) == KIND_TEXT


def test_sniff_printable_heuristic_for_extensionless_text(tmp_path):
    path = tmp_path / "readme"
    path.write_bytes(b"Just some plain readable text with no markers at all.")
    assert sniff_type(path) == KIND_TEXT


def test_sniff_unknown_for_binary_junk(tmp_path):
    path = tmp_path / "mystery.bin"
    path.write_bytes(b"\x00\x01\x02\x03" * 32)
    assert sniff_type(path) == KIND_UNKNOWN


def test_sniff_unknown_for_unreadable_path(tmp_path):
    assert sniff_type(tmp_path / "does-not-exist") == KIND_UNKNOWN
