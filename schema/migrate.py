"""Migration runner for the `con` schema on Azure SQL Database.

Applies the numbered .sql files in schema/migrations/ in filename order,
tracking each applied file in con.schema_migrations (migration_id = file name).
Each migration file runs inside its own transaction, except *fulltext* files,
which run with autocommit because CREATE FULLTEXT INDEX / CREATE FULLTEXT
CATALOG cannot execute inside a user transaction.

pyodbc cannot execute the `GO` batch separator (it is a client-tool artifact,
not T-SQL), so files are split on lines containing only GO and each batch is
executed separately.

CLI:
    python -m schema.migrate [--dry-run] [--skip-fulltext]

Pure helpers `split_batches` and `pending` are import-safe without pyodbc and
are unit-tested directly; `run_migrations` accepts an injected connection so
tests use tests/fakes.py FakeConnection (no live DB in tests).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# A batch separator is a line containing only GO (any case), with optional
# surrounding whitespace. GO appearing inside a longer line (e.g. in a string
# literal or identifier) does not separate batches.
_GO_LINE = re.compile(r"^\s*GO\s*$", re.IGNORECASE)

_BOOTSTRAP = (
    "IF SCHEMA_ID(N'con') IS NULL EXEC (N'CREATE SCHEMA con');",
    """\
IF OBJECT_ID(N'con.schema_migrations', N'U') IS NULL
    CREATE TABLE con.schema_migrations (
        migration_id NVARCHAR(100) NOT NULL CONSTRAINT PK_schema_migrations PRIMARY KEY,
        applied_at   DATETIME2     NOT NULL
            CONSTRAINT DF_schema_migrations_applied_at DEFAULT SYSUTCDATETIME()
    );""",
)


def split_batches(sql: str) -> list[str]:
    """Split a T-SQL script on GO separator lines into non-empty batches."""
    batches: list[str] = []
    current: list[str] = []

    def flush() -> None:
        batch = "\n".join(current).strip()
        if batch:
            batches.append(batch)
        current.clear()

    for line in sql.splitlines():
        if _GO_LINE.match(line):
            flush()
        else:
            current.append(line)
    flush()
    return batches


def _file_name(f) -> str:
    """File name of a migration entry (Path or str path)."""
    name = getattr(f, "name", None)
    return name if isinstance(name, str) else os.path.basename(str(f))


def pending(applied: set, files: list) -> list:
    """Migration files not yet recorded in `applied`, in filename order."""
    return sorted((f for f in files if _file_name(f) not in applied), key=_file_name)


def is_fulltext(f) -> bool:
    """True when the migration is a full-text file (skippable via --skip-fulltext)."""
    return "fulltext" in _file_name(f).lower()


def ensure_migrations_table(conn) -> None:
    """Create schema con and con.schema_migrations when absent (bootstrap)."""
    cursor = conn.cursor()
    for statement in _BOOTSTRAP:
        cursor.execute(statement)
    conn.commit()


def fetch_applied(conn) -> set[str]:
    """The set of migration_ids already recorded in con.schema_migrations."""
    cursor = conn.cursor()
    cursor.execute("SELECT migration_id FROM con.schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def _record(cursor, migration_id: str) -> None:
    cursor.execute(
        "INSERT INTO con.schema_migrations (migration_id) VALUES (?)", migration_id
    )


def apply_migration(conn, path: Path) -> None:
    """Apply one migration file and record it in con.schema_migrations.

    Regular files run inside a single transaction (commit on success, rollback
    on failure). Full-text files run with autocommit because CREATE FULLTEXT
    CATALOG / CREATE FULLTEXT INDEX cannot run in a user transaction.
    """
    batches = split_batches(Path(path).read_text(encoding="utf-8"))
    if is_fulltext(path):
        previous = getattr(conn, "autocommit", False)
        conn.autocommit = True
        try:
            cursor = conn.cursor()
            for batch in batches:
                cursor.execute(batch)
            _record(cursor, _file_name(path))
        finally:
            conn.autocommit = previous
    else:
        cursor = conn.cursor()
        try:
            for batch in batches:
                cursor.execute(batch)
            _record(cursor, _file_name(path))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def run_migrations(
    conn,
    migrations_dir: Path = MIGRATIONS_DIR,
    *,
    dry_run: bool = False,
    skip_fulltext: bool = False,
) -> list[str]:
    """Apply all pending migrations; returns the file names applied (or, on
    --dry-run, the names that would be applied). `conn` is any pyodbc-like
    connection (tests inject a FakeConnection)."""
    if not dry_run:
        ensure_migrations_table(conn)
        applied = fetch_applied(conn)
    else:
        try:
            applied = fetch_applied(conn)
        except Exception:
            applied = set()  # bootstrap not run yet; a dry run must not create it

    files = sorted(Path(migrations_dir).glob("*.sql"))
    todo = pending(applied, files)
    if skip_fulltext:
        skipped = [f for f in todo if is_fulltext(f)]
        for f in skipped:
            print(f"skip (fulltext): {_file_name(f)}")
        todo = [f for f in todo if not is_fulltext(f)]

    names: list[str] = []
    for f in todo:
        if dry_run:
            print(f"would apply: {_file_name(f)}")
        else:
            print(f"applying: {_file_name(f)}")
            apply_migration(conn, f)
        names.append(_file_name(f))
    if not names:
        print("nothing to apply; database is up to date")
    return names


def main(argv: list[str] | None = None, conn=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m schema.migrate",
        description="Apply pending con-schema migrations to Azure SQL Database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list pending migrations without executing anything",
    )
    parser.add_argument(
        "--skip-fulltext",
        action="store_true",
        help="skip migration files with 'fulltext' in the name "
        "(environments without full-text support)",
    )
    args = parser.parse_args(argv)

    owns_conn = conn is None
    if owns_conn:
        from common.db import get_connection  # deferred: needs pyodbc + env config

        conn = get_connection()
    try:
        applied = run_migrations(
            conn, dry_run=args.dry_run, skip_fulltext=args.skip_fulltext
        )
        verb = "pending" if args.dry_run else "applied"
        print(f"{len(applied)} migration(s) {verb}")
    finally:
        if owns_conn:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
