"""Diff two repository index snapshots and log changes to con.change_log.

CLI:
    python -m ingest.index_diff old.jsonl.gz new.jsonl.gz [--apply] [--out diff.json]

Snapshot files are gzipped JSON Lines (plain .jsonl also tolerated, for tests);
each line is {"id": int, "name": str, "ext": str, "path": str, "pages": int}.

Without --apply nothing touches the DB: counts are printed and --out writes
the diff as JSON ({"added": [rec], "modified": [{"old": rec, "new": rec}],
"deleted": [rec]}). With --apply, both snapshots are registered in
con.index_snapshot (if absent), change_log rows are inserted, and in-scope
MODIFIED documents get validation_status reset for re-validation. Deleted
in-scope documents are logged only — never deleted from con.document, and
repo metadata columns are NOT updated here (tag loads own those; the
change_log row carries the new values).

MEMORY CONTRACT: diff_snapshots holds only the OLD snapshot in a dict and
streams the NEW one (the full index is ~1M+ rows; see LESSONS.md).
"""

import argparse
import gzip
import json
import logging
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Fields whose change makes a record "modified".
RECORD_FIELDS: tuple[str, ...] = ("name", "ext", "path", "pages")

# IN (...) chunk size for the con.document scope lookup (module-level so
# tests can shrink it to exercise chunking).
_SCOPE_CHUNK = 1000


@dataclass
class SnapshotReadStats:
    """Per-file read counters; malformed lines are warned about and skipped."""

    lines: int = 0
    records: int = 0
    malformed: int = 0


@dataclass
class SnapshotDiff:
    added: list[dict] = field(default_factory=list)
    modified: list[tuple[dict, dict]] = field(default_factory=list)  # (old, new)
    deleted: list[dict] = field(default_factory=list)


@dataclass
class ApplyStats:
    old_snapshot_id: int
    new_snapshot_id: int
    added: int = 0
    modified: int = 0
    deleted: int = 0
    in_scope: int = 0
    revalidation_flagged: int = 0
    change_rows: int = 0


def read_snapshot(path: str | Path, stats: SnapshotReadStats | None = None) -> Iterator[dict]:
    """Yield snapshot records from a .jsonl.gz (or plain .jsonl) file.

    A line is malformed when it is not JSON, not an object, or has no int
    "id"; malformed lines are counted in stats (when given), logged as
    warnings, and skipped. Blank lines are ignored silently.
    """
    if stats is None:
        stats = SnapshotReadStats()
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stats.lines += 1
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                stats.malformed += 1
                log.warning("%s line %d: not valid JSON, skipped", path, line_number)
                continue
            if not isinstance(record, dict) or not isinstance(record.get("id"), int) \
                    or isinstance(record.get("id"), bool):
                stats.malformed += 1
                log.warning("%s line %d: no integer 'id', skipped", path, line_number)
                continue
            stats.records += 1
            yield record


def diff_snapshots(old_iter: Iterable[dict], new_iter: Iterable[dict]) -> SnapshotDiff:
    """Diff two snapshot record streams by id.

    Builds a dict over OLD only (id -> record), then streams NEW against it:
    each new id pops its old record (marking it seen); ids left over in the
    dict are deleted. Modified = same id with any of name/ext/path/pages
    changed. Ids are assumed unique within a snapshot.
    """
    old_by_id: dict[int, dict] = {rec["id"]: rec for rec in old_iter}
    diff = SnapshotDiff()
    for new_rec in new_iter:
        old_rec = old_by_id.pop(new_rec["id"], None)
        if old_rec is None:
            diff.added.append(new_rec)
        elif any(old_rec.get(f) != new_rec.get(f) for f in RECORD_FIELDS):
            diff.modified.append((old_rec, new_rec))
    diff.deleted = list(old_by_id.values())
    return diff


# --------------------------------------------------------------------------
# DB apply
# --------------------------------------------------------------------------

SNAPSHOT_SELECT_SQL = "SELECT snapshot_id FROM con.index_snapshot WHERE blob_name = ?"
SNAPSHOT_INSERT_SQL = (
    "INSERT INTO con.index_snapshot (blob_name) OUTPUT INSERTED.snapshot_id VALUES (?)"
)
CHANGE_INSERT_SQL = (
    "INSERT INTO con.change_log\n"
    "  (entry_id, change_type, old_snapshot_id, new_snapshot_id,"
    " details, in_scope, revalidation_flagged)\n"
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)
REVALIDATE_UPDATE_SQL = (
    "UPDATE con.document\n"
    "SET validation_status = 'Unvalidated', validated_by = NULL,"
    " validated_date = NULL, updated_at = SYSUTCDATETIME()\n"
    "WHERE entry_id = ?"
)


def _snapshot_id(cursor, blob_name: str) -> int:
    """Return the snapshot_id for blob_name, registering it when absent."""
    cursor.execute(SNAPSHOT_SELECT_SQL, (blob_name,))
    row = cursor.fetchone()
    if row is not None:
        return int(row[0])
    cursor.execute(SNAPSHOT_INSERT_SQL, (blob_name,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"could not register snapshot {blob_name!r}")
    return int(row[0])


def _in_scope_ids(cursor, entry_ids: list[int]) -> set[int]:
    """Which of entry_ids exist in con.document (IN-list chunks of _SCOPE_CHUNK)."""
    found: set[int] = set()
    for i in range(0, len(entry_ids), _SCOPE_CHUNK):
        chunk = entry_ids[i : i + _SCOPE_CHUNK]
        placeholders = ", ".join("?" for _ in chunk)
        cursor.execute(
            f"SELECT entry_id FROM con.document WHERE entry_id IN ({placeholders})",
            tuple(chunk),
        )
        found.update(int(r[0]) for r in cursor.fetchall())
    return found


def _changed_fields(old_rec: dict, new_rec: dict) -> dict:
    return {
        f: {"old": old_rec.get(f), "new": new_rec.get(f)}
        for f in RECORD_FIELDS
        if old_rec.get(f) != new_rec.get(f)
    }


def apply_diff(conn, diff: SnapshotDiff, old_blob_name: str, new_blob_name: str) -> ApplyStats:
    """Write a SnapshotDiff to the database.

    - Registers both snapshots in con.index_snapshot when absent.
    - Inserts one con.change_log row per change. details is JSON: the full
      record for added/deleted, {"field": {"old": ..., "new": ...}} per
      changed field for modified.
    - in_scope = entry_id exists in con.document (batched IN lookups).
    - In-scope MODIFIED documents get validation_status='Unvalidated',
      validated_by/validated_date=NULL, and their change row gets
      revalidation_flagged=1. Deleted in-scope documents are logged only.

    Commit strategy: a SINGLE commit at the end, so a failed apply leaves no
    partial change_log for this snapshot pair — the blob-trigger caller
    (functions/) retries the whole diff, which is idempotent to recompute.
    """
    cursor = conn.cursor()
    old_id = _snapshot_id(cursor, old_blob_name)
    new_id = _snapshot_id(cursor, new_blob_name)
    stats = ApplyStats(old_snapshot_id=old_id, new_snapshot_id=new_id)

    all_ids = sorted(
        {r["id"] for r in diff.added}
        | {n["id"] for _, n in diff.modified}
        | {r["id"] for r in diff.deleted}
    )
    in_scope = _in_scope_ids(cursor, all_ids)
    stats.in_scope = len(in_scope)

    for record in diff.added:
        scoped = record["id"] in in_scope
        cursor.execute(
            CHANGE_INSERT_SQL,
            (record["id"], "added", old_id, new_id, json.dumps(record), int(scoped), 0),
        )
        stats.added += 1
        stats.change_rows += 1

    for old_rec, new_rec in diff.modified:
        scoped = new_rec["id"] in in_scope
        cursor.execute(
            CHANGE_INSERT_SQL,
            (
                new_rec["id"],
                "modified",
                old_id,
                new_id,
                json.dumps(_changed_fields(old_rec, new_rec)),
                int(scoped),
                int(scoped),
            ),
        )
        stats.modified += 1
        stats.change_rows += 1
        if scoped:
            cursor.execute(REVALIDATE_UPDATE_SQL, (new_rec["id"],))
            stats.revalidation_flagged += 1

    for record in diff.deleted:
        scoped = record["id"] in in_scope
        cursor.execute(
            CHANGE_INSERT_SQL,
            (record["id"], "deleted", old_id, new_id, json.dumps(record), int(scoped), 0),
        )
        stats.deleted += 1
        stats.change_rows += 1

    conn.commit()
    return stats


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def diff_to_jsonable(diff: SnapshotDiff) -> dict:
    return {
        "added": diff.added,
        "modified": [{"old": o, "new": n} for o, n in diff.modified],
        "deleted": diff.deleted,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.index_diff",
        description="Diff two index snapshots; optionally apply to the database.",
    )
    parser.add_argument("old_snapshot", type=Path, help="older .jsonl.gz snapshot")
    parser.add_argument("new_snapshot", type=Path, help="newer .jsonl.gz snapshot")
    parser.add_argument(
        "--apply", action="store_true", help="write change_log/index_snapshot rows"
    )
    parser.add_argument("--out", type=Path, help="write the diff as JSON to this file")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    old_stats, new_stats = SnapshotReadStats(), SnapshotReadStats()
    diff = diff_snapshots(
        read_snapshot(args.old_snapshot, old_stats),
        read_snapshot(args.new_snapshot, new_stats),
    )

    print(f"old records:  {old_stats.records} (malformed skipped: {old_stats.malformed})")
    print(f"new records:  {new_stats.records} (malformed skipped: {new_stats.malformed})")
    print(f"added:        {len(diff.added)}")
    print(f"modified:     {len(diff.modified)}")
    print(f"deleted:      {len(diff.deleted)}")

    if args.out is not None:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(diff_to_jsonable(diff), f, indent=2)
        print(f"diff written: {args.out}")

    if args.apply:
        from common.db import get_connection  # lazy: pyodbc not needed for tests

        conn = get_connection()
        try:
            stats = apply_diff(
                conn, diff, args.old_snapshot.name, args.new_snapshot.name
            )
        finally:
            conn.close()
        print(
            f"applied: change rows {stats.change_rows}, in scope {stats.in_scope}, "
            f"revalidation flagged {stats.revalidation_flagged} "
            f"(snapshots {stats.old_snapshot_id} -> {stats.new_snapshot_id})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
