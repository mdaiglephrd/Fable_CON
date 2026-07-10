# functions/ — Azure Functions app (blob ingestion + catch-up sweep)

Azure Functions Python app (v2 programming model, single `function_app.py`)
that keeps the CON database in sync with two Storage containers:

| Container (env var) | Default name | Content | Handler |
| --- | --- | --- | --- |
| `SNAPSHOT_CONTAINER` | `index-snapshots` | Laserfiche index snapshots, `*.jsonl.gz` | `snapshot_blob_trigger` |
| `REPORT_CONTAINER` | `weekly-reports` | DCH weekly report PDFs, `*.pdf` | `report_blob_trigger` |

All logic lives in `processing.py` (plain module, no `azure.functions`
import) so it is unit-testable without the Functions runtime
(`tests/test_functions_logic.py`). `function_app.py` is a thin decorated
wrapper. Blobs with other extensions are ignored (not recorded).

## How the triggers work

### `snapshot_blob_trigger` (blob trigger, `%SNAPSHOT_CONTAINER%/{name}`)

1. Skip if `con.processed_blob` already records `container/name` as
   `succeeded`.
2. Find the latest prior snapshot (`con.index_snapshot` by highest
   `snapshot_id`).
   - **No prior snapshot (first ever): baseline behavior.** The blob is read
     once to count entries and find the max entry id, registered in
     `con.index_snapshot`, and recorded as processed. No diff is run.
   - **Prior snapshot exists:** both blobs are downloaded from the container
     to temp files, then `ingest.index_diff.read_snapshot` +
     `diff_snapshots` + `apply_diff` write `con.change_log`, register the new
     snapshot, and flag in-scope modified documents for re-validation.
3. Record `con.processed_blob` (`succeeded`, detail = stats summary).

### `report_blob_trigger` (blob trigger, `%REPORT_CONTAINER%/{name}`)

Skip if already succeeded; download the PDF to a temp file; then
`ingest.weekly_report_parser.extract_text` -> `parse_report_text` ->
`load_events` (inserts `con.weekly_report_event` rows, creates stub matters);
record `con.processed_blob`.

### `daily_sweep` (timer trigger, `%SWEEP_CRON%`, default `0 0 6 * * *`)

Lists both containers via `BlobServiceClient` and runs the exact same
processing functions for every blob whose `container/name` key is not
recorded as `succeeded` in `con.processed_blob`. This catches blobs whose
trigger event was missed (Functions blob triggers can miss events on
consumption plans) and retries previously failed blobs. A failing blob is
logged and skipped so it cannot starve the rest of the sweep.

The six-field NCRONTAB default `0 0 6 * * *` = daily at 06:00 UTC.

## Failure and poison-blob behavior

Every blob processing attempt ends in a `con.processed_blob` row keyed
`container/name` with status `succeeded` or `failed` (detail = stats summary
or `ExceptionType: message`). On failure the DB transaction is rolled back
first, so no partial diff/event data is committed; then the failure row is
committed and the exception is **re-raised**. The Functions host retries a
failed blob trigger up to 5 times and then writes the blob receipt to the
`webjobs-blobtrigger-poison` queue. Because a `failed` row does not block
reprocessing (only `succeeded` does), host retries and the daily sweep will
keep retrying transient failures; genuinely bad blobs stabilize as `failed`
and can be inspected via their `detail` text.

## Configuration (app settings / `local.settings.json`)

| Setting | Meaning |
| --- | --- |
| `AzureWebJobsStorage` | Functions host storage; also the connection the blob triggers listen on. |
| `FUNCTIONS_WORKER_RUNTIME` | Must be `python`. |
| `SQL_SERVER` / `SQL_DATABASE` | Azure SQL target; `common.db.get_connection` uses ODBC Driver 18 with `ActiveDirectoryDefault` (managed identity in Azure). |
| `SQL_CONNECTION_STRING` | Optional full ODBC string; wins over the pair above (local dev / SQL auth). |
| `SNAPSHOT_CONTAINER` | Snapshot container name (default `index-snapshots`). |
| `REPORT_CONTAINER` | Weekly report container name (default `weekly-reports`). |
| `SWEEP_CRON` | NCRONTAB schedule for `daily_sweep` (default `0 0 6 * * *`). |
| `STORAGE_CONNECTION` | Storage connection string used for downloads/listing; falls back to `AzureWebJobsStorage`. |
| `STORAGE_ACCOUNT_URL` | Optional. When neither connection string is set, `https://<account>.blob.core.windows.net` + `DefaultAzureCredential` (managed identity) is used instead. |

Copy `local.settings.json.example` to `local.settings.json` for local runs
(never commit it; it is gitignored).

## Run locally (Azurite + Core Tools)

```bash
# 1. Storage emulator
npm install -g azurite && azurite --silent &

# 2. Containers
az storage container create -n index-snapshots --connection-string "UseDevelopmentStorage=true"
az storage container create -n weekly-reports  --connection-string "UseDevelopmentStorage=true"

# 3. App settings + shared code next to the app
cd functions
cp local.settings.json.example local.settings.json   # point SQL_* at a dev DB
ln -s ../common common && ln -s ../ingest ingest     # or copy; deploy.sh stages these for Azure

# 4. Start the host (needs Azure Functions Core Tools v4 and Python 3.11)
func start
```

Upload a `.jsonl.gz` into `index-snapshots` or a `.pdf` into
`weekly-reports` to fire the triggers. To fire the sweep on demand:
`curl -X POST http://localhost:7071/admin/functions/daily_sweep -H 'Content-Type: application/json' -d '{}'`.

Unit tests (no runtime, no DB, no storage):

```bash
python3 -m pytest tests/test_functions_logic.py -q
```

## Deploy

```bash
./functions/deploy.sh <function-app-name>     # or FUNCTION_APP_NAME=... ./functions/deploy.sh
```

The script stages `function_app.py`, `processing.py`, `host.json`,
`requirements.txt` plus the repo-root `common/` and `ingest/` packages into
`functions/.build/` and runs `func azure functionapp publish <name> --python`
from there (remote Oryx build installs `requirements.txt`). A commented
fallback in the script does the same with `zip` +
`az functionapp deployment source config-zip` when Core Tools is not
available.

## ODBC driver (msodbcsql18) in the Functions Python image

`pyodbc` needs the platform ODBC stack (`unixODBC` + `msodbcsql18`, per
`common/db.py`'s `Driver={ODBC Driver 18 for SQL Server}`); pip installs only
the Python binding. The Linux base images used by Azure Functions for Python
(`mcr.microsoft.com/azure-functions/python`, built from the
[Azure/azure-functions-docker](https://github.com/Azure/azure-functions-docker)
repo) install unixODBC and the Microsoft ODBC driver in their Dockerfiles, so
pyodbc is expected to work on Linux Consumption/Flex/Premium plans without a
custom container — unlike Linux **App Service**, whose Python blessed image
does *not* include the driver.

This claim could not be re-verified against a first-party document from this
build environment, so verify it against the target runtime before relying on
it:

1. Check the Dockerfile for your Python version in
   `Azure/azure-functions-docker` (e.g.
   `host/4/*/amd64/python/python311/*.Dockerfile`) for an
   `apt-get install ... msodbcsql18` (or `msodbcsql17`) line.
2. Or at runtime, log `pyodbc.drivers()` from any function (a one-off timer
   or the sweep) — it should list `ODBC Driver 18 for SQL Server`.
3. Or from Kudu/SSH on the deployed app: `odbcinst -q -d`.

If the driver turns out to be absent (or only v17 is present), either deploy
as a custom container that installs `msodbcsql18`, or set
`SQL_CONNECTION_STRING` to reference the driver version that is present.
