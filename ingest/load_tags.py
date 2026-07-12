"""Loader for the Laserfiche metadata tag export (CSV or JSON).

CLI:
    python -m ingest.load_tags path/to/export.csv [--json] [--batch-size 500]
        [--default-status Unvalidated] [--rejects out.csv]

Input: one row per document, carrying both the document's fields and its
matter's fields (column names == the field names in DESIGN.md; matter fields
repeated on every document row of that matter). Multi-value columns
(service_type, phases_present, docket_variants, parties — and
completeness_flags, which is stored as a JSON array) are ';'-separated in CSV
and arrays in JSON.

Contracts:
- shape_row(row) is PURE: normalizes the docket via common.docket, checks
  every controlled value via common.vocab (no fuzzy guessing), parses
  ints/floats/dates (ISO 8601 and US m/d/Y accepted). Bad rows raise
  RowRejected carrying a RowError; they belong in the rejects report, never
  a crash and never a guess.
- load_rows(conn, rows) owns the SQL: MERGE con.matter first (document FK),
  then MERGE con.document, then child tables (matter_docket_variant,
  matter_service_type, matter_phase) as insert-if-missing — child rows are
  never deleted. MERGE UPDATE uses COALESCE(source, target) so a sparser
  later row never blanks a richer earlier one, EXCEPT
  validation_status/validated_by/validated_date, which are always taken from
  the row (validation_status falling back to --default-status).
- Idempotent + resumable: commits every --batch-size rows; rerunning the
  same file converges to the same state.
"""

import argparse
import csv
import json
import logging
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from common.docket import normalize_docket
from common.vocab import (
    ACTION_TYPES,
    DECISION_LEVELS,
    DOC_TYPES,
    MATTER_TYPES,
    OUTCOMES,
    PHASES,
    SERVICE_TYPES,
    VALIDATION_STATUSES,
    match_county,
    match_vocab,
)

log = logging.getLogger(__name__)

DOCVIEW_URL_TEMPLATE = (
    "https://weblink.dch.georgia.gov/WebLink/DocView.aspx"
    "?id={entry_id}&dbid=1&repo=HealthPlanning"
)

# Accepted string date shapes beyond ISO 8601 (datetime.fromisoformat).
_US_DATE_FORMAT = "%m/%d/%Y"
_US_DATETIME_FORMATS = (
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y",
)


@dataclass(frozen=True)
class RowError:
    """One rejected input row: which field failed and why."""

    row_number: int
    field: str
    message: str
    raw_value: str


class RowRejected(Exception):
    """Raised by shape_row for a row that must go to the rejects report."""

    def __init__(self, error: RowError):
        super().__init__(f"row {error.row_number}: {error.field}: {error.message}")
        self.error = error


@dataclass(frozen=True)
class ShapedRow:
    """A validated, typed input row ready for the DB layer.

    matter/document map column name -> value (None = not provided; the MERGE
    keeps the existing DB value via COALESCE). document['validation_status']
    may be None, meaning "apply --default-status".
    """

    entry_id: int
    docket_id: str
    matter: dict[str, object]
    document: dict[str, object]
    docket_variants: tuple[str, ...]
    service_types: tuple[str, ...]
    phases: tuple[str, ...]


@dataclass
class LoadStats:
    rows_read: int = 0
    matters_upserted: int = 0  # distinct docket_ids merged
    documents_upserted: int = 0
    commits: int = 0
    rejected: list[RowError] = field(default_factory=list)


# --------------------------------------------------------------------------
# Pure shaping layer
# --------------------------------------------------------------------------


def _reject(row_number: int, field_name: str, message: str, raw: object) -> "RowRejected":
    return RowRejected(
        RowError(row_number, field_name, message, "" if raw is None else str(raw))
    )


def _text(value: object) -> str | None:
    """Trimmed string, or None for missing/blank input."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_int(row_number: int, field_name: str, value: object) -> int | None:
    if value is None or isinstance(value, bool):
        if isinstance(value, bool):
            raise _reject(row_number, field_name, "not an integer", value)
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        raise _reject(row_number, field_name, "not an integer", value) from None


def _parse_float(row_number: int, field_name: str, value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        raise _reject(row_number, field_name, "not a number", value) from None


def _parse_date(row_number: int, field_name: str, value: object) -> date | None:
    """DATE column: accept date/datetime objects, ISO 8601, or m/d/Y strings."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, _US_DATE_FORMAT).date()
    except ValueError:
        raise _reject(row_number, field_name, "unparseable date", value) from None


def _parse_datetime(row_number: int, field_name: str, value: object) -> datetime | None:
    """DATETIME2 column: accept datetime/date objects, ISO 8601, or m/d/Y [time]."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in _US_DATETIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise _reject(row_number, field_name, "unparseable datetime", value)


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


def _vocab(
    row_number: int, field_name: str, value: object, allowed: tuple[str, ...]
) -> str | None:
    raw = _text(value)
    if raw is None:
        return None
    matched = match_vocab(raw, allowed)
    if matched is None:
        raise _reject(row_number, field_name, "not in controlled vocabulary", value)
    return matched


def _validation_status(row_number: int, value: object) -> str | None:
    """Validation status from the row, or None (loader applies --default-status).

    Unlike source metadata, validation_status is loader-owned workflow state:
    a value outside the controlled list (real exports contain e.g.
    "Provisional") means "not yet validated here", so it falls back to the
    default with a warning instead of rejecting the whole row.
    """
    raw = _text(value)
    if raw is None:
        return None
    matched = match_vocab(raw, VALIDATION_STATUSES)
    if matched is None:
        log.warning(
            "row %d: validation_status %r not in %s; using default",
            row_number,
            raw,
            "/".join(VALIDATION_STATUSES),
        )
    return matched


def _parse_decision_level(row_number: int, field_name: str, value: object) -> int | None:
    """Parse a decision level: 3, "3", or the export form "3 Superior Court Decision".

    When a label accompanies the number it must match the vocabulary label for
    that level (a mismatch means mislabeled data, which we reject, not guess).
    """
    raw = _text(value)
    if raw is None:
        return None
    m = re.match(r"^(\d+)\s*(.*)$", raw)
    if not m:
        raise _reject(row_number, field_name, "not a decision level", value)
    level = int(m.group(1))
    if level not in DECISION_LEVELS:
        raise _reject(row_number, field_name, "not a valid decision level (1-5)", value)
    label = m.group(2).strip()
    if label and match_vocab(label, [DECISION_LEVELS[level]]) is None:
        raise _reject(
            row_number,
            field_name,
            f"label does not match level {level} ({DECISION_LEVELS[level]!r})",
            value,
        )
    return level


def shape_row(row: dict, row_number: int = 0) -> ShapedRow:
    """Shape one export row (CSV all-strings dict or JSON typed dict).

    Pure — no I/O, no DB. Raises RowRejected (carrying a RowError with
    row_number/field/message/raw_value) for: missing/invalid entry_id,
    a docket_id that common.docket.normalize_docket cannot normalize, any
    controlled value not matching its vocabulary, and unparseable
    ints/floats/dates. Missing/blank optional fields become None.
    """
    entry_id = _parse_int(row_number, "entry_id", row.get("entry_id"))
    if entry_id is None:
        raise _reject(row_number, "entry_id", "missing entry_id", row.get("entry_id"))

    raw_docket = _text(row.get("docket_id"))
    if raw_docket is None:
        raise _reject(row_number, "docket_id", "missing docket_id", row.get("docket_id"))
    docket = normalize_docket(raw_docket)
    if docket is None:
        raise _reject(
            row_number, "docket_id", "unnormalizable docket", row.get("docket_id")
        )

    variants = set(docket.variants) | set(_multi(row.get("docket_variants")))

    service_types = tuple(
        _vocab(row_number, "service_type", v, SERVICE_TYPES)
        for v in _multi(row.get("service_type"))
    )
    phases_present = tuple(
        _vocab(row_number, "phases_present", v, PHASES)
        for v in _multi(row.get("phases_present"))
    )

    county = None
    raw_county = _text(row.get("county"))
    if raw_county is not None:
        county = match_county(raw_county)
        if county is None:
            raise _reject(row_number, "county", "not a Georgia county", row.get("county"))

    highest_review_level = _parse_decision_level(
        row_number, "highest_review_level", row.get("highest_review_level")
    )
    decision_level = _parse_decision_level(
        row_number, "decision_level", row.get("decision_level")
    )

    completeness_flags = _multi(row.get("completeness_flags"))
    parties = _multi(row.get("parties"))

    matter: dict[str, object] = {
        "applicant": _text(row.get("applicant")),
        "facility": _text(row.get("facility")),
        "matter_type": _vocab(row_number, "matter_type", row.get("matter_type"), MATTER_TYPES),
        "action_type": _vocab(row_number, "action_type", row.get("action_type"), ACTION_TYPES),
        "county": county,
        "service_area": _text(row.get("service_area")),
        "bed_count": _parse_int(row_number, "bed_count", row.get("bed_count")),
        "year_filed": _parse_int(row_number, "year_filed", row.get("year_filed")),
        "final_outcome": _vocab(row_number, "final_outcome", row.get("final_outcome"), OUTCOMES),
        "final_decision_date": _parse_date(
            row_number, "final_decision_date", row.get("final_decision_date")
        ),
        "highest_review_level": highest_review_level,
        "completeness_flags": json.dumps(completeness_flags) if completeness_flags else None,
    }

    docview_url = _text(row.get("docview_url")) or DOCVIEW_URL_TEMPLATE.format(
        entry_id=entry_id
    )

    document: dict[str, object] = {
        "docket_id": docket.canonical,
        "docview_url": docview_url,
        "file_name": _text(row.get("file_name")),
        "doc_type": _vocab(row_number, "doc_type", row.get("doc_type"), DOC_TYPES),
        "decision_level": decision_level,
        "phase": _vocab(row_number, "phase", row.get("phase"), PHASES),
        "page_count": _parse_int(row_number, "page_count", row.get("page_count")),
        "repo_date_created": _parse_datetime(
            row_number, "repo_date_created", row.get("repo_date_created")
        ),
        "repo_date_modified": _parse_datetime(
            row_number, "repo_date_modified", row.get("repo_date_modified")
        ),
        "doc_date": _parse_date(row_number, "doc_date", row.get("doc_date")),
        "decision_maker": _text(row.get("decision_maker")),
        "outcome": _vocab(row_number, "outcome", row.get("outcome"), OUTCOMES),
        "parties": json.dumps(parties) if parties else None,
        "source_path": _text(row.get("source_path")),
        "template_name": _text(row.get("template_name")),
        "ocr_status": _text(row.get("ocr_status")),
        "ocr_confidence": _parse_float(row_number, "ocr_confidence", row.get("ocr_confidence")),
        "validation_status": _validation_status(row_number, row.get("validation_status")),
        "validated_by": _text(row.get("validated_by")),
        "validated_date": _parse_datetime(
            row_number, "validated_date", row.get("validated_date")
        ),
        "duplicate_of": _parse_int(row_number, "duplicate_of", row.get("duplicate_of")),
    }

    return ShapedRow(
        entry_id=entry_id,
        docket_id=docket.canonical,
        matter=matter,
        document=document,
        docket_variants=tuple(sorted(variants)),
        service_types=service_types,
        phases=phases_present,
    )


# --------------------------------------------------------------------------
# DB layer (parameterized T-SQL only; SQL text is module-constant)
# --------------------------------------------------------------------------

_MATTER_COLS: tuple[str, ...] = (
    "applicant",
    "facility",
    "matter_type",
    "action_type",
    "county",
    "service_area",
    "bed_count",
    "year_filed",
    "final_outcome",
    "final_decision_date",
    "highest_review_level",
    "completeness_flags",
)

MATTER_MERGE_SQL = (
    "MERGE con.matter AS t\n"
    "USING (SELECT "
    + ", ".join(f"? AS {c}" for c in ("docket_id", *_MATTER_COLS))
    + ") AS s\n"
    "ON (t.docket_id = s.docket_id)\n"
    "WHEN MATCHED THEN UPDATE SET\n    "
    + ",\n    ".join(f"{c} = COALESCE(s.{c}, t.{c})" for c in _MATTER_COLS)
    + ",\n    updated_at = SYSUTCDATETIME()\n"
    "WHEN NOT MATCHED THEN INSERT (docket_id, "
    + ", ".join(_MATTER_COLS)
    + ")\n    VALUES (s.docket_id, "
    + ", ".join(f"s.{c}" for c in _MATTER_COLS)
    + ");"
)

# COALESCE(source, target) for everything EXCEPT the validation trio, which is
# always taken from the row (validation_status having already been defaulted).
_DOC_COALESCE_COLS: tuple[str, ...] = (
    "docket_id",
    "docview_url",
    "file_name",
    "doc_type",
    "decision_level",
    "phase",
    "page_count",
    "repo_date_created",
    "repo_date_modified",
    "doc_date",
    "decision_maker",
    "outcome",
    "parties",
    "source_path",
    "template_name",
    "ocr_status",
    "ocr_confidence",
    "duplicate_of",
)
_DOC_DIRECT_COLS: tuple[str, ...] = ("validation_status", "validated_by", "validated_date")
_DOC_COLS: tuple[str, ...] = _DOC_COALESCE_COLS + _DOC_DIRECT_COLS

DOCUMENT_MERGE_SQL = (
    "MERGE con.document AS t\n"
    "USING (SELECT "
    + ", ".join(f"? AS {c}" for c in ("entry_id", *_DOC_COLS))
    + ") AS s\n"
    "ON (t.entry_id = s.entry_id)\n"
    "WHEN MATCHED THEN UPDATE SET\n    "
    + ",\n    ".join(f"{c} = COALESCE(s.{c}, t.{c})" for c in _DOC_COALESCE_COLS)
    + ",\n    "
    + ",\n    ".join(f"{c} = s.{c}" for c in _DOC_DIRECT_COLS)
    + ",\n    updated_at = SYSUTCDATETIME()\n"
    "WHEN NOT MATCHED THEN INSERT (entry_id, "
    + ", ".join(_DOC_COLS)
    + ")\n    VALUES (s.entry_id, "
    + ", ".join(f"s.{c}" for c in _DOC_COLS)
    + ");"
)

VARIANT_INSERT_SQL = (
    "INSERT INTO con.matter_docket_variant (docket_id, variant)\n"
    "SELECT ?, ?\n"
    "WHERE NOT EXISTS (SELECT 1 FROM con.matter_docket_variant"
    " WHERE docket_id = ? AND variant = ?);"
)
SERVICE_TYPE_INSERT_SQL = (
    "INSERT INTO con.matter_service_type (docket_id, service_type)\n"
    "SELECT ?, ?\n"
    "WHERE NOT EXISTS (SELECT 1 FROM con.matter_service_type"
    " WHERE docket_id = ? AND service_type = ?);"
)
PHASE_INSERT_SQL = (
    "INSERT INTO con.matter_phase (docket_id, phase)\n"
    "SELECT ?, ?\n"
    "WHERE NOT EXISTS (SELECT 1 FROM con.matter_phase"
    " WHERE docket_id = ? AND phase = ?);"
)


def _write_shaped(cursor, shaped: ShapedRow, default_status: str) -> None:
    """Emit the MERGEs and child inserts for one shaped row (matter first)."""
    matter_params = (shaped.docket_id, *(shaped.matter[c] for c in _MATTER_COLS))
    cursor.execute(MATTER_MERGE_SQL, matter_params)

    doc_values = dict(shaped.document)
    if doc_values["validation_status"] is None:
        doc_values["validation_status"] = default_status
    doc_params = (shaped.entry_id, *(doc_values[c] for c in _DOC_COLS))
    cursor.execute(DOCUMENT_MERGE_SQL, doc_params)

    for variant in shaped.docket_variants:
        cursor.execute(VARIANT_INSERT_SQL, (shaped.docket_id, variant) * 2)
    for st in shaped.service_types:
        cursor.execute(SERVICE_TYPE_INSERT_SQL, (shaped.docket_id, st) * 2)
    for ph in shaped.phases:
        cursor.execute(PHASE_INSERT_SQL, (shaped.docket_id, ph) * 2)


def load_rows(
    conn,
    rows: Iterable[dict],
    *,
    default_status: str = "Unvalidated",
    batch_size: int = 500,
) -> LoadStats:
    """Shape and upsert rows; commit every batch_size successful rows.

    conn is any pyodbc-shaped connection (tests inject tests.fakes
    FakeConnection). Rejected rows emit no SQL, so a partial batch never
    contains half a row. Rerunning the same input converges: MERGE+COALESCE
    upserts and insert-if-missing child rows are idempotent.
    """
    matched_default = match_vocab(default_status, VALIDATION_STATUSES)
    if matched_default is None:
        raise ValueError(f"default_status not a validation status: {default_status!r}")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    stats = LoadStats()
    seen_dockets: set[str] = set()
    cursor = conn.cursor()
    pending = 0
    for row_number, row in enumerate(rows, start=1):
        stats.rows_read += 1
        try:
            shaped = shape_row(row, row_number)
        except RowRejected as exc:
            stats.rejected.append(exc.error)
            continue
        _write_shaped(cursor, shaped, matched_default)
        seen_dockets.add(shaped.docket_id)
        stats.documents_upserted += 1
        pending += 1
        if pending >= batch_size:
            conn.commit()
            stats.commits += 1
            pending = 0
    if pending:
        conn.commit()
        stats.commits += 1
    stats.matters_upserted = len(seen_dockets)
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


def write_rejects(path: Path, rejected: list[RowError]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["row_number", "field", "message", "raw_value"])
        for err in rejected:
            writer.writerow([err.row_number, err.field, err.message, err.raw_value])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.load_tags",
        description="Load a metadata tag export (CSV or JSON) into con.matter/con.document.",
    )
    parser.add_argument("path", type=Path, help="export file (CSV, or JSON with --json)")
    parser.add_argument("--json", action="store_true", help="input is a JSON array of objects")
    parser.add_argument("--batch-size", type=int, default=500, help="rows per commit")
    parser.add_argument(
        "--default-status",
        default="Unvalidated",
        choices=VALIDATION_STATUSES,
        help="validation_status when the row does not provide one",
    )
    parser.add_argument("--rejects", type=Path, help="write rejected rows to this CSV")
    args = parser.parse_args(argv)

    rows = iter_json_rows(args.path) if args.json else iter_csv_rows(args.path)

    from common.db import get_connection  # lazy: pyodbc not needed for tests

    conn = get_connection()
    try:
        stats = load_rows(
            conn, rows, default_status=args.default_status, batch_size=args.batch_size
        )
    finally:
        conn.close()

    if args.rejects is not None:
        write_rejects(args.rejects, stats.rejected)

    print(f"rows read:          {stats.rows_read}")
    print(f"matters upserted:   {stats.matters_upserted}")
    print(f"documents upserted: {stats.documents_upserted}")
    print(f"rejected rows:      {len(stats.rejected)}")
    print(f"commits:            {stats.commits}")
    for err in stats.rejected[:20]:
        print(f"  reject row {err.row_number}: {err.field}: {err.message} ({err.raw_value!r})")
    if len(stats.rejected) > 20:
        print(f"  ... and {len(stats.rejected) - 20} more (use --rejects for the full list)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
