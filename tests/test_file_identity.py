import hashlib

from common.file_identity import hash_file, hash_path


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
