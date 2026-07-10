"""Unit tests for schema/migrate.py. No live DB — uses tests/fakes.py."""

from pathlib import Path

import pytest

from schema.migrate import (
    MIGRATIONS_DIR,
    is_fulltext,
    main,
    pending,
    run_migrations,
    split_batches,
)
from tests.fakes import FakeConnection, FakeCursor

# ---------------------------------------------------------------- split_batches


def test_split_on_go_lines():
    sql = "CREATE TABLE a (x INT);\nGO\nCREATE TABLE b (y INT);\nGO\n"
    assert split_batches(sql) == ["CREATE TABLE a (x INT);", "CREATE TABLE b (y INT);"]


def test_split_go_case_insensitive():
    sql = "SELECT 1\ngo\nSELECT 2\nGo\nSELECT 3"
    assert split_batches(sql) == ["SELECT 1", "SELECT 2", "SELECT 3"]


def test_split_go_with_surrounding_whitespace():
    sql = "SELECT 1\nGO   \nSELECT 2\n\tGO\t\nSELECT 3\n  go  \nSELECT 4"
    assert split_batches(sql) == ["SELECT 1", "SELECT 2", "SELECT 3", "SELECT 4"]


def test_go_inside_a_longer_line_is_not_a_separator():
    sql = "PRINT 'GO';\nSELECT category -- GO faster\nGO\nSELECT 2"
    assert split_batches(sql) == ["PRINT 'GO';\nSELECT category -- GO faster", "SELECT 2"]


def test_empty_batches_are_dropped():
    sql = "GO\n\nGO\nSELECT 1\nGO\nGO\n   \nGO"
    assert split_batches(sql) == ["SELECT 1"]


def test_no_go_yields_single_batch():
    assert split_batches("SELECT 1;\nSELECT 2;") == ["SELECT 1;\nSELECT 2;"]


def test_empty_script_yields_no_batches():
    assert split_batches("") == []
    assert split_batches("\nGO\n") == []


# --------------------------------------------------------------------- pending


def test_pending_orders_by_filename():
    files = [Path("m/0003_c.sql"), Path("m/0001_a.sql"), Path("m/0002_b.sql")]
    assert [f.name for f in pending(set(), files)] == [
        "0001_a.sql",
        "0002_b.sql",
        "0003_c.sql",
    ]


def test_pending_filters_applied_and_accepts_strings():
    files = ["0002_b.sql", "0001_a.sql", "0003_c.sql"]
    assert pending({"0001_a.sql", "0003_c.sql"}, files) == ["0002_b.sql"]


def test_is_fulltext():
    assert is_fulltext(Path("0005_fulltext.sql"))
    assert is_fulltext("0007_more_FULLTEXT_stuff.sql")
    assert not is_fulltext(Path("0002_core_tables.sql"))


# -------------------------------------------------------------- run_migrations


def write_migration(directory: Path, name: str, sql: str) -> Path:
    path = directory / name
    path.write_text(sql, encoding="utf-8")
    return path


def test_run_applies_pending_in_filename_order(tmp_path):
    # Created out of order on purpose; filename order must win.
    write_migration(tmp_path, "0002_second.sql", "SELECT 'second'\nGO\n")
    write_migration(tmp_path, "0001_first.sql", "SELECT 'first'\nGO\n")
    conn = FakeConnection()

    applied = run_migrations(conn, tmp_path)

    assert applied == ["0001_first.sql", "0002_second.sql"]
    sqls = conn.executed_sql()
    assert sqls.index("SELECT 'first'") < sqls.index("SELECT 'second'")
    records = [p for s, p in conn.executed if "INSERT INTO con.schema_migrations" in s]
    assert records == [("0001_first.sql",), ("0002_second.sql",)]
    # bootstrap commit + one commit per migration file
    assert conn.committed == 3


def test_already_applied_migrations_are_skipped(tmp_path):
    write_migration(tmp_path, "0001_first.sql", "SELECT 'first'\nGO\n")
    write_migration(tmp_path, "0002_second.sql", "SELECT 'second'\nGO\n")
    conn = FakeConnection()
    conn.script(
        "SELECT migration_id", rows=[("0001_first.sql",)], columns=["migration_id"]
    )

    applied = run_migrations(conn, tmp_path)

    assert applied == ["0002_second.sql"]
    sqls = conn.executed_sql()
    assert "SELECT 'first'" not in sqls
    assert "SELECT 'second'" in sqls


def test_skip_fulltext_filters_fulltext_files(tmp_path):
    write_migration(tmp_path, "0001_core.sql", "SELECT 'core'\nGO\n")
    write_migration(tmp_path, "0002_fulltext.sql", "CREATE FULLTEXT CATALOG con_fts;\nGO\n")
    conn = FakeConnection()

    applied = run_migrations(conn, tmp_path, skip_fulltext=True)

    assert applied == ["0001_core.sql"]
    assert not any("FULLTEXT" in s for s in conn.executed_sql())
    # Skipped, not recorded: a later run without the flag still applies it.
    records = [p for s, p in conn.executed if "INSERT INTO con.schema_migrations" in s]
    assert records == [("0001_core.sql",)]


def test_fulltext_file_runs_with_autocommit(tmp_path):
    write_migration(tmp_path, "0001_fulltext.sql", "CREATE FULLTEXT CATALOG con_fts;\nGO\n")
    conn = FakeConnection()

    applied = run_migrations(conn, tmp_path)

    assert applied == ["0001_fulltext.sql"]
    assert "CREATE FULLTEXT CATALOG con_fts;" in conn.executed_sql()
    records = [p for s, p in conn.executed if "INSERT INTO con.schema_migrations" in s]
    assert records == [("0001_fulltext.sql",)]
    assert conn.autocommit is False  # restored after the file
    assert conn.committed == 1  # bootstrap only; fulltext file never calls commit()


def test_dry_run_executes_nothing(tmp_path):
    write_migration(tmp_path, "0001_first.sql", "SELECT 'first'\nGO\n")
    conn = FakeConnection()

    applied = run_migrations(conn, tmp_path, dry_run=True)

    assert applied == ["0001_first.sql"]
    sqls = conn.executed_sql()
    assert "SELECT 'first'" not in sqls
    assert not any("INSERT INTO con.schema_migrations" in s for s in sqls)
    assert not any("CREATE TABLE con.schema_migrations" in s for s in sqls)
    assert conn.committed == 0


class FailingConnection(FakeConnection):
    """FakeConnection whose cursors raise when the SQL contains a marker."""

    def __init__(self, fail_on: str):
        super().__init__()
        self.fail_on = fail_on

    def cursor(self):
        conn = self

        class Cursor(FakeCursor):
            def execute(self, sql, *params):
                super().execute(sql, *params)
                if conn.fail_on in sql:
                    raise RuntimeError(f"boom: {conn.fail_on}")
                return self

        return Cursor(self)


def test_failed_migration_rolls_back_and_is_not_recorded(tmp_path):
    write_migration(tmp_path, "0001_bad.sql", "SELECT 'ok'\nGO\nSELECT 'BOOM'\nGO\n")
    conn = FailingConnection(fail_on="BOOM")

    with pytest.raises(RuntimeError):
        run_migrations(conn, tmp_path)

    assert conn.rolled_back == 1
    assert not any(
        "INSERT INTO con.schema_migrations" in s for s in conn.executed_sql()
    )


# ------------------------------------------------- CLI + real migration files


def test_main_with_injected_connection_applies_real_migrations():
    conn = FakeConnection()
    assert main(["--skip-fulltext"], conn=conn) == 0
    sqls = conn.executed_sql()
    assert any("CREATE TABLE con.matter" in s for s in sqls)
    assert any("CREATE TABLE con.weekly_report_event" in s for s in sqls)
    assert not any("FULLTEXT" in s for s in sqls)
    records = [p[0] for s, p in conn.executed if "INSERT INTO con.schema_migrations" in s]
    assert records == sorted(records)
    assert "0005_fulltext.sql" not in records
    assert conn.closed is False  # injected connections are not closed by main


def test_real_migration_files_split_into_nonempty_batches():
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert len(files) == 5
    for f in files:
        batches = split_batches(f.read_text(encoding="utf-8"))
        assert batches, f"{f.name} produced no batches"
        for batch in batches:
            assert batch.strip()
            assert not any(
                line.strip().upper() == "GO" for line in batch.splitlines()
            ), f"unsplit GO left inside a batch of {f.name}"
