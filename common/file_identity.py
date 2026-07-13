"""Stable file identity for the tag ETL pipeline.

A document's identity for idempotency purposes is (file_path, file_hash), not
just its filename -- see DESIGN.md's tag-ETL module contracts. hash_file()
streams the file so large PDFs don't need to fit in memory at once.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


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
