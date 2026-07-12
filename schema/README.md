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

## Research layer (v2)

Migrations `0006`–`0009` add the legal-*content* layer for the CON Research
Console on top of the v1 inventory. This layer is purely additive: the v1
tables, seeds, and modules are unchanged. DESIGN.md "RESEARCH LAYER (v2)" is
authoritative for every name, type, FK, CHECK, and index.

- `0006_research_tables.sql` — structure. `ALTER TABLE ADD` the new NULLable
  columns on `con.matter` (contact/officer, project, cost, service-area JSON,
  `docket_family`, LOI/complete/deadline dates, batching cycle, competing
  dockets JSON, `precedent_signal`) and `con.document` (`title`, `text_source`),
  then create all new tables. The five new vocab tables are **created empty in
  0006** (so the FKs declared in 0006 resolve) and **seeded in 0007** — the
  reverse of the v1 structure/data split, because migrations run in filename
  order and 0006 precedes 0007. Tables are ordered so FK targets exist first
  (`con.topic`/`con.statute` before the headnote/citation/deadline tables,
  `con.wiki_article` before `con.wiki_revision`, `con.research_project` before
  `con.project_item`). Self-referencing FKs (`con.topic.parent_topic_id`,
  `con.statute_xref`) are `NO ACTION` because SQL Server forbids cascade cycles.
- `0007_research_vocab.sql` — seeds the five new vocab tables.
- `0008_topic_taxonomy.sql` — seeds the `con.topic` key-number tree.
- `0009_deadline_rules.sql` — seeds `con.deadline_rule`; its rows are kept in
  sync with `common/deadline_rules.py` (single source of truth for the deadline
  offsets and the `/deadlines/calculate` API). Owned/authored separately.

New tables, grouped:

- **Content**: `con.document_text`, `con.opinion`, `con.opinion_paragraph`,
  `con.reporter_citation`, `con.headnote`.
- **Taxonomy + citator**: `con.topic`, `con.document_topic`, `con.citation`.
- **People + timeline**: `con.counsel`, `con.brief`, `con.proceeding_stage`,
  `con.docket_event`.
- **Statutes**: `con.statute`, `con.statute_xref`.
- **Workspace**: `con.wiki_article`, `con.wiki_revision`,
  `con.research_project`, `con.project_item`, `con.saved_alert`,
  `con.deadline_rule`.

New vocabularies (codes are the exact strings, seeded in 0007):

- `con.vocab_treatment` — Followed; Distinguished; Criticized; Reversed;
  Overruled; Cited; Neutral.
- `con.vocab_docket_family` — CON; DET; DET-EQT; DET-ASC; LNR-ASC; LNR-EQT.
- `con.vocab_event_type` — Filing; Order; Opinion; Hearing; Brief; Notice.
- `con.vocab_counsel_side` — Applicant; Petitioner; Respondent; Appellant;
  Appellee; Intervenor; Amicus; Agency.
- `con.vocab_treatment_level` — positive; caution; negative; neutral
  (good-law banner level).

Topic taxonomy (seeded in 0008): roots `CON I`–`CON VII`
(`topic_id` `i`..`vii`, `parent_topic_id` NULL) plus the leaves referenced by
the corpus headnotes/citator — `iii-7`, `iv-11`, `iv-12`, `iv-13`, `iv-15`,
`v-21`, `vi-24`, `vi-25` — each pointing at its root parent. `key_number` uses
the middle-dot separator the corpus prints (e.g. `CON VI · 24`).

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
