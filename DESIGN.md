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
  section      NVARCHAR(40) NOT NULL CHECK IN (the 15 codes of vocab.REPORT_SECTIONS:
                LETTER_OF_INTENT, LOI_EXPIRED, NEW_APPLICATION, WITHDRAWN_APPLICATION,
                PENDING_APPLICATION, APPROVED, DENIED, DISQUALIFIED, APPEALED,
                APPEALED_DETERMINATION, LETTER_OF_DETERMINATION, DET_REVIEW,
                LNR_CONVERSION, EXTENDED_IMPLEMENTATION, OTHER),
  section_heading NVARCHAR(200) NULL,      -- the report's literal heading text
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
- `DET...` -> `DET-` + the rest, internal separators normalized to hyphens. Subtyped
  determinations keep the subtype: `DET-EQT2024-073` -> `DET-EQT-2024-073`,
  `DET-ASC...` likewise (kind stays 'DET').
- Weekly-report CON project numbers print WITHOUT the prefix as year-seq (`2026-002`);
  the repository form is `CON{YYYY}{SEQ3}` (`CON2026002`). The report parser (only —
  too ambiguous for generic extraction) maps `2026-002` -> canonical `CON-2026002`
  with `2026-002` kept as a variant.
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
AZURE_OPENAI_API_VERSION # optional; api/search_client.py supplies the default
KEY_VAULT_URI           # informational only — code never reads Key Vault directly.
                        # Secrets reach the apps as env vars via App Settings
                        # @Microsoft.KeyVault(SecretUri=...) references.
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

---

# RESEARCH LAYER (v2) — authoritative contract for the CON Research Console

The console (design handoff in `web/design-reference/`) needs legal *content* on top of the v1
inventory. This layer is additive: v1 tables/modules/tests are unchanged. Build against the names
below. Reference data shapes: `tests/fixtures/handoff/con-corpus.js` (cases) and
`docket-engine.js` (stage engine) — these are the UI's authoritative data contract.

## Schema — research layer (schema `con`; migrations 0006+)

### New controlled-vocabulary tables (seeded in 0007; codes are the exact strings)
- `con.vocab_treatment(code NVARCHAR(40) PK)`: Followed; Distinguished; Criticized; Reversed; Overruled; Cited; Neutral
- `con.vocab_docket_family(code NVARCHAR(20) PK)`: CON; DET; DET-EQT; DET-ASC; LNR-ASC; LNR-EQT
- `con.vocab_event_type(code NVARCHAR(20) PK)`: Filing; Order; Opinion; Hearing; Brief; Notice
- `con.vocab_counsel_side(code NVARCHAR(20) PK)`: Applicant; Petitioner; Respondent; Appellant; Appellee; Intervenor; Amicus; Agency
- `con.vocab_treatment_level(code NVARCHAR(20) PK)`: positive; caution; negative; neutral  (good-law banner level)

### Extend existing tables (0006, ALTER … ADD; all new cols NULLable)
- `con.matter` + : `contact_officer NVARCHAR(200)`, `project_description NVARCHAR(MAX)`,
  `estimated_cost DECIMAL(18,2)`, `primary_service_area NVARCHAR(MAX) CHECK ISJSON` (JSON array of counties),
  `docket_family NVARCHAR(20) FK->vocab_docket_family`, `letter_of_intent_date DATE`,
  `deemed_complete_date DATE`, `decision_deadline DATE`, `batching_cycle NVARCHAR(60)`,
  `competing_docket_ids NVARCHAR(MAX) CHECK ISJSON`, `precedent_signal NVARCHAR(20)` (valid|questioned|overturned|noprecedent).
- `con.document` + : `title NVARCHAR(500)`, `text_source NVARCHAR(10)` (ocr|native|tag).

### New content tables (0006)
```
con.document_text(entry_id INT PK FK->document, full_text NVARCHAR(MAX), text_source NVARCHAR(10),
  char_count INT, di_model NVARCHAR(60), di_confidence DECIMAL(5,2), extracted_at DATETIME2 DEFAULT SYSUTCDATETIME())
con.opinion(entry_id INT PK FK->document, caption_json NVARCHAR(MAX) CHECK ISJSON, tribunal_line NVARCHAR(400),
  byline NVARCHAR(200), intro_text NVARCHAR(MAX), disposition_json NVARCHAR(MAX) CHECK ISJSON,
  editorial_synopsis NVARCHAR(MAX), decided_date DATE, argued_date DATE, court_docket_no NVARCHAR(60),
  subsequent_history NVARCHAR(MAX), is_published BIT, standard_of_review NVARCHAR(200),
  treatment_level NVARCHAR(20) FK->vocab_treatment_level, treatment_note_json NVARCHAR(MAX) CHECK ISJSON)
con.opinion_paragraph(paragraph_id BIGINT IDENTITY PK, entry_id INT FK->document, para_num NVARCHAR(10),
  segs_json NVARCHAR(MAX) CHECK ISJSON, plain_text NVARCHAR(MAX), sort_order INT)   -- segs_json = the tagged-tuple rich-text array
con.reporter_citation(cite_id BIGINT IDENTITY PK, entry_id INT FK->document, citation NVARCHAR(120),
  reporter NVARCHAR(40), volume NVARCHAR(20), page NVARCHAR(20), is_parallel BIT DEFAULT 0)
con.headnote(headnote_id BIGINT IDENTITY PK, entry_id INT FK->document, num NVARCHAR(10),
  topic_id NVARCHAR(40) FK->con.topic, topic_label NVARCHAR(200), text NVARCHAR(MAX))
```

### Taxonomy / citator (0006; topic tree seeded 0008)
```
con.topic(topic_id NVARCHAR(40) PK, parent_topic_id NVARCHAR(40) NULL FK->con.topic,
  key_number NVARCHAR(40), title NVARCHAR(200), description NVARCHAR(MAX))   -- e.g. 'vi-24','CON VI · 24','Substantial Evidence'
con.document_topic(entry_id INT FK->document, topic_id NVARCHAR(40) FK->con.topic, PK(entry_id,topic_id))
con.citation(citation_id BIGINT IDENTITY PK, citing_entry_id INT FK->document,
  cited_entry_id INT NULL FK->document, cited_statute_id NVARCHAR(40) NULL FK->con.statute,
  cited_external NVARCHAR(300) NULL, treatment NVARCHAR(40) NULL FK->vocab_treatment, depth TINYINT NULL,
  pinpoint NVARCHAR(60), snippet NVARCHAR(MAX), topic_id NVARCHAR(40) NULL FK->con.topic)
  -- how-cited = WHERE cited_*; table-of-authorities = WHERE citing_entry_id
```

### People / filings / timeline (0006)
```
con.counsel(counsel_id BIGINT IDENTITY PK, entry_id INT NULL FK->document, docket_id NVARCHAR(50) NULL FK->matter,
  role NVARCHAR(120), attorney_name NVARCHAR(200), firm NVARCHAR(200), party_side NVARCHAR(20) FK->vocab_counsel_side)
con.brief(brief_id BIGINT IDENTITY PK, docket_id NVARCHAR(50) FK->matter, entry_id INT NULL FK->document,
  title NVARCHAR(400), party_side NVARCHAR(20) NULL FK->vocab_counsel_side, attorney_name NVARCHAR(200),
  firm NVARCHAR(200), filed_date DATE, page_count INT)
con.proceeding_stage(stage_id BIGINT IDENTITY PK, docket_id NVARCHAR(50) FK->matter, stage_num NVARCHAR(10),
  stage_label NVARCHAR(80), court NVARCHAR(200), title NVARCHAR(300), cite NVARCHAR(200), stage_date DATE,
  outcome NVARCHAR(60) NULL FK->vocab_outcome, summary NVARCHAR(MAX), filings_count INT, decision_maker NVARCHAR(200),
  duration_days INT, is_current BIT DEFAULT 0, has_opinion BIT DEFAULT 0, opinion_entry_id INT NULL FK->document,
  sort_order INT)
con.docket_event(event_id BIGINT IDENTITY PK, docket_id NVARCHAR(50) FK->matter, event_date DATE,
  event_type NVARCHAR(20) FK->vocab_event_type, court NVARCHAR(200), description NVARCHAR(MAX),
  actor NVARCHAR(200), entry_id INT NULL FK->document)
```

### Statutes (0006; content seeded/loaded separately)
```
con.statute(statute_id NVARCHAR(40) PK, kind NVARCHAR(10) CHECK IN ('OCGA','RULE'), citation_label NVARCHAR(200),
  title NVARCHAR(400), full_text NVARCHAR(MAX), effective_date DATE, regime_note NVARCHAR(MAX),
  subsections_json NVARCHAR(MAX) CHECK ISJSON)
con.statute_xref(from_statute_id NVARCHAR(40) FK->con.statute, to_statute_id NVARCHAR(40) FK->con.statute,
  PK(from_statute_id,to_statute_id))
```

### Workspace (0006)
```
con.wiki_article(article_id NVARCHAR(60) PK, group_name NVARCHAR(120), title NVARCHAR(300),
  toc_json NVARCHAR(MAX) CHECK ISJSON, body_json NVARCHAR(MAX) CHECK ISJSON, status NVARCHAR(20), updated_at DATETIME2)
con.wiki_revision(revision_id BIGINT IDENTITY PK, article_id NVARCHAR(60) FK->con.wiki_article, author NVARCHAR(200),
  submitted_at DATETIME2 DEFAULT SYSUTCDATETIME(), status NVARCHAR(20) CHECK IN ('pending','approved','rejected'),
  diff_json NVARCHAR(MAX) CHECK ISJSON)
con.research_project(project_id NVARCHAR(60) PK, owner_upn NVARCHAR(200), name NVARCHAR(300), description NVARCHAR(MAX),
  tags_json NVARCHAR(MAX) CHECK ISJSON, status NVARCHAR(20) DEFAULT 'open', created_at DATETIME2 DEFAULT SYSUTCDATETIME())
con.project_item(item_id BIGINT IDENTITY PK, project_id NVARCHAR(60) FK->con.research_project,
  entry_id INT NULL FK->document, docket_id NVARCHAR(50) NULL FK->matter, flagged BIT DEFAULT 0, note NVARCHAR(MAX))
con.saved_alert(alert_id NVARCHAR(60) PK, owner_upn NVARCHAR(200), name NVARCHAR(300), query_json NVARCHAR(MAX) CHECK ISJSON,
  scope NVARCHAR(20), frequency NVARCHAR(20), active BIT DEFAULT 1, created_at DATETIME2 DEFAULT SYSUTCDATETIME())
con.deadline_rule(rule_id NVARCHAR(60) PK, docket_family NVARCHAR(20) FK->vocab_docket_family, trigger_event NVARCHAR(120),
  offset_days INT, basis_statute NVARCHAR(40) NULL FK->con.statute, description NVARCHAR(MAX))
```

### Indexes (0006): citation(citing_entry_id),(cited_entry_id),(cited_statute_id); document_topic(topic_id);
opinion(decided_date); proceeding_stage(docket_id); docket_event(docket_id),(event_date);
counsel(entry_id),(docket_id); brief(docket_id); reporter_citation(entry_id); headnote(entry_id).

### Topic taxonomy seed (0008) — CON key-number tree used by the corpus
Roots CON I–VII; sub-numbers referenced by the handoff headnotes/citator: `iii-7` (CON III · 7,
Need / Service-Area Methodology), `iv-11` (Psychiatric/Behavioral — Need), `iv-12` (Hospital Beds — Need),
`iv-13` (Ambulatory Surgery — Need), `iv-15` (Cardiac Cath / OHS — Need), `v-21` (Burden of Proof),
`vi-24` (Substantial Evidence — Standard of Review), `vi-25` (Final Agency Action — Remand). Parents:
`iii` Need/Utilization, `iv` Service-Type Need, `v` Procedure/Burden, `vi` Judicial Review. Give every
leaf a parent; extend freely — this seed must at least cover the ids above.

## common/ — new modules

### common/docket_family.py
`classify_family(docket_id_or_variant: str) -> str` -> one of vocab_docket_family. Rules: LNR-ASC/LNR-EQT
by prefix; DET-EQT/DET-ASC by subtype (see docket.py DocketMatch); plain DET -> 'DET'; everything CON-* /
county / GA-legacy -> 'CON'. Pure.

### common/deadline_rules.py
`DEADLINE_RULES: list[DeadlineRule]` (the same rows seeded into con.deadline_rule) and
`compute_deadlines(family: str, trigger_event: str, base: date) -> list[ComputedDeadline]`
(`ComputedDeadline(label, due_date, basis_statute, description)`). Pure; the API `/deadlines/calculate`
and the seed both come from here (single source of truth). Offsets from the handoff docket-engine copy
(e.g., challenge window 30 days; HO appointment 30 days; hearing window 60–120 days; judicial petition
30 days; 120-day default finality).

### common/proceeding.py  — Python port of docket-engine.js (kept in PARITY with the JS)
```
REFERENCE_NOW = date(2026, 6, 25)   # matches docket-engine.js `NOW`
def build_proceeding(rec: dict, now: date = REFERENCE_NOW) -> dict
   # rec = {type, num, facility, title, received, date, finding, county, contact}
   # returns EXACTLY the JS build() shape: {badge, subtypeLabel?, subtypeSub?, isClosed, isActive,
   #   filedLine, closedLine, durationLine, finalDisposition, precedent, compact[], stages[]}
def stages_to_rows(docket_id, proceeding) -> list[dict]   # -> con.proceeding_stage column dicts
```
Parity is verified against golden JSON generated from the real JS (see tests). Port buildCON (stages
0–7) and buildDET (stages 1–5, subtype copy) faithfully; keep the STATUS/SUBTYPE_COPY tables.
NOTE the JS `precedentForCON` uses a string-seeded pseudo-random — replicate the exact `seedOf` hash and
thresholds so precedent output matches.

## api/ — new routers (mounted in api/main.py; same get_db dependency, parameterized SQL, whitelists)
Response shapes mirror the handoff JS (camelCase keys in JSON responses to match the SPA).
- `api/routers/cases.py`  GET /cases/{id} -> reader payload (opinion + paragraphs + headnotes +
  reporterCitations + counsel + treatment + briefs + meta + citator summary)
- `api/routers/proceeding.py`  GET /dockets/{docket_id}/proceeding -> build_proceeding output for the
  matter (from stored con.proceeding_stage if present, else synthesized via common.proceeding from the matter row)
- `api/routers/citator.py`  GET /citator/{id} -> {flags[], citingCases[], tableOfAuthorities[]}
- `api/routers/topics.py`  GET /topics (tree) ; GET /topics/{topic_id} -> docs under a key number
- `api/routers/statutes.py`  GET /statutes ; GET /statutes/{id} (+ citingCases)
- `api/routers/history.py`  GET /history/{docket_id}?type= -> docket_event timeline
- `api/routers/stats.py`  GET /stats?range= -> aggregates (grant/denial KPIs; byService/byYear/
  byFamily counts; appeal reversal rate)
- `api/routers/deadlines.py`  POST /deadlines/calculate {family,trigger_event,date} -> compute_deadlines
- `api/routers/projects.py`  GET/POST /projects ; GET/POST /projects/{id}/items
- `api/routers/alerts.py`  GET/POST /alerts ; DELETE /alerts/{id} (soft, active=0)
- `api/routers/wiki.py`  GET /wiki ; GET /wiki/{id} ; POST /wiki/{id}/revisions ; POST /wiki/{id}/revisions/{rid}/review {action}
- /ask stays but is optional (Copilot preferred). All new routers testable with tests/fakes.FakeConnection.

## ingest/ — additions
- `ingest/load_tags.py` gains the new matter/document columns (B1/B0). Keep it idempotent + rejects.
  New multi-value/JSON columns: primary_service_area, competing_docket_ids (`;`/list). docket_family
  defaults via common.docket_family.classify_family when the column is absent.
- `ingest/load_document_text.py` — CLI `python -m ingest.load_document_text <jsonl-file-or-dir>
  [--apply] [--batch-size 200] [--rejects out.csv]` (dry-run by default).
  Reads an OCR/text export (JSONL: `{entry_id, full_text, text_source, di_model, di_confidence, paragraphs:[{num,text}]}`)
  and upserts con.document_text + con.opinion_paragraph (plain_text set; segs_json defaults to a single
  plain segment when cross-links not yet editorially added). Idempotent. (Actual Document-Intelligence
  invocation is documented in docs/06; the loader consumes its JSONL output — no live Azure call in code/tests.)

## web/ — React console (built after backend)
React + Vite + TypeScript SPA in `web/`. `web/design-reference/` holds the handoff (do not ship it).
`web/src/lib/docketEngine.ts` = TS copy kept in parity with common/proceeding.py. Static Web Apps Free
hosting; Entra auth via staticwebapp.config.json. One route per handoff view.

## Conventions (research layer)
- API JSON is camelCase (SPA contract); DB columns stay snake_case; routers map at the boundary.
- New vocab/seed values must match this file exactly (Python constants in common/vocab.py mirror the
  seed SQL, same as v1).
- Parity: common/proceeding.py and web/src/lib/docketEngine.ts must both match golden fixtures generated
  from tests/fixtures/handoff/docket-engine.js via node.

---

# TAG ETL LAYER (Phase 1) — Georgia CON Tagging Taxonomy

Bulk-loads the ~150K-document SSD corpus (the same Laserfiche `HealthPlanning` repository v1/v2
already model, confirmed via the operator-supplied document index — see docs/07) into the *existing*
`con.matter`/`con.document`/`con.document_text` tables, and stands up the schema Harvey's Phase 2
Axis 1-4 tagging (docs/08) writes into. Phase 1 loads document records only; it never applies tags.

## Schema — Axis 1-4 (migrations 0010-0012; additive on the existing `con` schema, no new database)

### Vocab/lookup tables (0010; seeded verbatim from GeorgiaCONTaggingTaxonomy_2.docx)
- `con.vocab_axis1_proceeding_type(code NVARCHAR(20) PK, description NVARCHAR(400) NULL)` — 5 values:
  CON, DET, DET-ASC, DET-EQT, Other.
- `con.vocab_axis2_authority_type(code NVARCHAR(60) PK, description NVARCHAR(400) NULL)` — 12 values
  incl. Masterfile.
- `con.axis3_substantive_issue(code NVARCHAR(10) PK, parent_code NVARCHAR(10) NULL FK->self,
  label NVARCHAR(600), citation NVARCHAR(1000) NULL, sort_order INT)` — 125 rows (100-900 series).
- `con.axis4_procedural_issue` — same shape, P-prefixed codes, 59 rows (P100-P900 series).
- Mirrored in `common/axis_taxonomy.py` (same "constants mirror the seed data" convention as
  common/vocab.py): `AXIS1_PROCEEDING_TYPE`, `AXIS2_AUTHORITY_TYPE` (dicts, code -> description),
  `AXIS3_SUBSTANTIVE_ISSUE`, `AXIS4_PROCEDURAL_ISSUE` (tuples of `AxisCode`), `AXIS3_BY_CODE`/
  `AXIS4_BY_CODE` (dicts), `MASTERFILE = "Masterfile"`.

### Tag-assignment tables (0011; empty after Phase 1 -- Phase 2/Harvey populates these)
```
con.document_axis1(entry_id FK->con.document, value FK->vocab_axis1_proceeding_type, PK(entry_id))
con.document_axis2(entry_id FK->con.document, value FK->vocab_axis2_authority_type, PK(entry_id))
con.document_axis3(entry_id FK->con.document, code  FK->axis3_substantive_issue, PK(entry_id, code))
con.document_axis4(entry_id FK->con.document, code  FK->axis4_procedural_issue, PK(entry_id, code))
```
Masterfile rule (a document tagged Masterfile on Axis 2 carries no Axis 3/4 tags) is enforced by
triggers in both directions (`trg_axis2_masterfile_guard`, `trg_axis3_masterfile_guard`,
`trg_axis4_masterfile_guard`) AND mirrored in pure Python (`common/axis_validation.py::validate_tags`)
so `ingest/load_axis_tags.py` rejects violations before ever reaching the triggers.

### Idempotency ledger (0012)
`con.tag_source_file(path_hash CHAR(64), file_hash CHAR(64), file_path NVARCHAR(1000),
entry_id INT NULL FK->con.document, status NVARCHAR(20) CHECK IN ('Succeeded','Failed','Unresolved'),
detail NVARCHAR(MAX), processed_at, PK(path_hash, file_hash))`. `path_hash`/`file_hash` are sha256 of
the real file path string / file bytes (`common/file_identity.py` hash_path/hash_file) -- the file's
stable identity is (path, content), but a real path is too long to use directly in a PK without risking
SQL Server's 900-byte index key limit, hence hashing both dimensions to fixed-size columns. Mirrors
con.processed_blob's "only Succeeded blocks reprocessing" rule.

## common/ — new modules
- `common/axis_taxonomy.py`, `common/axis_validation.py` — as above.
- `common/file_identity.py` — `hash_file(path) -> str`, `hash_path(path: str) -> str` (both sha256).
- `common/json_logging.py` — `configure_json_logging(name) -> Logger`, structured JSON log records.
  Used only by `ingest/tag_*` modules -- a deliberate, scoped divergence from the rest of the repo's
  plain stdlib `logging` convention, per this pipeline's own quality bar.
- `common/docket.py` — `_LNR_RE` now recognizes the `ASC`/`EQT` subtype the same way `_DET_RE` already
  did (`LNR-ASC2005006` -> canonical `LNR-ASC-2005006`), fixing a real gap surfaced by the actual SSD
  index (pre-2019 LNR-ASC/LNR-EQT filings are ~4.3% of the real corpus). `common/docket_family.py`
  needed no logic change (it already worked around the gap via a raw-string prefix check) but its
  stale comment describing the gap was corrected.

## ingest/ — new modules (flat, `tag_`-prefixed, matching the existing one-file-per-concern convention)
- `ingest/tag_enumerate.py` — `enumerate_candidate_files(root) -> Iterator[CandidateFile]`. Pure
  filesystem walk; no DB, no OCR.
- `ingest/tag_crosswalk.py` — `load_index(xlsx_path) -> CrosswalkIndex` (operator-supplied
  Path/Name/Type/Entry ID/Page Count index); `resolve_entry_id(file_path, index, docket=None,
  actual_page_count=None) -> MatchResult` (fuzzy match via difflib + docket-scoped narrowing +
  page-count cross-check; unresolved when below `MATCH_THRESHOLD` or ambiguous within
  `AMBIGUITY_MARGIN`); `infer_doc_type_phase(path_parts) -> (doc_type, phase)` (folder-position table
  grounded in real observed folder names, e.g. "A Main Application" -> Application/Request).
- `ingest/tag_ocr.py` — `OcrEngine` protocol, `OcrResult`; `NativeTextEngine` (pdfplumber text-layer
  fast path); `OpenOcrEngine` (wraps `openocr-python`, lazy-imported).
- `ingest/tag_process.py` — `process_one_file(candidate, engine, index) -> ProcessedDocument`. Pure
  given an engine + index; never raises (OCR failure and crosswalk-unresolved are both captured in the
  returned object, not exceptions).
- `ingest/tag_load.py` — `load_one_record(conn, doc) -> LoadResult`. Calls `ingest.load_tags.
  shape_row`/`_write_shaped` and `ingest.load_document_text.shape_record`/`_write_shaped` directly
  (the private `_write_shaped` helpers, not the public `load_rows`/`load_texts`, because those commit
  on their own batch-size -- this module's caller owns commit cadence). Also owns the
  `con.tag_source_file` ledger (`already_succeeded`/`record_processed`).
- `ingest/tag_orchestrate.py` — CLI `python -m ingest.tag_orchestrate root --index-xlsx PATH [--apply]
  [--batch-size 500] [--rejects out.csv]`. Thin wrapper composing the three stages above; batching is
  implicit via `os.walk`'s natural directory-tree traversal order (no separate re-grouping pass, so the
  whole corpus never needs buffering before work starts).
- `ingest/load_axis_tags.py` — Phase 2's consumer loader. CLI `python -m ingest.load_axis_tags path
  [--json] [--apply] [--batch-size 500] [--rejects out.csv]`. One row per `entry_id` + axis1/axis2/
  axis3/axis4; `shape_tag_row` validates via `common.axis_validation.validate_tags` before any write;
  a blank axis in a row leaves that axis's existing value(s) untouched (incremental tagging).

## docs/ — new guides
- `docs/07-tag-etl-runbook.md` — Phase 1 operational runbook (mirrors docs/03's structure).
- `docs/08-harvey-tagging-guide.md` — Phase 2 guide for a human operator (Harvey Vaults per document
  type, Review Table column mapping, the Masterfile-vs-"1 Master File"-folder pitfall, export + load
  via `ingest/load_axis_tags.py`, verification queries).

## Conventions (tag ETL layer)
- No new database, no new schema name: Axis 1-4 tables live in the existing `con` schema, reusing
  `common/db.py`'s existing `get_connection()` -- confirmed against real data (the SSD index's Entry ID
  range and folder convention match this repo's own Laserfiche-sourced schema), not assumed.
- File paths (`root`, `--index-xlsx`) are CLI arguments, never environment variables -- matching every
  other loader in this repo (`ingest/load_tags.py`'s `path`, `ingest/index_diff.py`'s snapshot args).
- Every `ingest/tag_*` module logs via `common/json_logging.py` (structured JSON), not plain `logging`.
