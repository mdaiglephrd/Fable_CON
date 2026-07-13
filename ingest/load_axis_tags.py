"""Loader for Harvey's Axis 1-4 tag exports (CSV or JSON).

CLI:
    python -m ingest.load_axis_tags path/to/export.csv [--json] [--apply]
        [--batch-size 500] [--rejects out.csv]

Input: one row per document (one row per entry_id) -- see
docs/08-harvey-tagging-guide.md. Columns: entry_id, axis1, axis2, axis3
(';'-separated in CSV, an array in JSON), axis4 (same). Any of axis1/axis2/
axis3/axis4 may be blank/absent: Harvey may tag axes incrementally across
passes, and a row that omits an axis leaves that axis's existing value(s)
untouched.

Contracts:
- shape_tag_row(row) is PURE: parses entry_id, then validates every value via
  common.axis_validation.validate_tags (unknown axis1/2 value, unknown/
  duplicate axis3/4 code, and the Masterfile-suppresses-Axis-3/4 rule)
  before any DB write. Bad rows raise RowRejected; they belong in the
  rejects report, never a crash and never a guess.
- load_tag_rows(conn, rows) owns the SQL: MERGE con.document_axis1/2
  (single-value, direct overwrite when provided -- Harvey's export is
  authoritative), insert-if-missing con.document_axis3/4 (multi-value,
  never deleted here, matching ingest/load_tags.py's child-table
  convention). con.trg_axis2_masterfile_guard and its Axis 3/4 counterparts
  (schema/migrations/0011) are the DB-side backstop for the same rule this
  module already checks in Python before ever reaching them.
- Idempotent + resumable: commits every --batch-size rows; rerunning the
  same file converges to the same state.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from common.axis_validation import validate_tags
from ingest.load_tags import RowError, RowRejected, write_rejects

# --------------------------------------------------------------------------
# Pure shaping layer
# --------------------------------------------------------------------------


def _reject(row_number: int, field_name: str, message: str, raw: object) -> RowRejected:
    return RowRejected(
        RowError(row_number, field_name, message, "" if raw is None else str(raw))
    )


def _text(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _multi(value: object) -> list[str]:
    """Multi-value column: ';'-separated string (CSV) or list (JSON)."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value]
    else:
        parts = [p.strip() for p in str(value).split(";")]
    out: list[str] = []
    for p in parts:
        if p and p not in out:
            out.append(p)
    return out


@dataclass(frozen=True)
class ShapedTagRow:
    entry_id: int
    axis1: str | None
    axis2: str | None
    axis3_codes: tuple[str, ...]
    axis4_codes: tuple[str, ...]


def shape_tag_row(row: dict, row_number: int = 0) -> ShapedTagRow:
    """Shape and validate one Axis 1-4 tag row. Pure -- no I/O, no DB.

    Raises RowRejected for a missing/non-integer entry_id, or anything
    common.axis_validation.validate_tags rejects (unknown axis1/2 value,
    unknown/duplicate axis3/4 code, or the Masterfile rule).
    """
    raw_entry_id = row.get("entry_id")
    entry_id: int | None = None
    if isinstance(raw_entry_id, int) and not isinstance(raw_entry_id, bool):
        entry_id = raw_entry_id
    else:
        raw = _text(raw_entry_id)
        if raw is not None:
            try:
                entry_id = int(raw)
            except ValueError:
                entry_id = None
    if entry_id is None:
        raise _reject(row_number, "entry_id", "missing or non-integer entry_id", raw_entry_id)

    axis1 = _text(row.get("axis1"))
    axis2 = _text(row.get("axis2"))
    axis3_codes = tuple(_multi(row.get("axis3")))
    axis4_codes = tuple(_multi(row.get("axis4")))

    errors = validate_tags(axis1, axis2, axis3_codes, axis4_codes)
    if errors:
        raise _reject(row_number, "axis_tags", "; ".join(errors), row)

    return ShapedTagRow(
        entry_id=entry_id,
        axis1=axis1,
        axis2=axis2,
        axis3_codes=axis3_codes,
        axis4_codes=axis4_codes,
    )


@dataclass
class LoadStats:
    rows_read: int = 0
    rows_upserted: int = 0
    commits: int = 0
    rejected: list[RowError] = field(default_factory=list)


# --------------------------------------------------------------------------
# DB layer (parameterized T-SQL only; SQL text is module-constant)
# --------------------------------------------------------------------------

AXIS1_MERGE_SQL = (
    "MERGE con.document_axis1 AS t\n"
    "USING (SELECT ? AS entry_id, ? AS value) AS s\n"
    "ON (t.entry_id = s.entry_id)\n"
    "WHEN MATCHED THEN UPDATE SET value = s.value\n"
    "WHEN NOT MATCHED THEN INSERT (entry_id, value) VALUES (s.entry_id, s.value);"
)
AXIS2_MERGE_SQL = (
    "MERGE con.document_axis2 AS t\n"
    "USING (SELECT ? AS entry_id, ? AS value) AS s\n"
    "ON (t.entry_id = s.entry_id)\n"
    "WHEN MATCHED THEN UPDATE SET value = s.value\n"
    "WHEN NOT MATCHED THEN INSERT (entry_id, value) VALUES (s.entry_id, s.value);"
)
AXIS3_INSERT_SQL = (
    "INSERT INTO con.document_axis3 (entry_id, code)\n"
    "SELECT ?, ?\n"
    "WHERE NOT EXISTS (SELECT 1 FROM con.document_axis3 WHERE entry_id = ? AND code = ?);"
)
AXIS4_INSERT_SQL = (
    "INSERT INTO con.document_axis4 (entry_id, code)\n"
    "SELECT ?, ?\n"
    "WHERE NOT EXISTS (SELECT 1 FROM con.document_axis4 WHERE entry_id = ? AND code = ?);"
)


def _write_shaped(cursor, shaped: ShapedTagRow) -> None:
    """Emit the MERGEs/inserts for one shaped row. Axes absent from the row
    (None / empty) are left untouched -- incremental tagging never blanks a
    prior pass's work."""
    if shaped.axis1 is not None:
        cursor.execute(AXIS1_MERGE_SQL, (shaped.entry_id, shaped.axis1))
    if shaped.axis2 is not None:
        cursor.execute(AXIS2_MERGE_SQL, (shaped.entry_id, shaped.axis2))
    for code in shaped.axis3_codes:
        cursor.execute(AXIS3_INSERT_SQL, (shaped.entry_id, code, shaped.entry_id, code))
    for code in shaped.axis4_codes:
        cursor.execute(AXIS4_INSERT_SQL, (shaped.entry_id, code, shaped.entry_id, code))


def load_tag_rows(conn, rows: Iterable[dict], *, batch_size: int = 500) -> LoadStats:
    """Shape, validate, and upsert Axis 1-4 tag rows; commit every batch_size rows.

    conn is any pyodbc-shaped connection (tests inject tests.fakes
    FakeConnection). Rejected rows emit no SQL. Rerunning the same input
    converges: MERGE and insert-if-missing writes are idempotent.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    stats = LoadStats()
    cursor = conn.cursor()
    pending = 0
    for row_number, row in enumerate(rows, start=1):
        stats.rows_read += 1
        try:
            shaped = shape_tag_row(row, row_number)
        except RowRejected as exc:
            stats.rejected.append(exc.error)
            continue
        _write_shaped(cursor, shaped)
        stats.rows_upserted += 1
        pending += 1
        if pending >= batch_size:
            conn.commit()
            stats.commits += 1
            pending = 0
    if pending:
        conn.commit()
        stats.commits += 1
    return stats


def validate_rows(rows: Iterable[dict]) -> LoadStats:
    """Dry-run shaping (no DB): counts and rejects only (the path without --apply)."""
    stats = LoadStats()
    for row_number, row in enumerate(rows, start=1):
        stats.rows_read += 1
        try:
            shape_tag_row(row, row_number)
        except RowRejected as exc:
            stats.rejected.append(exc.error)
            continue
        stats.rows_upserted += 1
    return stats


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def iter_csv_rows(path: Path) -> Iterator[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        yield from csv.DictReader(f)


def iter_json_rows(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit(f"{path}: JSON input must be an array of objects")
    for item in data:
        if not isinstance(item, dict):
            raise SystemExit(f"{path}: JSON array items must be objects")
        yield item


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.load_axis_tags",
        description="Load an Axis 1-4 tag export (CSV or JSON) into con.document_axis1-4.",
    )
    parser.add_argument("path", type=Path, help="export file (CSV, or JSON with --json)")
    parser.add_argument("--json", action="store_true", help="input is a JSON array of objects")
    parser.add_argument(
        "--apply", action="store_true", help="write to the database (default: dry run)"
    )
    parser.add_argument("--batch-size", type=int, default=500, help="rows per commit")
    parser.add_argument("--rejects", type=Path, help="write rejected rows to this CSV")
    args = parser.parse_args(argv)

    rows = iter_json_rows(args.path) if args.json else iter_csv_rows(args.path)

    if args.apply:
        from common.db import get_connection  # lazy: pyodbc not needed for tests

        conn = get_connection()
        try:
            stats = load_tag_rows(conn, rows, batch_size=args.batch_size)
        finally:
            conn.close()
    else:
        stats = validate_rows(rows)

    if args.rejects is not None:
        write_rejects(args.rejects, stats.rejected)

    print(f"rows read:     {stats.rows_read}")
    if args.apply:
        print(f"rows upserted: {stats.rows_upserted}")
        print(f"commits:       {stats.commits}")
    else:
        print(f"valid rows:    {stats.rows_upserted}")
        print("dry run: no database writes (use --apply)")
    print(f"rejected rows: {len(stats.rejected)}")
    for err in stats.rejected[:20]:
        print(f"  reject row {err.row_number}: {err.field}: {err.message} ({err.raw_value!r})")
    if len(stats.rejected) > 20:
        print(f"  ... and {len(stats.rejected) - 20} more (use --rejects for the full list)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
