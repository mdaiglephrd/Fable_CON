"""CLI orchestrator for the tag ETL: enumerate -> resolve/OCR -> load.

CLI:
    python -m ingest.tag_orchestrate /path/to/ssd --index-xlsx index.xlsx
        [--apply] [--batch-size 500] [--rejects out.csv]

Without --apply, this only enumerates the corpus and hashes each file (a
readable preview of scope and file-health, matching ingest/index_diff.py's
--apply gating convention) -- no OCR runs and nothing touches the database.

Batching: files are processed in enumerate_candidate_files' natural
directory-tree-order (os.walk descends one subtree at a time), which already
clusters files by their real folder -- and therefore by document category --
without needing a separate re-grouping pass that would require buffering the
whole 150,000-document corpus before starting any work. A commit happens
every --batch-size documents, so a crash mid-run only ever loses the
currently-uncommitted batch; already-committed documents are never
duplicated (ingest/tag_load.py's con.tag_source_file ledger + con.document's
own entry_id MERGE both make reprocessing a no-op).

This is a thin CLI wrapper: enumerate_candidate_files / process_one_file /
load_one_record hold all the real logic and are independently unit-tested.
Keeping this file thin is deliberate -- it is what makes the later lift-and-
shift into a timer-triggered Azure Function a wiring change, not a rewrite
(see docs/07-tag-etl-runbook.md).
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.file_identity import hash_file, hash_path
from common.json_logging import configure_json_logging
from ingest.tag_crosswalk import CrosswalkIndex, load_index
from ingest.tag_enumerate import enumerate_candidate_files
from ingest.tag_load import (
    STATUS_SUCCEEDED,
    STATUS_UNRESOLVED,
    already_succeeded,
    load_one_record,
)
from ingest.tag_ocr import OcrEngine, OpenOcrEngine
from ingest.tag_process import process_one_file

log = configure_json_logging(__name__)


@dataclass
class RunStats:
    seen: int = 0
    skipped_already_done: int = 0
    loaded: int = 0
    unresolved: int = 0
    failed: int = 0
    commits: int = 0

    def summary_lines(self) -> list[str]:
        return [
            f"files seen:             {self.seen}",
            f"skipped (already done): {self.skipped_already_done}",
            f"loaded:                 {self.loaded}",
            f"unresolved (crosswalk): {self.unresolved}",
            f"failed (ocr/db):        {self.failed}",
            f"commits:                {self.commits}",
        ]


def run(
    conn: Any,
    root: Path,
    index: CrosswalkIndex,
    engine: OcrEngine,
    *,
    batch_size: int = 500,
    apply: bool = False,
    rejects_writer: Any = None,
) -> RunStats:
    """Enumerate -> resolve/OCR -> load every file under root."""
    stats = RunStats()
    pending = 0

    for candidate in enumerate_candidate_files(root):
        stats.seen += 1
        file_hash = hash_file(candidate.path)

        if not apply:
            continue  # dry run: enumeration + hashing only, no OCR/DB

        path_hash = hash_path(str(candidate.path))
        if already_succeeded(conn, path_hash, file_hash):
            stats.skipped_already_done += 1
            continue

        doc = process_one_file(candidate, engine, index)
        result = load_one_record(conn, doc)

        if result.status == STATUS_SUCCEEDED:
            stats.loaded += 1
        elif result.status == STATUS_UNRESOLVED:
            stats.unresolved += 1
            _write_reject(rejects_writer, candidate.path, doc.docket_id, f"confidence={doc.match_confidence:.2f}")
        else:
            stats.failed += 1
            _write_reject(rejects_writer, candidate.path, result.docket_id, result.detail or "")

        pending += 1
        if pending >= batch_size:
            conn.commit()
            stats.commits += 1
            pending = 0

    if apply and pending:
        conn.commit()
        stats.commits += 1

    return stats


def _write_reject(writer: Any, path: Path, docket_id: str | None, detail: str) -> None:
    if writer is not None:
        writer.writerow([str(path), docket_id or "", detail])


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.tag_orchestrate",
        description=(
            "Walk the SSD CON/DET document corpus, OCR each file, and load "
            "untagged document records into con.matter/con.document/con.document_text."
        ),
    )
    parser.add_argument("root", type=Path, help="root directory of the SSD document corpus")
    parser.add_argument(
        "--index-xlsx",
        type=Path,
        required=True,
        help="operator-supplied Path/Name/Type/Entry ID/Page Count index (.xlsx)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="write to the database (default: dry run)"
    )
    parser.add_argument("--batch-size", type=int, default=500, help="documents per commit")
    parser.add_argument(
        "--rejects", type=Path, help="write unresolved/failed files to this CSV"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    index = load_index(args.index_xlsx)
    log.info("index loaded", extra={"index_rows": len(index)})

    rejects_file = None
    rejects_writer = None
    if args.rejects is not None:
        rejects_file = open(args.rejects, "w", newline="", encoding="utf-8")
        rejects_writer = csv.writer(rejects_file)
        rejects_writer.writerow(["file_path", "docket_id", "detail_or_confidence"])

    engine: OcrEngine = OpenOcrEngine()

    conn = None
    try:
        if args.apply:
            from common.db import get_connection  # lazy: pyodbc not needed for dry runs

            conn = get_connection()
        stats = run(
            conn,
            args.root,
            index,
            engine,
            batch_size=args.batch_size,
            apply=args.apply,
            rejects_writer=rejects_writer,
        )
    finally:
        if conn is not None:
            conn.close()
        if rejects_file is not None:
            rejects_file.close()

    for line in stats.summary_lines():
        print(line)
    if not args.apply:
        print("dry run: no OCR performed, no database writes (use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
