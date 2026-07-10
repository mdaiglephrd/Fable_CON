# schema/ — database migrations for the `con` schema

Numbered T-SQL files in `schema/migrations/` are applied in filename order by
`schema/migrate.py` and tracked in `con.schema_migrations` (migration_id = file
name, `applied_at` timestamp). Each file runs exactly once: rerunning the
runner applies only files not yet recorded. Every non-fulltext file runs inside
its own transaction — it either fully applies and is recorded, or rolls back.

The runner bootstraps itself: it creates schema `con` and
`con.schema_migrations` when absent, so it works on an empty database.

## Running

Migrations connect via `common.db.get_connection()` (see DESIGN.md env vars).

AAD (managed identity in Azure, `az login` locally):

```bash
export SQL_SERVER=myserver.database.windows.net
export SQL_DATABASE=condb
python -m schema.migrate
```

SQL authentication via a full ODBC string (wins over the pair above):

```bash
export SQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=tcp:myserver.database.windows.net,1433;Database=condb;Uid=myuser;Pwd=...;Encrypt=yes;TrustServerCertificate=no;'
python -m schema.migrate
```

Flags:

- `--dry-run` — list pending migrations; executes nothing (and does not
  bootstrap `schema_migrations`).
- `--skip-fulltext` — skip files with `fulltext` in the name. Use on
  environments without full-text support (localdev/tests). Skipped files stay
  unrecorded, so a later run without the flag applies them.

## Adding a migration

1. Create `schema/migrations/NNNN_short_name.sql` with the next four-digit
   number. Never edit or renumber an already-applied file — the runner tracks
   files by name and runs each once.
2. Separate batches with `GO` on its own line where T-SQL requires it
   (e.g. `CREATE SCHEMA`/`CREATE VIEW` must start a batch).
3. Name constraints and indexes explicitly (`PK_*`, `FK_*`, `CK_*`, `UQ_*`,
   `DF_*`, `IX_*`) — full-text indexes reference PKs by constraint name.
4. Run `python -m schema.migrate --dry-run` to confirm it is picked up, then
   run without the flag.

## Caveats

- **GO splitting**: `GO` is a client-tool batch separator, not T-SQL — pyodbc
  cannot execute it. The runner splits each file on lines containing only `GO`
  (case-insensitive, surrounding whitespace allowed) and executes the batches
  one by one. `GO` inside a longer line (string literal, comment text) is not
  treated as a separator; do not put anything else on a separator line.
- **Full-text**: `CREATE FULLTEXT CATALOG` / `CREATE FULLTEXT INDEX` cannot run
  inside a user transaction, so files with `fulltext` in the name are executed
  with autocommit instead of a per-file transaction (a failure mid-file is not
  rolled back — full-text DDL statements are individually re-runnable after
  fixing the file under a new migration number). The full-text migration is
  kept separate per DESIGN.md so `--skip-fulltext` can omit it.
- **Seeds**: vocabulary seed data in `0001_schema_and_vocab.sql` must stay
  byte-identical to `common/vocab.py` — those exact strings are the codes
  stored in the database.
