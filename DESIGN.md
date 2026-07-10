# DESIGN — internal contracts (authoritative for all modules)

This file is the single source of truth for names, shapes, and interfaces shared
across modules. If a module needs something that contradicts this file, fix this
file first.

## Stack

- Python 3.11, Azure SQL Database (T-SQL), pyodbc (ODBC Driver 18).
- Packages at repo root: `common/`, `ingest/`, `api/`, `schema/` (SQL + runner),
  `functions/` (Azure Functions app root), `infra/` (Bicep), `m365/`, `docs/`, `tests/`.
- No ORM. Thin helpers in `common/db.py`. Parameterized T-SQL only.
- All config from environment variables (see `.env.example`); secrets come from
  Key Vault / App Settings in Azure, `.env` locally. Never hardcode.

## Database schema (schema name: `con`)

All tables live in schema `con`. Migrations are numbered SQL files in `schema/migrations/`
applied by `schema/migrate.py`, tracked in `con.schema_migrations(migration_id NVARCHAR(100) PK, applied_at)`.

### Vocabulary tables (seeded by migrations; codes are the exact human-readable strings)

- `con.vocab_service_type(code NVARCHAR(100) PK)` — 26 values (see common/vocab.py SERVICE_TYPES)
- `con.vocab_matter_type(code NVARCHAR(60) PK)` — CON Application; Determination/Reviewability (DET); Administrative Appeal; Judicial Review; Other/Administrative
- `con.vocab_action_type(code NVARCHAR(60) PK)` — New service/facility; Bed or capacity addition; Relocation; Replacement; Change of ownership (CHOW); Cost overrun/capital amendment; Determination request; Other
- `con.vocab_doc_type(code NVARCHAR(60) PK)` — 14 values (see DOC_TYPES)
- `con.vocab_phase(code NVARCHAR(80) PK)` — 5 values (see PHASES)
- `con.vocab_outcome(code NVARCHAR(60) PK)` — 13 values (see OUTCOMES), used by both document.outcome and matter.final_outcome
- `con.vocab_decision_level(level TINYINT PK, label NVARCHAR(60))` — 1 Desk Decision; 2 Hearing Officer Decision; 3 Superior Court Decision; 4 Appellate Court Decision; 5 Initial Application
- `con.county(name NVARCHAR(30) PK)` — the 159 Georgia counties, Title Case ("Ben Hill", "DeKalb", "McDuffie")

### Core tables

```
con.matter (
  docket_id            NVARCHAR(50)  PK,          -- canonical, from common/docket.py
  applicant            NVARCHAR(500),
  facility             NVARCHAR(500),
  matter_type          NVARCHAR(60)  FK->vocab_matter_type,
  action_type          NVARCHAR(60)  FK->vocab_action_type,
  county               NVARCHAR(30)  FK->con.county,
  service_area         NVARCHAR(200),
  bed_count            INT,
  year_filed           SMALLINT,
  final_outcome        NVARCHAR(60)  FK->vocab_outcome,
  final_decision_date  DATE,
  highest_review_level TINYINT       FK->vocab_decision_level,
  completeness_flags   NVARCHAR(MAX) CHECK ISJSON,  -- JSON array of flag strings
  created_at DATETIME2 DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 DEFAULT SYSUTCDATETIME()
)
con.matter_docket_variant (docket_id FK->matter ON DELETE CASCADE, variant NVARCHAR(50), PK(docket_id, variant))
con.matter_service_type   (docket_id FK->matter ON DELETE CASCADE, service_type NVARCHAR(100) FK->vocab_service_type, PK(docket_id, service_type))
con.matter_phase          (docket_id FK->matter ON DELETE CASCADE, phase NVARCHAR(80) FK->vocab_phase, PK(docket_id, phase))  -- phases_present

con.document (
  entry_id           INT PK,                       -- Laserfiche Entry ID
  docket_id          NVARCHAR(50) FK->matter,
  docview_url        NVARCHAR(400),
  file_name          NVARCHAR(400),
  doc_type           NVARCHAR(60) FK->vocab_doc_type,
  decision_level     TINYINT      FK->vocab_decision_level,
  phase              NVARCHAR(80) FK->vocab_phase,
  page_count         INT,
  repo_date_created  DATETIME2,
  repo_date_modified DATETIME2,
  doc_date           DATE,
  decision_maker     NVARCHAR(200),
  outcome            NVARCHAR(60) FK->vocab_outcome,
  parties            NVARCHAR(MAX) CHECK ISJSON,   -- JSON array of party name strings
  source_path        NVARCHAR(1000),
  template_name      NVARCHAR(200),
  ocr_status         NVARCHAR(30),
  ocr_confidence     DECIMAL(5,2),
  validation_status  NVARCHAR(20) NOT NULL DEFAULT 'Unvalidated'
                     CHECK IN ('Unvalidated','Validated','Corrected','Rejected'),
  validated_by       NVARCHAR(100),
  validated_date     DATETIME2,
  duplicate_of       INT FK->con.document(entry_id),
  created_at / updated_at DATETIME2 as above
)

con.index_snapshot (
  snapshot_id  INT IDENTITY PK,
  blob_name    NVARCHAR(400) NOT NULL UNIQUE,   -- file or blob name of the .jsonl.gz
  snapshot_date DATE,
  entry_count  INT,
  max_entry_id INT,
  processed_at DATETIME2 DEFAULT SYSUTCDATETIME()
)

con.change_log (
  change_id        BIGINT IDENTITY PK,
  entry_id         INT NOT NULL,
  change_type      NVARCHAR(10) NOT NULL CHECK IN ('added','modified','deleted'),
  old_snapshot_id  INT FK->index_snapshot,
  new_snapshot_id  INT FK->index_snapshot,
  details          NVARCHAR(MAX) CHECK ISJSON,  -- {"field": {"old":..., "new":...}} or full record for added/deleted
  in_scope         BIT NOT NULL DEFAULT 0,      -- entry_id exists in con.document
  revalidation_flagged BIT NOT NULL DEFAULT 0,  -- we reset document.validation_status
  detected_at      DATETIME2 DEFAULT SYSUTCDATETIME()
)

con.watchlist (
  watch_id   INT IDENTITY PK,
  docket_id  NVARCHAR(50) NULL FK->matter,
  entry_id   INT NULL,
  path_prefix NVARCHAR(400) NULL,   -- watch new repo docs under a folder path
  reason     NVARCHAR(400),
  created_by NVARCHAR(100),
  active     BIT NOT NULL DEFAULT 1,
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
)

con.weekly_report_event (
  event_id     BIGINT IDENTITY PK,
  report_date  DATE NOT NULL,
  report_file  NVARCHAR(400),
  section      NVARCHAR(40) NOT NULL CHECK IN ('LETTER_OF_INTENT','NEW_APPLICATION',
                'WITHDRAWN_APPLICATION','PENDING_APPLICATION','APPROVED','DENIED',
                'APPEALED','LETTER_OF_DETERMINATION'),
  docket_id    NVARCHAR(50) NULL,          -- canonical; NULL when no docket in the entry
  docket_raw   NVARCHAR(100) NULL,         -- docket exactly as printed
  applicant    NVARCHAR(500),
  project_description NVARCHAR(MAX),
  county       NVARCHAR(30),
  cost         DECIMAL(18,2),
  opposition   NVARCHAR(200),              -- opposition status as printed
  filing_date  DATE,
  decision_deadline DATE,
  decision_date DATE,
  raw_text     NVARCHAR(MAX),
  dedupe_hash  CHAR(64) NOT NULL,          -- sha256 of (report_date|section|docket_raw|raw_text)
  ingested_at  DATETIME2 DEFAULT SYSUTCDATETIME(),
  UNIQUE (dedupe_hash)
)

con.processed_blob (
  blob_name    NVARCHAR(400) PK,   -- "container/name"
  processed_at DATETIME2 DEFAULT SYSUTCDATETIME(),
  status       NVARCHAR(20) NOT NULL,   -- 'succeeded' | 'failed'
  detail       NVARCHAR(MAX)
)
```

### Indexes (beyond PKs)

document: (docket_id), (doc_type), (phase), (outcome), (validation_status), (doc_date)
matter: (county), (year_filed), (final_outcome), (matter_type), (action_type)
matter_service_type: (service_type)
change_log: (entry_id), (detected_at), (change_type)
weekly_report_event: (docket_id), (report_date), (section)

### Full-text search

Full-text catalog `con_fts`; full-text indexes on:
- `con.matter(applicant, facility, service_area)`
- `con.document(file_name, decision_maker, source_path)`
- `con.weekly_report_event(applicant, project_description)`
Full-text migration is separate (`schema/migrations/*_fulltext.sql`) because
localdev/tests can't run it; migrate.py applies it but tolerates absence only via
explicit `--skip-fulltext` flag.

## common/ interfaces

### common/docket.py

```python
@dataclass(frozen=True)
class DocketMatch:
    canonical: str      # e.g. "CON-1234567", "DET-2020-014", "LNR-2023-008", "BEN-HILL-45"
    kind: str           # 'CON' | 'DET' | 'LNR' | 'COUNTY'
    variants: tuple[str, ...]  # includes the raw form as seen, plus common alternates
    raw: str            # the exact substring matched

def normalize_docket(raw: str) -> DocketMatch | None   # whole-string (tolerates labels like "Docket No.")
def extract_dockets(text: str) -> list[DocketMatch]    # scan free text (filenames, PDF text)
```

Canonicalization rules:
- Uppercase; separators (space, underscore, period, en-dash) become a single hyphen.
- `CON#######` / `CON-#######` -> `CON-#######` (digits preserved verbatim, incl. leading zeros).
- Legacy `GA-#######` (embedded in names) -> canonical `CON-#######` with the `GA-...` form
  kept as a variant. ASSUMPTION: GA-number space == CON-number space; single constant
  `GA_MAPS_TO_CON = True` in docket.py to flip.
- `DET...` -> `DET-` + the rest, internal separators normalized to hyphens.
- `LNR-...` -> `LNR-` + rest, same normalization.
- County legacy `FULTON-213`, `Ben Hill 45` -> `<COUNTY>-<N>` with multi-word counties
  hyphenated: `BEN-HILL-45`. County part must match one of the 159 counties.
- Variants always include: the raw matched string, the canonical, and the no-hyphen
  compact form for CON/DET (e.g. `CON1234567`).

### common/vocab.py

Constants: `SERVICE_TYPES`, `MATTER_TYPES`, `ACTION_TYPES`, `DOC_TYPES`, `PHASES`,
`OUTCOMES`, `VALIDATION_STATUSES`, `DECISION_LEVELS: dict[int, str]`, `COUNTIES` (159, Title Case),
`REPORT_SECTIONS`. Helper `match_county(raw: str) -> str | None` (case/space tolerant).
Helper `match_vocab(value: str, allowed: Sequence[str]) -> str | None` (exact after
case/whitespace normalization; no fuzzy guessing).

### common/db.py

```python
def get_connection() -> pyodbc.Connection
    # SQL_CONNECTION_STRING wins if set; else builds ODBC 18 string from
    # SQL_SERVER + SQL_DATABASE with Authentication=ActiveDirectoryDefault.
    # autocommit=False.
def utcnow_iso() -> str
```
Keep this file tiny. Modules own their SQL.

## Module contracts

### ingest/load_tags.py

- CLI: `python -m ingest.load_tags path/to/export.csv [--json] [--batch-size 500] [--default-status Unvalidated] [--rejects out.csv]`
- Reads CSV (utf-8-sig) or JSON (array of objects). Column names == field names in this
  file (matter fields may be repeated per document row). Multi-value columns
  (`service_type`, `phases_present`, `docket_variants`, `parties`) are `;`-separated
  in CSV, arrays in JSON.
- Pure function `shape_row(row: dict) -> ShapedRow` (normalizes docket, vocab-checks,
  parses dates/ints) raises/collects `RowError`; DB writes via `MERGE` upserts
  (matter first, then document; child tables via delete-and-insert per matter batch...
  actually per-row set-union: INSERT missing variant/service/phase rows, never delete).
- Idempotent + resumable: batch commit every `--batch-size` rows; rerunning converges.
- Rows with an unknown/missing entry_id or unparseable docket -> rejects report, not a crash.
- validation_status: taken from the row when present+valid, else `--default-status`.
- Prints a summary: rows read, matters upserted, documents upserted, rejects.

### ingest/index_diff.py

- CLI: `python -m ingest.index_diff old.jsonl.gz new.jsonl.gz [--apply] [--out diff.json]`
  Without `--apply`, prints/writes the diff only (no DB). With `--apply`, writes
  change_log + registers con.index_snapshot rows + flags re-validation.
- Snapshot line format: `{"id": int, "name": str, "ext": str, "path": str, "pages": int}`.
- `diff_snapshots(old_iter, new_iter) -> SnapshotDiff` — memory: dict over OLD only;
  streams NEW. added: list[record], modified: list[(old, new)] (any of name/ext/path/pages
  changed), deleted: list[record].
- `apply_diff(conn, diff, old_blob_name, new_blob_name)`:
  in_scope = entry_id IN con.document. For in-scope modified docs, set
  document.validation_status='Unvalidated', validated_by/validated_date=NULL and
  set revalidation_flagged=1 on the change row. Also updates document.repo metadata?
  NO — repo fields update only via tag loads; the change_log carries the new values.
- Deleted in-scope documents are NOT deleted from con.document; only logged.

### ingest/weekly_report_parser.py

- CLI: `python -m ingest.weekly_report_parser report.pdf [--apply] [--out events.json]`
- `extract_text(pdf_path) -> str` (pdfplumber; page texts joined with form-feed \f).
- `parse_report_text(text, report_file="") -> ReportParse` — PURE, unit-testable.
  `ReportParse(report_date: date | None, events: list[ReportEvent], warnings: list[str])`
  `ReportEvent(section, docket_raw, docket_id, applicant, project_description, county,
   cost, opposition, filing_date, decision_deadline, decision_date, raw_text)`
- Section header mapping (case-insensitive, tolerant):
  "Letters of Intent"->LETTER_OF_INTENT, "New Applications"/"Applications Received"->NEW_APPLICATION,
  "Withdrawn"->WITHDRAWN_APPLICATION, "Pending Applications"->PENDING_APPLICATION,
  "Recently Approved"->APPROVED, "Recently Denied"->DENIED,
  "Appealed Projects"->APPEALED, "Letters of Determination"->LETTER_OF_DETERMINATION.
- `load_events(conn, parse, report_file) -> LoadStats`: INSERT events (skip on dedupe_hash
  conflict), create stub matters for unknown canonical dockets
  (completeness_flags=["stub_from_weekly_report"]) so events join to matters. Never
  overwrites populated matter fields.
- Built against tests/fixtures/sample_weekly_report.pdf (synthetic, generated by
  tests/fixtures/make_weekly_report_fixture.py using reportlab). Will be re-tuned
  against the real DCH sample when provided.

### functions/ (Azure Functions app root; Python v2 model, single function_app.py)

- Blob trigger container `index-snapshots` -> download new blob, find previous snapshot
  (con.index_snapshot highest snapshot_id), download it from same container, run
  diff+apply. First-ever snapshot: register as baseline, no diff.
- Blob trigger container `weekly-reports` -> parse + load_events.
- Timer (daily, CRON from env or default `0 0 6 * * *`) -> sweep both containers,
  process any blob missing from con.processed_blob (catch-up for missed events).
- Every blob processing wrapped: record con.processed_blob success/failure.
- Uses AzureWebJobsStorage / STORAGE_CONNECTION or managed identity via env.
- Shared code: deploy script stages common/ + ingest/ into the app folder (see functions/deploy.sh).

### api/ (FastAPI, app in api/main.py)

Endpoints:
- GET /health
- GET /vocab/{name}
- GET /matters — query params for every matter field (incl. service_type, phase — via child tables), q (full-text), paging (limit/offset), sort
- GET /matters/{docket_id} — matter + variants + service types + phases + its documents + weekly events
- GET /documents — query params for every document field, paging
- GET /documents/{entry_id}
- GET /dockets/{docket_id}/documents — accepts any variant, resolves via normalize + matter_docket_variant
- GET /search?q=&scope=matters|documents|events|all — SQL full-text (CONTAINSTABLE), falls back to LIKE when full-text unavailable (flag env FULLTEXT_ENABLED)
- GET /changes?since=&change_type=&in_scope=
- GET /watchlist, POST /watchlist, DELETE /watchlist/{id}
- GET /reports/events?docket_id=&section=&since=
- GET /search/semantic?q=&k= — Azure AI Search hybrid (semantic + vector when configured)
- POST /ask {"question": str} -> {"answer": str, "citations": [{entry_id|docket_id, docview_url, snippet}]} — retrieve from AI Search, answer via Azure OpenAI chat; refuses (answer explains) when SEARCH/AOAI env not configured.
- api/search_sync.py — CLI to create/update the AI Search index `con-records` and push
  rows (record_type: 'matter'|'document'|'event'; denormalized matter fields on document
  records; vector field `content_vector` filled via Azure OpenAI embeddings when
  AZURE_OPENAI_* configured, else omitted; semantic configuration always defined).
- Auth: none in code; platform-level Entra (App Service Easy Auth). Documented.

## Environment variables (canonical names — use exactly these)

```
SQL_CONNECTION_STRING   # full ODBC string (optional; wins over the pair below)
SQL_SERVER              # e.g. myserver.database.windows.net
SQL_DATABASE            # e.g. condb
STORAGE_CONNECTION      # Azure Storage connection string (functions local dev)
STORAGE_ACCOUNT_URL     # https://<account>.blob.core.windows.net — managed-identity alternative
                        # to STORAGE_CONNECTION (fallback order: STORAGE_CONNECTION ->
                        # AzureWebJobsStorage -> STORAGE_ACCOUNT_URL + DefaultAzureCredential)
SNAPSHOT_CONTAINER=index-snapshots
REPORT_CONTAINER=weekly-reports
FULLTEXT_ENABLED=true
SEARCH_ENDPOINT         # https://<name>.search.windows.net
SEARCH_API_KEY          # optional; DefaultAzureCredential used when absent
SEARCH_INDEX=con-records
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY    # optional; AAD when absent
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
KEY_VAULT_URI           # optional; when set, missing secrets are read from Key Vault
```

## Conventions

- Do NOT edit root shared files (pyproject.toml, requirements*.txt, README.md,
  .env.example, LESSONS.md, DESIGN.md) from module work — report needed changes instead.
- Tests: one file per module in tests/ (test_docket.py, test_vocab.py, test_load_tags.py,
  test_index_diff.py, test_weekly_report_parser.py, test_api.py). Fixtures in tests/fixtures/.
- DB-dependent logic is tested with fake connections (tests/fakes.py FakeConnection
  capturing executed SQL + params); pure logic tested directly. No live DB in tests.
- Dates in DB are DATE/DATETIME2; in Python use datetime.date/datetime; parse with
  common helpers in the module that owns the boundary.
- Docket 'FK to Matter': document.docket_id, weekly_report_event.docket_id and
  watchlist.docket_id reference con.matter. Loaders must upsert the matter first.
