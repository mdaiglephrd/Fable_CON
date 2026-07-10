# 03 — Ingestion runbook

How data gets into the database, how to operate and monitor the pipelines, and
what to do when something sticks. Verified against `ingest/load_tags.py`,
`ingest/index_diff.py`, `ingest/weekly_report_parser.py`,
`functions/processing.py` / `function_app.py`, and `schema/migrate.py`.

Three inputs, three paths:

| Input | Format | How it is ingested | Lands in |
|---|---|---|---|
| Metadata tag export | CSV or JSON | **Manual CLI** (`ingest.load_tags`) — the `tag-exports` container is just a drop zone; no trigger watches it | `con.matter`, `con.document` + child tables |
| Repository index snapshot | `.jsonl.gz` (gzipped JSON Lines) | Blob trigger on `index-snapshots` (or manual CLI `ingest.index_diff`) | `con.index_snapshot`, `con.change_log`, re-validation flags on `con.document` |
| DCH weekly CON Tracking Report | PDF | Blob trigger on `weekly-reports` (or manual CLI `ingest.weekly_report_parser`) | `con.weekly_report_event`, stub rows in `con.matter` |

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
- **Multi-value columns** — `service_type`, `phases_present`,
  `docket_variants`, `parties`, `completeness_flags` — are **`;`-separated in
  CSV** and **arrays in JSON**.
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

| Header seen in the PDF | Section code |
|---|---|
| Letters of Intent [Received/Filed] | `LETTER_OF_INTENT` |
| New Applications [Received/Filed] / Applications Received | `NEW_APPLICATION` |
| Withdrawn [Applications/Projects] | `WITHDRAWN_APPLICATION` |
| Pending Applications [Under Review] | `PENDING_APPLICATION` |
| [Recently] Approved [Applications/Projects] | `APPROVED` |
| [Recently] Denied [Applications/Projects] | `DENIED` |
| Appealed [Projects/Applications] | `APPEALED` |
| Letters of Determination [Issued] | `LETTER_OF_DETERMINATION` |

Within a section, an entry starts at a line with a docket reference or a
"Project No."-style label; labeled fields recognized: Applicant, Project
[Description], County, Site, [Estimated/Total] [Project] Cost, Opposition,
Date Filed/Filing Date/Filed, Decision Due/Deadline/Review Period Ends,
Decision Date/Approved/Denied/Withdrawn. The **report date** must be findable
near the top ("Week of …", "Report Date: …", or a bare date line) — loading
**fails** without it because `report_date` is NOT NULL.

Loading semantics: events dedupe on `dedupe_hash`
(sha256 of `report_date|section|docket_raw|raw_text`) so re-processing the
same PDF inserts nothing new; unknown canonical dockets get **stub matters**
(`completeness_flags = ["stub_from_weekly_report"]`) so events always join to
a matter; existing matter fields are never overwritten.

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

### 2.4 Search index refresh (after any bulk load)

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
   - **Power App** (`m365/powerapp/` — ValidationScreen is a work queue of
     `validation_status = 'Unvalidated'` rows; buttons `Patch()` the row with
     status, `validated_by`, `validated_date`), or
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
