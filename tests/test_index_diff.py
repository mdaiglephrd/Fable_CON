import gzip
import json

import pytest

from ingest.index_diff import (
    SnapshotDiff,
    SnapshotReadStats,
    apply_diff,
    diff_snapshots,
    read_snapshot,
)
from tests.fakes import FakeConnection


def rec(id: int, name="doc", ext=".pdf", path="/CON/1234567", pages=1) -> dict:
    return {"id": id, "name": name, "ext": ext, "path": path, "pages": pages}


class TestDiffSnapshots:
    def test_added_modified_deleted(self):
        old = [rec(1), rec(2), rec(3)]
        new = [rec(1), rec(2, pages=5), rec(4)]
        d = diff_snapshots(iter(old), iter(new))
        assert [r["id"] for r in d.added] == [4]
        assert [(o["id"], n["id"]) for o, n in d.modified] == [(2, 2)]
        assert [r["id"] for r in d.deleted] == [3]

    def test_unchanged_records_produce_nothing(self):
        snap = [rec(1), rec(2, name="other"), rec(3, pages=99)]
        d = diff_snapshots(iter(snap), iter(list(snap)))
        assert d.added == [] and d.modified == [] and d.deleted == []

    @pytest.mark.parametrize(
        "change", [{"name": "renamed"}, {"ext": ".tif"}, {"path": "/moved"}, {"pages": 42}]
    )
    def test_each_field_triggers_modified(self, change):
        old = [rec(1)]
        new = [rec(1, **change)]
        d = diff_snapshots(iter(old), iter(new))
        assert len(d.modified) == 1
        old_rec, new_rec = d.modified[0]
        (field,) = change
        assert old_rec[field] != new_rec[field]

    def test_modified_pair_carries_both_records(self):
        d = diff_snapshots(iter([rec(1, pages=1)]), iter([rec(1, pages=2)]))
        old_rec, new_rec = d.modified[0]
        assert old_rec["pages"] == 1
        assert new_rec["pages"] == 2

    def test_empty_old_all_added(self):
        d = diff_snapshots(iter([]), iter([rec(1), rec(2)]))
        assert [r["id"] for r in d.added] == [1, 2]
        assert d.deleted == []

    def test_empty_new_all_deleted(self):
        d = diff_snapshots(iter([rec(1), rec(2)]), iter([]))
        assert [r["id"] for r in d.deleted] == [1, 2]


class TestReadSnapshot:
    def _write(self, path, lines):
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "wt", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def test_gzip_roundtrip(self, tmp_path):
        path = tmp_path / "snap.jsonl.gz"
        records = [rec(1), rec(2, pages=7)]
        self._write(path, [json.dumps(r) for r in records])
        stats = SnapshotReadStats()
        assert list(read_snapshot(path, stats)) == records
        assert stats.records == 2
        assert stats.malformed == 0

    def test_plain_jsonl_tolerated(self, tmp_path):
        path = tmp_path / "snap.jsonl"
        self._write(path, [json.dumps(rec(5))])
        assert [r["id"] for r in read_snapshot(path)] == [5]

    def test_malformed_lines_skipped_with_warning_count(self, tmp_path, caplog):
        path = tmp_path / "snap.jsonl.gz"
        self._write(
            path,
            [
                json.dumps(rec(1)),
                "{not json at all",            # invalid JSON
                json.dumps([1, 2, 3]),          # not an object
                json.dumps({"name": "no id"}),  # missing id
                json.dumps({"id": "9"}),        # id not an int
                "",                              # blank: ignored, not malformed
                json.dumps(rec(2)),
            ],
        )
        stats = SnapshotReadStats()
        with caplog.at_level("WARNING", logger="ingest.index_diff"):
            good = list(read_snapshot(path, stats))
        assert [r["id"] for r in good] == [1, 2]
        assert stats.malformed == 4
        assert stats.records == 2
        assert len(caplog.records) == 4

    def test_diff_over_real_files(self, tmp_path):
        old_path = tmp_path / "old.jsonl.gz"
        new_path = tmp_path / "new.jsonl.gz"
        self._write(old_path, [json.dumps(r) for r in [rec(1), rec(2)]])
        self._write(new_path, [json.dumps(r) for r in [rec(2, name="renamed"), rec(3)]])
        d = diff_snapshots(read_snapshot(old_path), read_snapshot(new_path))
        assert [r["id"] for r in d.added] == [3]
        assert [n["id"] for _, n in d.modified] == [2]
        assert [r["id"] for r in d.deleted] == [1]


def scripted_conn(document_ids: list[int], snapshot_id: int = 7) -> FakeConnection:
    """FakeConnection with the snapshot-register and scope lookups scripted."""
    conn = FakeConnection()
    # Snapshot not yet registered: SELECT returns nothing (unscripted), the
    # INSERT ... OUTPUT returns the new id.
    conn.script("OUTPUT INSERTED.snapshot_id", rows=[(snapshot_id,)], columns=["snapshot_id"])
    conn.script(
        "SELECT entry_id FROM con.document",
        rows=[(i,) for i in document_ids],
        columns=["entry_id"],
    )
    return conn


class TestApplyDiff:
    def make_diff(self) -> SnapshotDiff:
        return SnapshotDiff(
            added=[rec(10)],
            modified=[(rec(2, pages=1), rec(2, pages=9))],
            deleted=[rec(3)],
        )

    def test_change_log_rows_have_correct_change_type(self):
        conn = scripted_conn(document_ids=[2, 3])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        changes = [p for s, p in conn.executed if "INSERT INTO con.change_log" in s]
        assert [(p[0], p[1]) for p in changes] == [
            (10, "added"),
            (2, "modified"),
            (3, "deleted"),
        ]
        # every change row carries both snapshot ids
        assert all(p[2] == 7 and p[3] == 7 for p in changes)

    def test_added_and_deleted_details_are_full_record(self):
        conn = scripted_conn(document_ids=[2, 3])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        changes = {p[1]: p for s, p in conn.executed if "con.change_log" in s}
        assert json.loads(changes["added"][4]) == rec(10)
        assert json.loads(changes["deleted"][4]) == rec(3)

    def test_modified_details_are_per_field_old_new(self):
        conn = scripted_conn(document_ids=[2, 3])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        changes = {p[1]: p for s, p in conn.executed if "con.change_log" in s}
        assert json.loads(changes["modified"][4]) == {"pages": {"old": 1, "new": 9}}

    def test_in_scope_modified_updates_document_and_flags(self):
        conn = scripted_conn(document_ids=[2, 3])
        stats = apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        changes = {p[1]: p for s, p in conn.executed if "con.change_log" in s}
        # (entry_id, change_type, old_id, new_id, details, in_scope, revalidation_flagged)
        assert changes["modified"][5] == 1
        assert changes["modified"][6] == 1
        updates = [(s, p) for s, p in conn.executed if "UPDATE con.document" in s]
        assert len(updates) == 1
        sql, params = updates[0]
        assert params == (2,)
        assert "validation_status = 'Unvalidated'" in sql
        assert "validated_by = NULL" in sql
        assert "validated_date = NULL" in sql
        assert stats.revalidation_flagged == 1

    def test_out_of_scope_modified_not_updated(self):
        conn = scripted_conn(document_ids=[])  # nothing in con.document
        stats = apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        assert not any("UPDATE con.document" in s for s in conn.executed_sql())
        changes = {p[1]: p for s, p in conn.executed if "con.change_log" in s}
        assert changes["modified"][5] == 0
        assert changes["modified"][6] == 0
        assert stats.revalidation_flagged == 0

    def test_deleted_in_scope_logged_but_never_deleted(self):
        conn = scripted_conn(document_ids=[2, 3])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        changes = {p[1]: p for s, p in conn.executed if "con.change_log" in s}
        assert changes["deleted"][5] == 1  # in scope
        assert changes["deleted"][6] == 0  # but no revalidation
        assert not any("DELETE" in s.upper() for s in conn.executed_sql())

    def test_snapshots_registered_when_absent(self):
        conn = scripted_conn(document_ids=[])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        inserts = [(s, p) for s, p in conn.executed if "INSERT INTO con.index_snapshot" in s]
        assert [p for _, p in inserts] == [("old.jsonl.gz",), ("new.jsonl.gz",)]

    def test_existing_snapshot_not_reinserted(self):
        conn = FakeConnection()
        conn.script("SELECT snapshot_id", rows=[(3,)], columns=["snapshot_id"])
        conn.script("SELECT entry_id FROM con.document", rows=[], columns=["entry_id"])
        stats = apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        assert not any("INSERT INTO con.index_snapshot" in s for s in conn.executed_sql())
        assert stats.old_snapshot_id == 3
        assert stats.new_snapshot_id == 3

    def test_single_commit_at_end(self):
        conn = scripted_conn(document_ids=[2, 3])
        apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        assert conn.committed == 1

    def test_scope_lookup_is_chunked(self, monkeypatch):
        import ingest.index_diff as mod

        monkeypatch.setattr(mod, "_SCOPE_CHUNK", 2)
        diff = SnapshotDiff(added=[rec(i) for i in range(1, 6)])  # 5 ids -> 3 chunks
        conn = scripted_conn(document_ids=[])
        apply_diff(conn, diff, "old.jsonl.gz", "new.jsonl.gz")
        scope_sqls = [s for s in conn.executed_sql() if "SELECT entry_id FROM con.document" in s]
        assert len(scope_sqls) == 3
        assert all("IN (" in s for s in scope_sqls)

    def test_stats_counts(self):
        conn = scripted_conn(document_ids=[2, 3])
        stats = apply_diff(conn, self.make_diff(), "old.jsonl.gz", "new.jsonl.gz")
        assert (stats.added, stats.modified, stats.deleted) == (1, 1, 1)
        assert stats.change_rows == 3
        assert stats.in_scope == 2
