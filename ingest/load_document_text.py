"""Loader for the document-text intake JSONL (Document Intelligence output).

CLI:
    python -m ingest.load_document_text path [--apply] [--batch-size 200]
        [--rejects out.csv]

path is a JSONL file or a directory of *.jsonl files. One object per document
(docs/05-metadata-extraction-spec.md §B):

    {"entry_id": 9000030, "full_text": "...", "text_source": "ocr",
     "di_model": "prebuilt-layout", "di_confidence": 0.98,
     "paragraphs": [{"num": "1", "text": "In February 2023, ..."}]}

Contracts:
- shape_record(obj, line_number) is PURE: validates entry_id (integer),
  full_text (non-empty string), text_source (ocr|native|tag), di_confidence
  (number) and the paragraphs list shape, and computes char_count. Bad
  records raise RowRejected (load_tags' reject pattern; unparseable JSONL
  lines flow through the same path) — they belong in the rejects report,
  never a crash.
- load_texts(conn, records, batch_size) owns the SQL. con.document_text is
  MERGEd on entry_id with COALESCE(source, target) semantics like load_tags,
  EXCEPT full_text/char_count, which always take the incoming value: a
  re-extraction is authoritative for the text itself.
- Paragraphs are replaced WHOLESALE per entry_id (DELETE then INSERT).
  para_num/sort_order define an ordering, so merging a partial paragraph set
  into an existing one would corrupt it; a record that carries "paragraphs"
  owns the entire set (an empty list clears it) and a record without the key
  leaves existing paragraphs untouched. plain_text holds the paragraph text;
  segs_json is a single plain segment (json.dumps([text])) until editorial
  cross-links are added in the console. sort_order is the list index.
- entry_ids not present in con.document are rejected with a clear message
  (the FK insert would fail otherwise); existence is checked per batch in
  IN-list chunks like index_diff. Reject row numbers are 1-based record
  positions in the input stream (files read in sorted order for a directory).
- Without --apply nothing touches the DB: records are parsed + validated and
  a summary is printed.
- Idempotent + resumable: commits every --batch-size records; rerunning the
  same input converges to the same state.
"""

import argparse
import json
import logging
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from common.vocab import match_vocab
from ingest.load_tags import TEXT_SOURCES, RowError, RowRejected, write_rejects

log = logging.getLogger(__name__)

# IN (...) chunk size for the con.document existence check (module-level so
# tests can shrink it to exercise chunking, like index_diff._SCOPE_CHUNK).
_EXISTS_CHUNK = 500


def _reject(row_number: int, field_name: str, message: str, raw: object) -> RowRejected:
    return RowRejected(
        RowError(row_number, field_name, message, "" if raw is None else str(raw))
    )


@dataclass(frozen=True)
class Paragraph:
    """One shaped opinion paragraph: num may be absent in the source."""

    num: str | None
    text: str


@dataclass(frozen=True)
class ShapedText:
    """A validated, typed text record ready for the DB layer.

    paragraphs is None when the record carried no "paragraphs" key (existing
    paragraph rows are left untouched); an empty tuple means the record
    explicitly supplied an empty set (existing rows are cleared).
    """

    entry_id: int
    full_text: str
    char_count: int
    text_source: str
    di_model: str | None
    di_confidence: float | None
    paragraphs: tuple[Paragraph, ...] | None


@dataclass
class LoadStats:
    records_read: int = 0
    texts_upserted: int = 0  # dry run: records that shaped cleanly
    paragraphs_written: int = 0
    commits: int = 0
    rejected: list[RowError] = field(default_factory=list)


# --------------------------------------------------------------------------
# Pure shaping layer
# --------------------------------------------------------------------------


def shape_record(obj: object, line_number: int = 0) -> ShapedText:
    """Shape one JSONL record (docs/05 §B object).

    Pure — no I/O, no DB. Raises RowRejected (carrying a RowError with
    row_number/field/message/raw_value) for: a non-object record,
    missing/non-integer entry_id, missing/empty full_text, text_source not
    one of ocr|native|tag, a non-numeric di_confidence, and a malformed
    paragraphs list. char_count is computed from full_text.
    """
    if not isinstance(obj, dict):
        raise _reject(line_number, "record", "not a JSON object", obj)

    raw_id = obj.get("entry_id")
    entry_id: int | None = None
    if isinstance(raw_id, int) and not isinstance(raw_id, bool):
        entry_id = raw_id
    elif isinstance(raw_id, str) and raw_id.strip():
        try:
            entry_id = int(raw_id.strip())
        except ValueError:
            entry_id = None
    if entry_id is None:
        raise _reject(line_number, "entry_id", "missing or non-integer entry_id", raw_id)

    full_text = obj.get("full_text")
    if not isinstance(full_text, str) or not full_text.strip():
        raise _reject(line_number, "full_text", "missing or empty full_text", full_text)

    raw_source = obj.get("text_source")
    text_source = (
        match_vocab(raw_source, TEXT_SOURCES) if isinstance(raw_source, str) else None
    )
    if text_source is None:
        raise _reject(
            line_number,
            "text_source",
            "must be one of " + "/".join(TEXT_SOURCES),
            raw_source,
        )

    di_model = obj.get("di_model")
    if di_model is not None:
        di_model = str(di_model).strip() or None

    raw_confidence = obj.get("di_confidence")
    di_confidence: float | None = None
    if raw_confidence is not None and raw_confidence != "":
        if isinstance(raw_confidence, bool):
            raise _reject(line_number, "di_confidence", "not a number", raw_confidence)
        try:
            di_confidence = float(raw_confidence)
        except (TypeError, ValueError):
            raise _reject(
                line_number, "di_confidence", "not a number", raw_confidence
            ) from None

    paragraphs: tuple[Paragraph, ...] | None = None
    raw_paragraphs = obj.get("paragraphs")
    if raw_paragraphs is not None:
        if not isinstance(raw_paragraphs, list):
            raise _reject(line_number, "paragraphs", "not a list", raw_paragraphs)
        shaped: list[Paragraph] = []
        for i, item in enumerate(raw_paragraphs):
            if not isinstance(item, dict):
                raise _reject(
                    line_number, "paragraphs", f"item {i} is not an object", item
                )
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise _reject(
                    line_number, "paragraphs", f"item {i} has no text", item.get("text")
                )
            num = item.get("num")
            num = str(num).strip() or None if num is not None else None
            shaped.append(Paragraph(num=num, text=text))
        paragraphs = tuple(shaped)

    return ShapedText(
        entry_id=entry_id,
        full_text=full_text,
        char_count=len(full_text),
        text_source=text_source,
        di_model=di_model,
        di_confidence=di_confidence,
        paragraphs=paragraphs,
    )


# --------------------------------------------------------------------------
# DB layer (parameterized T-SQL only; SQL text is module-constant)
# --------------------------------------------------------------------------

# full_text/char_count always take the incoming value (a re-extraction is
# authoritative for the text itself); the rest keep COALESCE(source, target).
_TEXT_DIRECT_COLS: tuple[str, ...] = ("full_text", "char_count")
_TEXT_COALESCE_COLS: tuple[str, ...] = ("text_source", "di_model", "di_confidence")
_TEXT_COLS: tuple[str, ...] = _TEXT_DIRECT_COLS + _TEXT_COALESCE_COLS

DOCUMENT_TEXT_MERGE_SQL = (
    "MERGE con.document_text AS t\n"
    "USING (SELECT "
    + ", ".join(f"? AS {c}" for c in ("entry_id", *_TEXT_COLS))
    + ") AS s\n"
    "ON (t.entry_id = s.entry_id)\n"
    "WHEN MATCHED THEN UPDATE SET\n    "
    + ",\n    ".join(f"{c} = s.{c}" for c in _TEXT_DIRECT_COLS)
    + ",\n    "
    + ",\n    ".join(f"{c} = COALESCE(s.{c}, t.{c})" for c in _TEXT_COALESCE_COLS)
    + ",\n    extracted_at = SYSUTCDATETIME()\n"
    "WHEN NOT MATCHED THEN INSERT (entry_id, "
    + ", ".join(_TEXT_COLS)
    + ")\n    VALUES (s.entry_id, "
    + ", ".join(f"s.{c}" for c in _TEXT_COLS)
    + ");"
)

PARAGRAPH_DELETE_SQL = "DELETE FROM con.opinion_paragraph WHERE entry_id = ?;"
PARAGRAPH_INSERT_SQL = (
    "INSERT INTO con.opinion_paragraph"
    " (entry_id, para_num, segs_json, plain_text, sort_order)\n"
    "VALUES (?, ?, ?, ?, ?);"
)


def _existing_entry_ids(cursor, entry_ids: list[int]) -> set[int]:
    """Which of entry_ids exist in con.document (IN-list chunks of _EXISTS_CHUNK)."""
    found: set[int] = set()
    for i in range(0, len(entry_ids), _EXISTS_CHUNK):
        chunk = entry_ids[i : i + _EXISTS_CHUNK]
        placeholders = ", ".join("?" for _ in chunk)
        cursor.execute(
            f"SELECT entry_id FROM con.document WHERE entry_id IN ({placeholders})",
            tuple(chunk),
        )
        found.update(int(r[0]) for r in cursor.fetchall())
    return found


def _write_shaped(cursor, shaped: ShapedText) -> int:
    """Emit the MERGE (and paragraph replacement) for one shaped record."""
    params = (shaped.entry_id, *(getattr(shaped, c) for c in _TEXT_COLS))
    cursor.execute(DOCUMENT_TEXT_MERGE_SQL, params)
    if shaped.paragraphs is None:
        return 0
    cursor.execute(PARAGRAPH_DELETE_SQL, (shaped.entry_id,))
    for sort_order, para in enumerate(shaped.paragraphs):
        cursor.execute(
            PARAGRAPH_INSERT_SQL,
            (shaped.entry_id, para.num, json.dumps([para.text]), para.text, sort_order),
        )
    return len(shaped.paragraphs)


def load_texts(conn, records: Iterable[object], *, batch_size: int = 200) -> LoadStats:
    """Shape and upsert text records; commit per batch of batch_size records.

    conn is any pyodbc-shaped connection (tests inject tests.fakes
    FakeConnection). Each batch's entry_ids are existence-checked against
    con.document in IN-list chunks; unknown ids become rejects (the FK would
    fail otherwise), never a crash. Rejected records emit no writes. MERGE +
    wholesale paragraph replacement make reruns converge.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    stats = LoadStats()
    cursor = conn.cursor()
    batch: list[tuple[int, ShapedText]] = []  # (record_number, shaped)

    def flush() -> None:
        if not batch:
            return
        existing = _existing_entry_ids(cursor, sorted({s.entry_id for _, s in batch}))
        wrote = False
        for record_number, shaped in batch:
            if shaped.entry_id not in existing:
                stats.rejected.append(
                    RowError(
                        record_number,
                        "entry_id",
                        "entry_id not in con.document (load the tag export first)",
                        str(shaped.entry_id),
                    )
                )
                continue
            stats.paragraphs_written += _write_shaped(cursor, shaped)
            stats.texts_upserted += 1
            wrote = True
        if wrote:
            conn.commit()
            stats.commits += 1
        batch.clear()

    for record_number, obj in enumerate(records, start=1):
        stats.records_read += 1
        try:
            shaped = shape_record(obj, record_number)
        except RowRejected as exc:
            stats.rejected.append(exc.error)
            continue
        batch.append((record_number, shaped))
        if len(batch) >= batch_size:
            flush()
    flush()
    return stats


def validate_records(records: Iterable[object]) -> LoadStats:
    """Dry-run shaping (no DB): counts and rejects only (the path without --apply)."""
    stats = LoadStats()
    for record_number, obj in enumerate(records, start=1):
        stats.records_read += 1
        try:
            shaped = shape_record(obj, record_number)
        except RowRejected as exc:
            stats.rejected.append(exc.error)
            continue
        stats.texts_upserted += 1
        stats.paragraphs_written += len(shaped.paragraphs or ())
    return stats


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def iter_records(path: Path) -> Iterator[object]:
    """Yield parsed JSONL records from a file, or every *.jsonl in a directory.

    Blank lines are skipped. A line that is not valid JSON is yielded as the
    raw string so it flows through shape_record's reject path (field
    "record") instead of crashing the run.
    """
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    if not files:
        raise SystemExit(f"{path}: no *.jsonl files in directory")
    for file in files:
        with open(file, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    log.warning("%s line %d: not valid JSON", file, line_number)
                    yield line


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.load_document_text",
        description=(
            "Load document-text JSONL (Document Intelligence output) into "
            "con.document_text/con.opinion_paragraph."
        ),
    )
    parser.add_argument("path", type=Path, help="JSONL file, or directory of *.jsonl files")
    parser.add_argument(
        "--apply", action="store_true", help="write to the database (default: dry run)"
    )
    parser.add_argument("--batch-size", type=int, default=200, help="records per commit")
    parser.add_argument("--rejects", type=Path, help="write rejected records to this CSV")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    records = iter_records(args.path)

    if args.apply:
        from common.db import get_connection  # lazy: pyodbc not needed for tests

        conn = get_connection()
        try:
            stats = load_texts(conn, records, batch_size=args.batch_size)
        finally:
            conn.close()
    else:
        stats = validate_records(records)

    if args.rejects is not None:
        write_rejects(args.rejects, stats.rejected)

    print(f"records read:       {stats.records_read}")
    if args.apply:
        print(f"texts upserted:     {stats.texts_upserted}")
        print(f"paragraphs written: {stats.paragraphs_written}")
        print(f"commits:            {stats.commits}")
    else:
        print(f"valid records:      {stats.texts_upserted}")
        print(f"paragraphs parsed:  {stats.paragraphs_written}")
        print("dry run: no database writes (use --apply)")
    print(f"rejected records:   {len(stats.rejected)}")
    for err in stats.rejected[:20]:
        print(f"  reject record {err.row_number}: {err.field}: {err.message} ({err.raw_value!r})")
    if len(stats.rejected) > 20:
        print(f"  ... and {len(stats.rejected) - 20} more (use --rejects for the full list)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
