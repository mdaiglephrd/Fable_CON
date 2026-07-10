"""Fake pyodbc connection/cursor for unit tests. No live DB in tests.

Usage:
    conn = FakeConnection()
    conn.script("SELECT snapshot_id", rows=[(3, "snap-2026-06.jsonl.gz")],
                columns=["snapshot_id", "blob_name"])
    ... run code under test with conn ...
    assert any("MERGE con.matter" in sql for sql, _ in conn.executed)

Each execute() whose SQL contains a scripted substring gets a fresh copy of the
scripted rows for fetchone/fetchall. Unscripted queries return no rows.
"""


class FakeCursor:
    def __init__(self, conn: "FakeConnection"):
        self._conn = conn
        self._rows: list = []
        self.description = None
        self.rowcount = -1

    def execute(self, sql, *params):
        if len(params) == 1 and isinstance(params[0], (list, tuple)):
            params = tuple(params[0])
        self._conn.executed.append((sql, params))
        self._rows = []
        self.description = None
        for substring, columns, rows in self._conn._scripts:
            if substring in sql:
                self._rows = [tuple(r) for r in rows]
                if columns:
                    self.description = [(c, None, None, None, None, None, None) for c in columns]
                break
        self.rowcount = len(self._rows) if self._rows else -1
        return self

    def executemany(self, sql, seq_of_params):
        for params in seq_of_params:
            self.execute(sql, params)
        return self

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def fetchval(self):
        row = self.fetchone()
        return row[0] if row else None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __iter__(self):
        rows, self._rows = self._rows, []
        return iter(rows)


class FakeConnection:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.committed = 0
        self.rolled_back = 0
        self.closed = False
        self._scripts: list[tuple[str, list | None, list]] = []

    def script(self, sql_substring: str, rows: list, columns: list | None = None):
        self._scripts.append((sql_substring, columns, rows))

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True

    def executed_sql(self) -> list[str]:
        return [sql for sql, _ in self.executed]
