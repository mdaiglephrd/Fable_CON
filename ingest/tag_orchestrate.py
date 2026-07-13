"""CLI orchestrator for the tag ETL: enumerate -> resolve/OCR -> load.

CLI:
    python -m ingest.tag_orchestrate /path/to/ssd --index-xlsx index.xlsx
        [--apply] [--batch-size 500] [--workers 1] [--rejects out.csv]

Without --apply, this only enumerates the corpus (file count + total size
from the directory walk's stat calls -- no file contents are read, so a
preview of a multi-terabyte SSD takes minutes, not hours). Hashing, OCR, and
all database work happen only with --apply, matching ingest/index_diff.py's
--apply gating convention.

Resume skip-check: the succeeded (path_hash, file_hash) ledger keys are
preloaded ONCE per run (ingest/tag_load.py::succeeded_source_keys) so
resuming a 150K-file run costs one SELECT, not 150K.

Parallelism (--workers N): hashing + crosswalk + OCR are pure and per-file,
so they fan out over a spawn-context multiprocessing.Pool; each worker builds
its own OCR engine and loads its own copy of the crosswalk index in its
initializer. The parent process stays the SINGLE database writer, consuming
results and committing every --batch-size documents -- load semantics are
identical to the serial path, and no DB connection ever crosses a process
boundary. --workers 1 (default) runs everything inline with no Pool.

Batching: files are processed in enumerate_candidate_files' natural
directory-tree-order (os.walk descends one subtree at a time), which already
clusters files by their real folder -- and therefore by document category --
without needing a separate re-grouping pass that would require buffering the
whole 150,000-document corpus before starting any work. A commit happens
every --batch-size documents, so a crash mid-run only ever loses the
currently-uncommitted batch; already-committed documents are never
duplicated (ingest/tag_load.py's con.tag_source_file ledger + con.document's
own entry_id MERGE both make reprocessing a no-op). With --workers > 1
completion order within the pool is not deterministic, but every file is
processed exactly once and load semantics don't depend on order.

This is a thin CLI wrapper: enumerate_candidate_files / process_one_file /
load_one_record hold all the real logic and are independently unit-tested.
Keeping this file thin is deliberate -- it is what makes the later lift-and-
shift into a timer-triggered Azure Function a wiring change, not a rewrite
(see docs/07-tag-etl-runbook.md).
"""

from __future__ import annotations

import argparse
import csv
import multiprocessing
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.file_identity import hash_file, hash_path
from common.json_logging import configure_json_logging
from ingest.tag_crosswalk import CrosswalkIndex, load_index
from ingest.tag_enumerate import CandidateFile, enumerate_candidate_files
from ingest.tag_load import (
    STATUS_SUCCEEDED,
    STATUS_UNRESOLVED,
    load_one_record,
    succeeded_source_keys,
)
from ingest.tag_ocr import OcrEngine, OpenOcrEngine
from ingest.tag_process import ProcessedDocument, process_one_file

log = configure_json_logging(__name__)

# Chunk size for Pool.imap: small enough to keep workers evenly fed on a
# mixed corpus (one huge scanned PDF next to many one-page letters), large
# enough to amortize IPC.
_POOL_CHUNKSIZE = 4


@dataclass
class RunStats:
    seen: int = 0
    total_bytes: int = 0
    skipped_already_done: int = 0
    loaded: int = 0
    unresolved: int = 0
    failed: int = 0
    commits: int = 0

    def summary_lines(self) -> list[str]:
        return [
            f"files seen:             {self.seen}",
            f"total size:             {self.total_bytes / (1024 ** 3):.2f} GiB",
            f"skipped (already done): {self.skipped_already_done}",
            f"loaded:                 {self.loaded}",
            f"unresolved (crosswalk): {self.unresolved}",
            f"failed (ocr/db):        {self.failed}",
            f"commits:                {self.commits}",
        ]


# --------------------------------------------------------------------------
# Per-file work (runs inline, or in a pool worker with --workers > 1)
# --------------------------------------------------------------------------


def _process_candidate(
    candidate: CandidateFile,
    engine: OcrEngine,
    index: CrosswalkIndex,
    succeeded: set[tuple[str, str]],
) -> ProcessedDocument | None:
    """Hash, skip-check, and process one file. None = already loaded (skip)."""
    path_hash = hash_path(str(candidate.path))
    file_hash = hash_file(candidate.path)
    if (path_hash, file_hash) in succeeded:
        return None
    return process_one_file(candidate, engine, index)


# Worker-process state, built once per worker by _init_worker (spawn context:
# nothing here is inherited from the parent; each worker loads its own index
# copy and constructs its own OCR engine).
_worker_state: dict[str, Any] = {}


def _init_worker(
    index_xlsx: str, succeeded: set[tuple[str, str]], ocr_mode: str, ocr_backend: str
) -> None:
    _worker_state["index"] = load_index(Path(index_xlsx))
    _worker_state["succeeded"] = succeeded
    _worker_state["engine"] = OpenOcrEngine(mode=ocr_mode, backend=ocr_backend)


def _worker_process(
    candidate: CandidateFile,
) -> tuple[CandidateFile, ProcessedDocument | None]:
    """Pool task: returns the candidate alongside its result so the parent
    can account for skipped files (whose result is None) without extra
    bookkeeping."""
    doc = _process_candidate(
        candidate,
        _worker_state["engine"],
        _worker_state["index"],
        _worker_state["succeeded"],
    )
    return candidate, doc


# --------------------------------------------------------------------------
# The run loop
# --------------------------------------------------------------------------


def run(
    conn: Any,
    root: Path,
    index: CrosswalkIndex,
    engine: OcrEngine,
    *,
    batch_size: int = 500,
    apply: bool = False,
    rejects_writer: Any = None,
    workers: int = 1,
    index_path: Path | None = None,
) -> RunStats:
    """Enumerate -> resolve/OCR -> load every file under root.

    workers > 1 fans the per-file stage out over a process pool (requires
    index_path -- each worker loads its own index -- and the default
    OpenOcrEngine, rebuilt per worker); the parent stays the single DB writer.
    """
    stats = RunStats()

    if not apply:
        # Dry run: scope preview only. No hashing (no file reads), no OCR, no DB.
        for candidate in enumerate_candidate_files(root):
            stats.seen += 1
            stats.total_bytes += candidate.size_bytes
        return stats

    succeeded = succeeded_source_keys(conn)
    pending = 0

    def handle(candidate_seen: CandidateFile, doc: ProcessedDocument | None) -> None:
        nonlocal pending
        stats.seen += 1
        stats.total_bytes += candidate_seen.size_bytes
        if doc is None:
            stats.skipped_already_done += 1
            return
        result = load_one_record(conn, doc)
        if result.status == STATUS_SUCCEEDED:
            stats.loaded += 1
        elif result.status == STATUS_UNRESOLVED:
            stats.unresolved += 1
            _write_reject(
                rejects_writer, doc.candidate.path, doc.docket_id,
                "crosswalk unresolved", f"{doc.match_confidence:.2f}",
            )
        else:
            stats.failed += 1
            _write_reject(
                rejects_writer, doc.candidate.path, result.docket_id, result.detail or "", ""
            )
        pending += 1
        if pending >= batch_size:
            conn.commit()
            stats.commits += 1
            pending = 0

    if workers <= 1:
        for candidate in enumerate_candidate_files(root):
            handle(candidate, _process_candidate(candidate, engine, index, succeeded))
    else:
        if index_path is None:
            raise ValueError("workers > 1 requires index_path (each worker loads its own index)")
        if not isinstance(engine, OpenOcrEngine):
            raise ValueError("workers > 1 supports only the default OpenOCR engine")
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(
            workers,
            initializer=_init_worker,
            initargs=(str(index_path), succeeded, engine._mode, engine._backend),
        ) as pool:
            # imap (ordered) keeps rejects/logs in tree order; workers still
            # run concurrently, and the parent stays the single DB writer.
            for candidate, doc in pool.imap(
                _worker_process, enumerate_candidate_files(root), chunksize=_POOL_CHUNKSIZE
            ):
                handle(candidate, doc)

    if pending:
        conn.commit()
        stats.commits += 1

    return stats


def _write_reject(
    writer: Any, path: Path, docket_id: str | None, detail: str, confidence: str
) -> None:
    if writer is not None:
        writer.writerow([str(path), docket_id or "", detail, confidence])


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


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
        "--workers",
        type=int,
        default=1,
        help="parallel OCR worker processes (1 = serial; DB writes stay in this process)",
    )
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
        rejects_writer.writerow(["file_path", "docket_id", "detail", "confidence"])

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
            workers=args.workers,
            index_path=args.index_xlsx,
        )
    finally:
        if conn is not None:
            conn.close()
        if rejects_file is not None:
            rejects_file.close()

    for line in stats.summary_lines():
        print(line)
    if not args.apply:
        print("dry run: enumeration only -- no hashing, no OCR, no database writes (use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
