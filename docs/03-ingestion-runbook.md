# 03 — Ingestion runbook

How data gets into the database, how to operate and monitor the pipelines, and
what to do when something sticks. Verified against `ingest/load_tags.py`,
`ingest/index_diff.py`, `ingest/weekly_report_parser.py`,
`ingest/load_document_text.py`, `functions/processing.py` /
`function_app.py`, and `schema/migrate.py`. What to *capture* in each input is
specified in [05-metadata-extraction-spec.md](05-metadata-extraction-spec.md);
this page is how to *load* it.

Four inputs, four paths:

| Input | Format | How it is ingested | Lands in |
|---|---|---|---|
| Metadata tag export | CSV or JSON | **Manual CLI** (`ingest.load_tags`) — the `tag-exports` container is just a drop zone; no trigger watches it | `con.matter`, `con.document` + child tables |
| Repository index snapshot | `.jsonl.gz` (gzipped JSON Lines) | Blob trigger on `index-snapshots` (or manual CLI `ingest.index_diff`) | `con.index_snapshot`, `con.change_log`, re-validation flags on `con.document` |
| DCH weekly CON Tracking Report | PDF | Blob trigger on `weekly-reports` (or manual CLI `ingest.weekly_report_parser`) | `con.weekly_report_event`, stub rows in `con.matter` |
| Document-text export (Document Intelligence output) | JSONL | **Manual CLI** (`ingest.load_document_text`) — the `document-text` container is a drop zone for extraction output; no trigger watches it | `con.document_text`, `con.opinion_paragraph` |

> **Awaiting real samples.** The tag-export column names and the weekly-report
> layout were built to the DESIGN.md spec and a synthetic fixture
> (`tests/fixtures/sample_weekly_report.pdf`), and **will be re-verified
> against real DCH samples**. For the weekly report, every layout assumption
> is a regex table at the top of `ingest/weekly_report_parser.py`
> (`ARTIFACT_PATTERNS`, `REPORT_DATE_PATTERNS`, `SECTION_PATTERNS`,
> `ENTRY_START_PATTERNS`, `FIELD_PATTERNS`, `DATE_PATTERNS`, cost regexes) —
> re-tuning is a table edit, not a rewrite. See `LESSONS.md`.

All CLIs need DB config (`SQL_SERVER`/`SQL_DATABASE` + `az login`, or
`SQL_CONNECTION_STRING` — see [02-configuration.md](02-configuration.md#7-connection-auth-options))
and your client IP in the SQL firewall.

---

## 1. Input format details

### 1.1 Tag export (CSV or JSON)

One row per **document**, carrying both the document's fields and its matter's
fields (matter fields repeated on every document row of that matter). Column
names are exactly the field names from DESIGN.md:

- **Required per row**: `entry_id` (int, Laserfiche Entry ID), `docket_id`
  (any recognized form — `CON1234567`, `CON-1234567`, `DET…`, `LNR-…`, legacy
  `GA-…`, county forms like `FULTON-213`; normalized by `common/docket.py`).
  Rows missing either, or with an unnormalizable docket, are rejected (not a
  crash).
- **Matter columns**: `applicant`, `facility`, `matter_type`, `action_type`,
  `county`, `service_area`, `bed_count`, `year_filed`, `final_outcome`,
  `final_decision_date`, `highest_review_level` (1–5), `completeness_flags`.
- **Document columns**: `docview_url` (defaulted from the entry_id when blank),
  `file_name`, `doc_type`, `decision_level` (1–5), `phase`, `page_count`,
  `repo_date_created`, `repo_date_modified`, `doc_date`, `decision_maker`,
  `outcome`, `parties`, `source_path`, `template_name`, `ocr_status`,
  `ocr_confidence`, `validation_status`, `validated_by`, `validated_date`,
  `duplicate_of`.
- **Research-layer columns** (spec: [05-metadata-extraction-spec.md §A](05-metadata-extraction-spec.md);
  ride the same export, blank = "not provided", never overwrites a populated
  value). Matter-level: `contact_officer`, `project_description`,
  `estimated_cost` (plain numbers, `"$1,234,567.89"`, or `"$4.5 million"`),
  `primary_service_area` (county names), `docket_family` (one of
  CON | DET | DET-EQT | DET-ASC | LNR-ASC | LNR-EQT; derived from the docket id
  via `common/docket_family.py` when absent), `letter_of_intent_date`,
  `deemed_complete_date`, `decision_deadline`, `batching_cycle`,
  `competing_docket_ids` (canonicalized). Document-level: `title`,
  `text_source` (ocr | native | tag). Analytical fields (headnotes, treatment,
  topics, synopses, citation edges) are **not** export columns — see §4.1.
- **Multi-value columns** — `service_type`, `phases_present`,
  `docket_variants`, `parties`, `completeness_flags`, `primary_service_area`,
  `competing_docket_ids` — are **`;`-separated in CSV** and **arrays in JSON**.
- Vocab-controlled columns (`matter_type`, `action_type`, `doc_type`, `phase`,
  `outcome`, `final_outcome`, `service_type`, `phases_present`, `county`,
  `validation_status`) must match `common/vocab.py` exactly after
  case/whitespace normalization — **no fuzzy guessing**; mismatches reject the
  row.
- Dates accept ISO 8601 or US `m/d/Y` (datetimes also `m/d/Y H:M[:S] [AM/PM]`).
- CSV is read as `utf-8-sig` (Excel BOM tolerated).

Loading semantics (why re-runs are safe): matter is MERGEd first, then the
document; updates use `COALESCE(source, target)` so a sparser later row never
blanks a richer earlier one — **except** `validation_status` / `validated_by`
/ `validated_date`, which are always taken from the row (status falling back
to `--default-status`). Child tables (variants, service types, phases) are
insert-if-missing, never deleted.

### 1.2 Index snapshot (`.jsonl.gz`)

Gzipped JSON Lines; each line:

```json
{"id": 123456, "name": "some-file", "ext": "pdf", "path": "/CON/2024/...", "pages": 12}
```

- `id` must be an integer (the Laserfiche Entry ID); lines without one, or that
  aren't JSON objects, are counted as malformed, logged, and skipped.
- A record is "modified" when any of `name`, `ext`, `path`, `pages` changed.
- The CLI tolerates plain `.jsonl` for testing, but the **blob trigger only
  processes names ending `.jsonl.gz`** (anything else is ignored, and not
  recorded in the ledger).
- Put a date in the blob name (`index-2026-07-04.jsonl.gz`) — `con.index_snapshot.snapshot_date`
  is parsed from the name by regex (`20YY[-_.]MM[-_.]DD`).
- Scale note: the diff holds only the OLD snapshot in memory and streams the
  NEW one (~1M-row indexes fit a Consumption-plan Function; see `LESSONS.md`).

### 1.3 Weekly CON Tracking Report (PDF)

Text-based PDF organized in lifecycle sections. The parser recognizes these
section headers (case-insensitive, tolerant of numbering prefixes/trailing
colons) and maps them to `con.weekly_report_event.section` codes:

| Heading seen in the real PDF | Section code |
|---|---|
| Letters of Intent / Letters of Intent – Batching | `LETTER_OF_INTENT` |
| Expired Letters of Intent | `LOI_EXPIRED` |
| New CON Applications | `NEW_APPLICATION` |
| Withdrawn CON Applications | `WITHDRAWN_APPLICATION` |
| Pending Review Applications | `PENDING_APPLICATION` |
| Recently Approved [CON] Applications | `APPROVED` |
| Recently Denied [CON] Applications | `DENIED` |
| Disqualified Applications | `DISQUALIFIED` |
| Appealed CON Projects | `APPEALED` |
| Appealed Determinations | `APPEALED_DETERMINATION` |
| Letters of Determination, generally / Requests for Miscellaneous LODs / Requests for DET-EQT / Requests for DET-ASC … | `LETTER_OF_DETERMINATION` |
| DET Review, generally | `DET_REVIEW` |
| LNR Conversion | `LNR_CONVERSION` |
| Requests for Extended Implementation/Performance Period | `EXTENDED_IMPLEMENTATION` |
| any other docket-bearing section | `OTHER` |

The literal heading text is also stored on each event (`section_heading`).
Sections whose body is the single word "none" produce no events.

Within a section, an entry starts at a line with a docket reference —
including the report's bare year-sequence CON project numbers (`2026-002`,
canonicalized to `CON-2026002`) and subtyped determinations
(`DET-EQT2024-073` → `DET-EQT-2024-073`). Application entries carry labeled
fields (Filed / Deemed Complete / 30th Day Deadline / Decision Deadline /
Site: … (County) / Contact / Estimated Cost, plus an `OPPOSITION FILED`
marker); appealed-determination entries are litigation narratives whose
"received on" date becomes `filing_date` and whose "Agency Decision: … on
<date>" becomes `decision_date`, with the full narrative kept in `raw_text`.
The **report date** comes from the reporting-period range on the cover page
("April 15, 2026 – April 21, 2026" → the end date) — loading
**fails** without it because `report_date` is NOT NULL.

Loading semantics: events dedupe on `dedupe_hash`
(sha256 of `report_date|section|docket_raw|raw_text`) so re-processing the
same PDF inserts nothing new; unknown canonical dockets get **stub matters**
(`completeness_flags = ["stub_from_weekly_report"]`) so events always join to
a matter; existing matter fields are never overwritten.

### 1.4 Document-text export (JSONL)

The output of your Document Intelligence extraction run (the run itself is
operator-driven — `docs/06-research-console-buildout.md` Phase 3; extraction
blobs land in the `document-text` container). One JSON object per line, shape
in [05-metadata-extraction-spec.md §B](05-metadata-extraction-spec.md):

```json
{"entry_id": 9000030, "full_text": "...", "text_source": "ocr",
 "di_model": "prebuilt-layout", "di_confidence": 0.98,
 "paragraphs": [{"num": "1", "text": "In February 2023, ..."}]}
```

- `entry_id` (int), non-empty `full_text`, and `text_source` (ocr | native |
  tag) are required; malformed records (including non-JSON lines) go to the
  rejects report, never a crash.
- **Existence check**: every `entry_id` must already exist in `con.document` —
  unknown ids are rejected with *"entry_id not in con.document (load the tag
  export first)"*. Load the tag export before the text.
- **Wholesale paragraph replace**: a record that carries a `paragraphs` key
  **owns the entire paragraph set** for that entry — existing
  `con.opinion_paragraph` rows are deleted and re-inserted (an empty list
  clears them). A record *without* the key leaves existing paragraphs
  untouched. `full_text`/`char_count` always take the incoming value (a
  re-extraction is authoritative); `text_source`/`di_model`/`di_confidence`
  keep the usual `COALESCE(source, target)` semantics.
- Paragraph `plain_text` is set now; `segs_json` starts as a single plain
  segment and is enriched with cross-links during the editorial pass (§4.1).

---

## 2. Running each CLI manually

Flags below are exactly the argparse definitions in each module.

### 2.1 Tag export → `con.matter` / `con.document`

```bash
python -m ingest.load_tags path/to/export.csv --rejects rejects.csv
python -m ingest.load_tags path/to/export.json --json
```

Full signature:
`python -m ingest.load_tags path [--json] [--batch-size 500] [--default-status {Unvalidated,Validated,Corrected,Rejected}] [--rejects out.csv]`

- `--batch-size` (default 500): rows per commit. Idempotent + resumable — if a
  run dies mid-file, just rerun it; MERGE upserts converge.
- `--default-status` (default `Unvalidated`): applied when a row has no
  `validation_status`.
- `--rejects out.csv`: writes `row_number,field,message,raw_value` for every
  rejected row. **Always pass this** on real loads; the console shows only the
  first 20 rejects.

Prints: rows read / matters upserted / documents upserted / rejected rows /
commits.

### 2.2 Snapshot diff → `con.change_log`

```bash
# inspect only (no DB):
python -m ingest.index_diff old.jsonl.gz new.jsonl.gz --out diff.json

# write to the database:
python -m ingest.index_diff old.jsonl.gz new.jsonl.gz --apply
```

Full signature:
`python -m ingest.index_diff old_snapshot new_snapshot [--apply] [--out diff.json]`

With `--apply`: both snapshots are registered in `con.index_snapshot` (if
absent), one `con.change_log` row per added/modified/deleted record is
inserted, and in-scope **modified** documents get their validation reset (see
§4). One commit at the end — a failed apply leaves nothing partial.

**Caution when mixing manual applies with the blob trigger**: the CLI registers
snapshots under the local **file name** (`old.jsonl.gz` → `blob_name`), and the
Functions app diffs each new blob against the highest `snapshot_id` row. Keep
file names identical to the blob names (or better: let the Functions app do
all applies) so the "latest snapshot" pointer stays coherent.

### 2.3 Weekly report → `con.weekly_report_event`

```bash
# parse and review first:
python -m ingest.weekly_report_parser report.pdf --out events.json

# then load:
python -m ingest.weekly_report_parser report.pdf --apply
```

Full signature:
`python -m ingest.weekly_report_parser pdf [--apply] [--out events.json]`

The summary prints the report date, per-section event counts, events without a
docket, and **warnings** (unrecognized counties, unparseable costs/dates, no
report date). On a first real DCH PDF, always run without `--apply` and read
the warnings — they tell you which regex table needs tuning.

### 2.4 Document-text JSONL → `con.document_text` / `con.opinion_paragraph`

```bash
# validate first — the default is a dry run (no DB):
python -m ingest.load_document_text extracted.jsonl --rejects rejects.csv

# then write:
python -m ingest.load_document_text extracted.jsonl --apply --rejects rejects.csv

# a directory loads every *.jsonl in it (sorted order):
python -m ingest.load_document_text extractions/ --apply
```

Full signature:
`python -m ingest.load_document_text path [--apply] [--batch-size 200] [--rejects out.csv]`

- `path`: a JSONL file, or a directory of `*.jsonl` files.
- Without `--apply` nothing touches the database — records are parsed and
  validated and a summary is printed.
- `--batch-size` (default 200): records per commit; idempotent + resumable
  like `load_tags` (MERGE + wholesale paragraph replacement converge on rerun).
- `--rejects out.csv`: same reject-report format as `load_tags`
  (`row_number,field,message,raw_value`; row numbers are 1-based record
  positions in the input stream). The console output shows only the first 20.

Prints: records read / texts upserted / paragraphs written / commits /
rejected records (dry run: valid records / paragraphs parsed).

### 2.5 Search index refresh (after any bulk load)

```bash
python -m api.search_sync [--recreate] [--skip-vectors] [--batch-size 200]
```

Only relevant when Azure AI Search is deployed. `merge_or_upload` semantics —
safe to re-run any time. See [01-azure-deployment.md](01-azure-deployment.md)
step 10 for credentials.

---

## 3. The blob-triggered flow (Functions app)

Authoritative detail: [`functions/README.md`](../functions/README.md).
Summary of what actually happens:

1. **Upload** a `*.jsonl.gz` to `index-snapshots` or a `*.pdf` to
   `weekly-reports` (containers configurable via `SNAPSHOT_CONTAINER` /
   `REPORT_CONTAINER`). Other extensions are ignored — not even recorded.
2. **Skip check**: if `con.processed_blob` already records
   `container/name` with status `succeeded`, the blob is skipped.
3. **Snapshots** (`snapshot_blob_trigger`):
   - **First snapshot ever** (no rows in `con.index_snapshot`): registered as
     the **baseline** — entry count and max entry id recorded, **no diff run**.
   - Otherwise: the latest prior snapshot (highest `snapshot_id`) is downloaded
     from the same container, both files are diffed
     (`read_snapshot` → `diff_snapshots` → `apply_diff`), `con.change_log`
     rows are written, the new snapshot registered, and in-scope modified
     documents flagged for re-validation.
4. **Reports** (`report_blob_trigger`): download → `extract_text` →
   `parse_report_text` → `load_events` (dedupe-hash skip, stub matters).
5. **Ledger**: every attempt ends in a `con.processed_blob` row keyed
   `container/name`, status `succeeded` (detail = stats summary) or `failed`
   (detail = `ExceptionType: message`). On failure the data transaction is
   rolled back **before** the failure row commits — no partial diffs/events.
6. **Retry semantics**: the exception is re-raised, so the Functions host
   retries the blob up to **5 times**, then writes the receipt to the
   `webjobs-blobtrigger-poison` queue. Because only `succeeded` blocks
   reprocessing, a `failed` blob stays retryable forever — fix the cause and
   either wait for the sweep or re-trigger (§6).
7. **Daily catch-up sweep** (`daily_sweep`, timer `SWEEP_CRON`, default 06:00
   UTC): lists both containers and processes every blob not recorded as
   `succeeded` — heals missed trigger events (Consumption-plan blob triggers
   can miss) and retries failures. One bad blob is logged and skipped; it
   cannot starve the rest.

Results land in: `con.index_snapshot` + `con.change_log` (+ validation resets
on `con.document`) for snapshots; `con.weekly_report_event` (+ stub
`con.matter` rows) for reports; `con.processed_blob` for both.

---

## 4. The re-validation loop

Validation state is **data** (`con.document.validation_status`:
`Unvalidated | Validated | Corrected | Rejected`), and the index diff drives
re-review:

1. A snapshot diff finds a document whose `name`/`ext`/`path`/`pages` changed
   and whose `entry_id` exists in `con.document` ("in scope").
2. `apply_diff` resets that document: `validation_status = 'Unvalidated'`,
   `validated_by = NULL`, `validated_date = NULL`, and marks the change row
   `revalidation_flagged = 1`. The repo metadata columns are **not** updated —
   tag loads own those; the `change_log.details` JSON carries the new values.
3. Researchers re-validate:
   - **The research console** (`web/` — its validation screens work the queue
     of `validation_status = 'Unvalidated'` rows; writes flow console →
     FastAPI → `con.document`, stamping status, `validated_by`,
     `validated_date`. The Power App that used to do this is retired —
     `m365/powerapp/README.md`), or
   - **SQL** directly:
     ```sql
     UPDATE con.document
     SET validation_status = 'Validated',
         validated_by = 'you@yourtenant.com',
         validated_date = SYSUTCDATETIME()
     WHERE entry_id = 123456;
     ```
   - The API surfaces the queue too: `GET /documents?validation_status=Unvalidated`
     and `GET /changes?in_scope=true&change_type=modified`.
4. Deleted in-scope documents are **logged only** — never deleted from
   `con.document`. Watch `GET /changes?change_type=deleted&in_scope=true`.

### 4.1 The editorial pass (research-layer analytical fields)

The analytical fields a machine cannot reliably decide — **headnotes** +
key-number topics, **treatment / good-law level**, **editorial synopses**, and
citation treatments — are not loader inputs: they are entered and verified by
a person **in the console's validation screens**, reusing the same
`Unvalidated → Validated / Corrected / Rejected` workflow as above
(spec: [05-metadata-extraction-spec.md](05-metadata-extraction-spec.md),
"Editorial (E) fields"). When tagging capacity is limited, follow docs/05's
priority order: (1) objective fields for all documents, (2) citation edges,
(3) treatment level + headnotes/topics for decided opinions (levels 2–4),
(4) editorial synopses. If your tagging team produces this data outside the
console, docs/05 §D defines the optional side-file shapes.

---

## 5. Monitoring

**Failed blobs (SQL — the first place to look):**

```sql
SELECT blob_name, processed_at, detail
FROM con.processed_blob
WHERE status = 'failed'
ORDER BY processed_at DESC;
```

**Function failures (App Insights → Logs, workspace `gacon-dev-appi`):**

```kusto
exceptions
| where timestamp > ago(24h)
| order by timestamp desc
| project timestamp, operation_Name, type, outerMessage

traces
| where timestamp > ago(24h)
| where message has_any ("snapshot_blob_trigger", "report_blob_trigger", "daily_sweep", "sweep:")
| order by timestamp desc
```

The sweep logs one line per blob (`sweep: container/name: <detail>`) and a
final counts dict (`processed`/`failed`/`skipped`).

**Ingestion sanity checks (SQL):**

```sql
SELECT TOP 5 * FROM con.index_snapshot ORDER BY snapshot_id DESC;   -- snapshots registered?
SELECT change_type, COUNT(*) FROM con.change_log
  WHERE detected_at > DATEADD(day,-7,SYSUTCDATETIME()) GROUP BY change_type;
SELECT report_date, COUNT(*) FROM con.weekly_report_event
  GROUP BY report_date ORDER BY report_date DESC;
SELECT validation_status, COUNT(*) FROM con.document GROUP BY validation_status;
```

**Tag loads**: keep every `--rejects` CSV; a nonzero reject count is your
signal that the export's columns or vocab values drifted from spec.

---

## 6. Forcing a reprocess

- Fix the underlying cause, then either **wait for the daily sweep** or run it
  now:
  ```bash
  # Azure (needs the function's master key):
  curl -X POST "https://gacon-dev-func.azurewebsites.net/admin/functions/daily_sweep" \
    -H "x-functions-key: $(az functionapp keys list -g gacon-dev-rg -n gacon-dev-func --query masterKey -o tsv)" \
    -H 'Content-Type: application/json' -d '{}'
  ```
- Re-uploading the same blob also re-fires the trigger (a `failed` ledger row
  does not block; only `succeeded` does).
- To force a re-run of a blob that **succeeded** (e.g. after fixing parser
  tables), delete its ledger row first:
  `DELETE FROM con.processed_blob WHERE blob_name = 'weekly-reports/<name>.pdf';`
  — for weekly reports also note events dedupe by hash, so an unchanged PDF
  re-inserts nothing.

---

## 7. Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| `python -m schema.migrate` fails mid-file (regular migration) | SQL error in one batch of an `NNNN_*.sql` file | Nothing to clean up: non-fulltext files run in a **single transaction** — the file rolled back and was not recorded. Fix the SQL (as a new migration if the file was ever applied anywhere) and rerun; already-applied files are skipped via `con.schema_migrations`. |
| Migration fails mid-file in `0005_fulltext.sql` | Full-text files run with **autocommit** (full-text DDL can't run in a transaction), so earlier statements in the file stuck | Check what exists (`SELECT * FROM sys.fulltext_catalogs; SELECT * FROM sys.fulltext_indexes;`). Fix under a **new migration number** containing only the missing statements (never edit an applied file), or drop the partial objects and rerun. See `schema/README.md` "Caveats". |
| Blob uploaded but nothing happens; no `con.processed_blob` row | (a) Wrong extension — trigger ignores anything but `*.jsonl.gz` / `*.pdf` (ignored blobs are not recorded); (b) Consumption-plan trigger missed the event; (c) function code not deployed / app stopped; (d) `AzureWebJobsStorage` misconfigured | (a) Rename/re-gzip and re-upload. (b) Wait for the daily sweep or fire it (§6). (c) `az functionapp function list -g gacon-dev-rg -n gacon-dev-func` should show the three functions. (d) Check app settings against [02-configuration.md](02-configuration.md). |
| Blob row stuck at `failed` | See its `detail` column — `ExceptionType: message` names the cause (bad gzip, malformed PDF, SQL error…) | Fix the file or the environment, re-upload or wait for the sweep. Repeated identical failures = genuinely bad blob; it stabilizes as `failed` and can sit there harmlessly. Weekly report `ValueError: cannot load events: report_date was not found` = the date regexes need tuning for the real layout (top of `weekly_report_parser.py`). |
| `load_tags` rejects many rows | Column names or vocab values differ from DESIGN.md spec (expected until re-verified against a real export); or dockets in an unrecognized form | Read the rejects CSV: `field` + `message` pinpoint it. `not in controlled vocabulary` → compare against `GET /vocab/<name>` (exact strings). `unnormalizable docket` → new docket pattern; extend `common/docket.py`. `missing entry_id` → the export needs the Entry ID column. Fix the export (or the spec tables) and rerun — the loader is idempotent. |
| `/search?q=...` or `?q=` filters return HTTP 500; SQL error mentions `CONTAINS`/`CONTAINSTABLE` or "not full-text indexed" | `FULLTEXT_ENABLED=true` (the default) but `0005_fulltext.sql` was never applied (e.g. migrated with `--skip-fulltext`) | Either run `python -m schema.migrate` without the flag (skipped files apply then), or set `FULLTEXT_ENABLED=false` on the web app for the LIKE fallback. Keep setting and schema in agreement. |
| Function (or API) can't reach SQL: `Login failed for user '<token-identified principal>'` | The managed identity has no database user | Run the `CREATE USER [gacon-dev-func] FROM EXTERNAL PROVIDER` + role grants from [01-azure-deployment.md](01-azure-deployment.md) step 5, as the Entra admin. |
| Function can't reach SQL: network/timeout errors | Firewall: `enablePublicNetworkAccess=false` without private endpoints, or the `AllowAzureServices` rule was removed; or the serverless DB is resuming from auto-pause | Restore public access + rule (or finish the private-endpoint work per `infra/README.md` "Hardening"). Auto-pause resume: first connection after idle takes ~30–60 s — retries (host retry / sweep) heal it. |
| Local CLI can't reach SQL | Your client IP not in the firewall; or `az login` token for the wrong tenant | `az sql server firewall-rule create ...` (step 5.1 of guide 01); `az account show` to confirm tenant/subscription. |
| `pyodbc` errors about the driver (`Can't open lib 'ODBC Driver 18 for SQL Server'`) | ODBC platform driver missing (local machine or a changed Functions base image) | Install msodbcsql18 locally; in Azure, verify per `functions/README.md` "ODBC driver" (log `pyodbc.drivers()` or `odbcinst -q -d` from Kudu/SSH); as a workaround set `SQL_CONNECTION_STRING` naming the driver version present. |
| `search_sync` 403 | Local user lacks Search data-plane roles and no `SEARCH_API_KEY` set | Grant yourself Search Service Contributor + Search Index Data Contributor, or export the admin key (guide 01, step 10). |
| `load_document_text` rejects rows with `entry_id not in con.document (load the tag export first)` | The document rows those texts belong to were never loaded — `con.document_text` FKs to `con.document`, and the loader existence-checks each batch instead of letting the FK insert fail | Run `python -m ingest.load_tags` for the export covering those entry_ids first, then rerun `load_document_text` (idempotent). If the id is genuinely wrong, fix the JSONL. |
| Document Intelligence extraction stalls / errors partway through the corpus | `docIntelSku = 'F0'` caps at **500 pages/month** — the ~24,290-document corpus far exceeds it | Batch the backfill across months at $0, or temporarily redeploy with `docIntelSku = 'S0'` (~$1.50/1,000 pages), run the extraction, then drop back to `F0` (`infra/README.md` step 8; decision table in guide 02). |
| Paragraphs for a document were replaced (or wiped) unexpectedly after a text re-load | Paragraphs are replaced **wholesale** per entry_id: any record carrying a `paragraphs` key owns the entire set (an **empty list clears it**) — a partial paragraph list overwrites the full one | Re-run with a record carrying the **complete** paragraph set for that entry_id; to update only `full_text`/metadata without touching paragraphs, omit the `paragraphs` key entirely. Editorial `segs_json` cross-links added in the console are lost on replace — re-extract before the editorial pass, not after. |
