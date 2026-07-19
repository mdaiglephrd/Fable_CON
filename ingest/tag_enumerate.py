"""Enumerate candidate files under the SSD root -- the first of the three
independently-testable stages (enumerate / process / load) the tag ETL
pipeline is split into so it can later be lift-and-shifted into a
timer-triggered Azure Function (see docs/07-tag-etl-runbook.md).

Pure filesystem walk: no DB, no OCR. Non-file entries (directories, symlinks
to directories) are skipped; a per-entry OSError (permission denied, broken
symlink) is logged and the walk continues rather than aborting -- one bad
entry in a 150,000-document tree must never stop the run.
"""

from __future__ import annotations

import os
import re
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

from common.json_logging import configure_json_logging

log = configure_json_logging(__name__)

_ORDERING_PREFIX_RE = re.compile(r"^(?:[\dA-Za-z](?:\.\d+)*)\s+")

# Folder names (leading ordering prefix stripped, e.g. "8 ", case-insensitive)
# whose entire subtree is out of scope: these files never become
# CandidateFiles at all, so they skip hashing, crosswalk, and OCR entirely --
# not just the OCR step. Architectural/facility drawings, not legal filings.
_EXCLUDED_SUBTREE_NAMES = frozenset({"state architect files"})


def _is_excluded_subtree(dirname: str) -> bool:
    stripped = _ORDERING_PREFIX_RE.sub("", dirname).strip().lower()
    return stripped in _EXCLUDED_SUBTREE_NAMES


@dataclass(frozen=True)
class CandidateFile:
    """One file found under the SSD root, ready for tag_process.process_one_file."""

    path: Path
    size_bytes: int
    modified_at: float  # POSIX timestamp (os.stat st_mtime)
    created_at: float  # POSIX timestamp (os.stat st_ctime; birth time where available)


def enumerate_candidate_files(root: Path):
    """Yield a CandidateFile for every regular file under `root`, recursively.

    Order is os.walk's (top-down, directory-by-directory) -- callers that
    need document-type batching sort/group the yielded items themselves
    (see ingest/tag_orchestrate.py), so this stays a plain, resumable
    generator with no batching logic of its own.
    """
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not _is_excluded_subtree(d))
        for filename in sorted(filenames):
            file_path = Path(dirpath) / filename
            try:
                info = os.stat(file_path)
            except OSError:
                log.warning("skipping unreadable entry", extra={"file_path": str(file_path)})
                continue
            if not stat_module.S_ISREG(info.st_mode):
                continue
            yield CandidateFile(
                path=file_path,
                size_bytes=info.st_size,
                modified_at=info.st_mtime,
                created_at=info.st_ctime,
            )
