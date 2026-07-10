# 01 — Azure deployment, end to end

This guide takes you from an empty Azure subscription to a working CON research
backend: SQL database with schema applied, blob-triggered ingestion Functions,
the FastAPI query/search API behind Entra login, and (optionally) Azure AI
Search + Azure OpenAI for `/search/semantic` and `/ask`.

Depth lives in the module READMEs — this guide is the ordering and the
decision points:

- [`infra/README.md`](../infra/README.md) — every resource, costs, hardening
- [`schema/README.md`](../schema/README.md) — migration runner details
- [`functions/README.md`](../functions/README.md) — trigger behavior, local runs, ODBC caveat
- [`api/README.md`](../api/README.md) — endpoint reference

Everything below was verified against `infra/main.bicep`, `infra/main.bicepparam`,
and the module code in this repo.

---

## 1. Prerequisites

On your workstation:

1. **Azure CLI ≥ 2.60** with Bicep: `az bicep install`, then `az login`.
2. **Python 3.11** with a virtualenv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt        # pyodbc, fastapi, azure-* SDKs, openai
   ```
3. **ODBC Driver 18 for SQL Server** (plus unixODBC on Linux/macOS). `common/db.py`
   hardcodes `Driver={ODBC Driver 18 for SQL Server}` — migrations, loaders, and
   `api/search_sync.py` all fail without it. Install per
   [Microsoft's instructions](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
   for your OS.
4. **Azure Functions Core Tools v4** (`func`) — used by `functions/deploy.sh`.
   (There is a zip-deploy fallback that needs only the Azure CLI; see step 8.)
5. **`zip`** — used for the API zip deploy in step 9.

On the subscription:

6. Rights to **create resource groups** and, on the resource group, **create role
   assignments** — the deployment assigns data-plane RBAC roles to the app
   managed identities, which requires **Owner** or **User Access Administrator**
   on the resource group.
7. To write Key Vault secrets in step 6 you also need the **Key Vault Secrets
   Officer** role on the vault (RBAC authorization is on; subscription Owner
   alone does not grant data-plane writes).
8. An **Entra ID user or group to act as SQL administrator**. The SQL server is
   deployed **Entra-only** (`azureADOnlyAuthentication: true` in
   `infra/modules/sql.bicep`) — there is no SQL password, and classic
   `Uid=/Pwd=` SQL logins will not work against it. As a solo builder, using
   your own user account is fine (see the parameter table below).

---

## 2. Create the resource group

```bash
az account set --subscription <subscription-id>
az group create --name gacon-dev-rg --location eastus2
```

Pick any region; every resource defaults to the resource group's location
unless you override the `location` parameter. If you plan to set
`deployOpenAI = true`, pick a region where you have `gpt-4o-mini` and
`text-embedding-3-small` quota (portal: *Azure OpenAI → Quotas*).

---

## 3. Fill in `infra/main.bicepparam`

Edit [`infra/main.bicepparam`](../infra/main.bicepparam). Complete parameter
reference (all defined in `infra/main.bicep`):

| Parameter | Required? | Default | What to put in it / how to find the value |
|---|---|---|---|
| `namePrefix` | no | `gacon` | 3–12 chars, lowercase letters/digits/hyphens. Prefixes every resource name (`<namePrefix>-<environment>-<suffix>`). |
| `environment` | no | `dev` | One of `dev` \| `test` \| `prod`. Used in names and tags. |
| `location` | no | resource-group location | Uncomment only to place resources in a different region than the RG. `az account list-locations -o table` for names. |
| `tags` | no | `{ project: 'ga-con-database', environment: <env> }` | Extra tags if you want them. |
| `sqlAdminObjectId` | **yes** | — | Entra **object ID** of the SQL administrator. For yourself: `az ad signed-in-user show --query id -o tsv`. For a group: `az ad group show --group <name> --query id -o tsv`. |
| `sqlAdminLogin` | **yes** | — | The display name matching that object ID: your UPN (`az ad signed-in-user show --query userPrincipalName -o tsv`) for a user, or the group display name. |
| `sqlAdminPrincipalType` | no | `Group` | `User` \| `Group` \| `Application`. **Decision:** solo builder → set `'User'` and use your own object ID; a group is better if anyone else may ever need admin. Must match what `sqlAdminObjectId` points at. |
| `sqlAdminTenantId` | no | deployment tenant | Only override for cross-tenant admins. `az account show --query tenantId -o tsv`. |
| `sqlDatabaseName` | no | `condb` | Database name; env var `SQL_DATABASE` must match it later. |
| `enablePublicNetworkAccess` | no | `true` | `true` = public endpoint + the `AllowAzureServices` (0.0.0.0) firewall rule. Set `false` only after building private endpoints (see `infra/README.md` "Hardening"). |
| `deploySearch` | no | `true` | Azure AI Search basic (~$75/month — the biggest fixed cost). Needed for `/search/semantic` and `/ask`. Decision guidance in [02-configuration.md](02-configuration.md). |
| `searchSemanticSearch` | no | `free` | `disabled` \| `free` (1,000 semantic requests/month cap) \| `standard` (billed per request). Recommendation: `free`. |
| `deployOpenAI` | no | `false` | Deploys an Azure OpenAI account with `gpt-4o-mini` + `text-embedding-3-small`. Off by default because regional model availability and quota vary. You can instead point `AZURE_OPENAI_ENDPOINT` at an existing account. |
| `openAiChatCapacity` | no | `8` | Thousands of tokens-per-minute for the chat deployment (only used when `deployOpenAI = true`). |
| `openAiEmbeddingCapacity` | no | `50` | Same, for embeddings. |
| `openAiChatModelVersion` | no | `2024-07-18` | `gpt-4o-mini` model version. |
| `openAiEmbeddingModelVersion` | no | `1` | `text-embedding-3-small` model version. |
| `sweepCron` | no | `0 0 6 * * *` | Six-field NCRONTAB for the daily catch-up sweep (`SWEEP_CRON` app setting) — default is 06:00 UTC daily. Format in [02-configuration.md](02-configuration.md). |
| `fulltextEnabled` | no | `true` | Sets the API's `FULLTEXT_ENABLED` app setting. Keep `true` — Azure SQL Database supports full-text and migration `0005_fulltext.sql` creates the indexes (step 7). |
| `logRetentionDays` | no | `30` | Log Analytics retention, 30–730. |
| `useUniqueStorageSuffix` | no | `true` | Appends `uniqueString(resourceGroup().id)` to the storage account name for global uniqueness. Leave `true`. |

Only `sqlAdminObjectId` and `sqlAdminLogin` have no usable default.

---

## 4. Deploy the Bicep

```bash
# preview what will be created
az deployment group what-if -g gacon-dev-rg -f infra/main.bicep -p infra/main.bicepparam

# deploy
az deployment group create -g gacon-dev-rg -f infra/main.bicep -p infra/main.bicepparam

# capture the outputs — you will need these values repeatedly
az deployment group show -g gacon-dev-rg -n main --query properties.outputs
```

Outputs (names from `infra/main.bicep`): `sqlServerFqdn` (→ `SQL_SERVER`),
`functionAppName`, `webAppName`, `searchEndpoint` (→ `SEARCH_ENDPOINT`; empty
when `deploySearch = false`), `storageAccountName`, `keyVaultUri`
(→ `KEY_VAULT_URI`), `appInsightsConnectionString`.

What now exists (dev defaults): `gacon-dev-log` + `gacon-dev-appi`
(monitoring), `gacondevst<unique>` storage with containers `index-snapshots`,
`weekly-reports`, `tag-exports`, `gacon-dev-kv`, `gacon-dev-sql` + `condb`
(GP_S_Gen5_1 serverless, auto-pause 60 min), `gacon-dev-func` (Linux
Consumption, Python 3.11), `gacon-dev-api` (Linux B1, Python 3.11), and — if
enabled — `gacon-dev-search` / `gacon-dev-aoai`. RBAC roles for the two
managed identities are assigned automatically (see `infra/README.md`).

---

## 5. Post-deploy step 1: SQL users for the managed identities

Database access for the managed identities is granted via **T-SQL, not ARM**.

1. If you will connect from your workstation, open the SQL firewall for your IP
   first:
   ```bash
   az sql server firewall-rule create -g gacon-dev-rg -s gacon-dev-sql \
     -n dev-client --start-ip-address <your-ip> --end-ip-address <your-ip>
   ```
   (Find your IP with `curl -s ifconfig.me`.)
2. Connect to `condb` **as the Entra admin** — portal Query Editor, `sqlcmd -G`,
   or Azure Data Studio with AAD auth — and run (bracketed names are the **app
   names**; adjust if you changed `namePrefix`/`environment`):

   ```sql
   -- ingestion function app
   CREATE USER [gacon-dev-func] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [gacon-dev-func];
   ALTER ROLE db_datawriter ADD MEMBER [gacon-dev-func];

   -- FastAPI web app
   CREATE USER [gacon-dev-api] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [gacon-dev-api];
   ALTER ROLE db_datawriter ADD MEMBER [gacon-dev-api];
   ```

`db_datareader` + `db_datawriter` cover the app workloads; migrations run as
the admin (step 7). Note: the serverless database auto-pauses after 60 idle
minutes — the first connection after a pause can take ~30–60 s or time out
once; just retry.

---

## 6. Post-deploy step 2: Key Vault secrets (only if you use API keys)

Both apps run on `DefaultAzureCredential` (managed identity) by default, so
**this step is optional**. If you choose key-based auth for Search or Azure
OpenAI (see the decision table in [02-configuration.md](02-configuration.md)),
store the keys in Key Vault — never in Bicep or code. Key Vault secret names
cannot contain underscores; use dashes:

```bash
az keyvault secret set --vault-name gacon-dev-kv --name SEARCH-API-KEY --value <key>
az keyvault secret set --vault-name gacon-dev-kv --name AZURE-OPENAI-API-KEY --value <key>
```

You need **Key Vault Secrets Officer** on the vault to write secrets. To feed a
secret into an app as an environment variable, use a **Key Vault reference**
app setting — exact syntax and commands in
[02-configuration.md](02-configuration.md#key-vault-references).

---

## 7. Post-deploy step 3: schema migrations

Run as the Entra SQL admin (the app MSIs cannot create schemas/tables). From
the repo root, with your venv active and `az login` done —
`ActiveDirectoryDefault` picks up your Azure CLI credential:

```bash
export SQL_SERVER=gacon-dev-sql.database.windows.net   # the sqlServerFqdn output
export SQL_DATABASE=condb

python -m schema.migrate --dry-run    # should list 0001..0005
python -m schema.migrate
```

Applies, in order: `0001_schema_and_vocab.sql`, `0002_core_tables.sql`,
`0003_operational_tables.sql`, `0004_indexes.sql`, `0005_fulltext.sql`, each
recorded in `con.schema_migrations`.

**The `--skip-fulltext` decision.** Azure SQL Database supports full-text
search, so for this deployment run **without** the flag. `--skip-fulltext`
exists for environments that can't run full-text DDL (local dev containers,
tests). Two properties to know (from `schema/migrate.py` and
`schema/README.md`):

- Skipped full-text files are **not recorded**, so a later plain
  `python -m schema.migrate` applies `0005_fulltext.sql` then. That is all
  "running fulltext later" takes.
- Full-text files run with **autocommit** (full-text DDL cannot run in a user
  transaction), so a mid-file failure is not rolled back — see the
  troubleshooting table in [03-ingestion-runbook.md](03-ingestion-runbook.md).

If (and only if) you skip full-text permanently, set the API app setting
`FULLTEXT_ENABLED=false` so `/search`, `/matters?q=`, `/documents?q=` use the
LIKE fallback instead of erroring.

---

## 8. Post-deploy step 4: deploy the Functions code

```bash
./functions/deploy.sh gacon-dev-func     # or: FUNCTION_APP_NAME=gacon-dev-func ./functions/deploy.sh
```

The script stages `function_app.py`, `processing.py`, `host.json`,
`functions/requirements.txt` **plus the repo-root `common/` and `ingest/`
packages** into `functions/.build/` and runs
`func azure functionapp publish gacon-dev-func --python` from there (remote
Oryx build installs the requirements). Requires Core Tools v4 and `az login`.

No Core Tools? Use the commented fallback at the bottom of
`functions/deploy.sh` (zip + `az functionapp deployment source config-zip`) —
but first set `SCM_DO_BUILD_DURING_DEPLOYMENT=true` and
`ENABLE_ORYX_BUILD=true` as app settings on the **function app** (Bicep does
not set them there; it only sets `SCM_DO_BUILD_DURING_DEPLOYMENT` on the web
app):

```bash
az functionapp config appsettings set -g gacon-dev-rg -n gacon-dev-func \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true
```

After deployment you should see three functions on the app:
`snapshot_blob_trigger`, `report_blob_trigger`, `daily_sweep`.

---

## 9. Post-deploy step 5: deploy the API code (zip deploy with SCM build)

The Bicep already configured the startup command
(`gunicorn -k uvicorn.workers.UvicornWorker api.main:app`) and
`SCM_DO_BUILD_DURING_DEPLOYMENT=true`, so a zip deploy from the repo root
works — Oryx installs the repo-root `requirements.txt` server-side:

```bash
zip -r api.zip api/ common/ requirements.txt
az webapp deploy -g gacon-dev-rg -n gacon-dev-api --src-path api.zip --type zip
```

(Alternative: `az webapp up -g gacon-dev-rg -n gacon-dev-api --runtime PYTHON:3.11`.)

---

## 10. Post-deploy step 6: build and populate the AI Search index

Skip this step if `deploySearch = false`.

`python -m api.search_sync` creates/updates the `con-records` index and pushes
every matter, document, and weekly event. You run it from your workstation, so
**you** (not the web app MSI) need data-plane access to the search service.
Pick one:

- **Managed-identity style (recommended):** grant yourself the same roles the
  web app has — **Search Service Contributor** and **Search Index Data
  Contributor** on `gacon-dev-search` — then rely on `DefaultAzureCredential`
  (your `az login`).
- **Admin key:** `export SEARCH_API_KEY=$(az search admin-key show --service-name gacon-dev-search -g gacon-dev-rg --query primaryKey -o tsv)`

Then:

```bash
export SEARCH_ENDPOINT=https://gacon-dev-search.search.windows.net   # searchEndpoint output
export SQL_SERVER=gacon-dev-sql.database.windows.net
export SQL_DATABASE=condb
# optional, for content_vector embeddings:
# export AZURE_OPENAI_ENDPOINT=https://gacon-dev-aoai.openai.azure.com

python -m api.search_sync                # add --skip-vectors to skip embeddings explicitly
```

Flags (from the argparse block): `--recreate` (delete and rebuild the index),
`--skip-vectors`, `--batch-size 200`. Vectors are automatically omitted when
Azure OpenAI is not configured; the index still defines the field, so you can
re-run with vectors later. Re-run `search_sync` whenever the database content
changes materially (it uses `merge_or_upload`, so re-runs are safe).

---

## 11. Post-deploy step 7: Easy Auth (Entra) on the API

The API has **no auth in code** — do not skip this on any internet-facing
deployment. Run the smoke tests in step 12 first (Easy Auth breaks anonymous
`curl`), then:

```bash
# create an app registration for the site
az ad app create --display-name gacon-dev-api \
  --web-redirect-uris https://gacon-dev-api.azurewebsites.net/.auth/login/aad/callback

# require Entra login for all requests
az webapp auth microsoft update -g gacon-dev-rg -n gacon-dev-api \
  --client-id <appId-from-previous-step> \
  --issuer https://login.microsoftonline.com/<tenant-id>/v2.0
az webapp auth update -g gacon-dev-rg -n gacon-dev-api \
  --enabled true --action RedirectToLoginPage --redirect-provider azureActiveDirectory
```

See `infra/README.md` step 6 for the Microsoft Learn pointer on client
secrets/certificates and restricting to specific users.

---

## 12. Smoke tests

Run these **before** enabling Easy Auth (or afterwards with a browser session
instead of `curl`).

1. **API is alive** (no DB involved):
   ```bash
   curl https://gacon-dev-api.azurewebsites.net/health
   # → {"status":"ok"}
   curl https://gacon-dev-api.azurewebsites.net/vocab/county
   # → {"name":"county","items":[...159 counties...],"count":159}
   ```
2. **API can reach SQL** (proves the MSI user from step 5 works):
   ```bash
   curl 'https://gacon-dev-api.azurewebsites.net/matters?limit=1'
   # → {"items":[],"total":0,...} on an empty DB — a 500 here means SQL access failed
   ```
   First call after an auto-pause may be slow; retry once.
3. **Blob ingestion round-trip.** Upload a tiny synthetic snapshot and watch it
   become the baseline:
   ```bash
   printf '%s\n' '{"id": 1, "name": "smoke-test", "ext": "pdf", "path": "/CON/smoke", "pages": 1}' \
     | gzip > index-2026-07-10.jsonl.gz

   az storage blob upload --account-name <storageAccountName output> \
     --container-name index-snapshots --name index-2026-07-10.jsonl.gz \
     --file index-2026-07-10.jsonl.gz --auth-mode login
   ```
   (`--auth-mode login` requires **Storage Blob Data Contributor** on the
   account for *your* user — the Bicep grants it only to the function MSI. Use
   `--auth-mode key` if you'd rather not add a role.)

   Within a couple of minutes (blob triggers on Consumption plans can lag),
   check the ledger as the SQL admin:
   ```sql
   SELECT * FROM con.processed_blob;
   -- expect blob_name = 'index-snapshots/index-2026-07-10.jsonl.gz',
   -- status = 'succeeded', detail = 'baseline snapshot registered: entries=1 max_entry_id=1'
   SELECT * FROM con.index_snapshot;
   ```
4. **Clean up the smoke-test baseline** before loading real snapshots — the
   diff engine always diffs against the highest `snapshot_id`:
   ```sql
   DELETE FROM con.index_snapshot WHERE blob_name = 'index-2026-07-10.jsonl.gz';
   DELETE FROM con.processed_blob WHERE blob_name = 'index-snapshots/index-2026-07-10.jsonl.gz';
   ```
   and delete the blob:
   ```bash
   az storage blob delete --account-name <storage> --container-name index-snapshots \
     --name index-2026-07-10.jsonl.gz --auth-mode login
   ```
5. **Function health in App Insights** (`gacon-dev-appi` → Logs):
   ```kusto
   traces | where message has "snapshot_blob_trigger" | order by timestamp desc | take 20
   exceptions | order by timestamp desc | take 20
   ```
6. **Search endpoints** (when `deploySearch = true`, after step 10):
   ```bash
   curl 'https://gacon-dev-api.azurewebsites.net/search/semantic?q=hospice&k=3'
   ```
   A 503 naming `SEARCH_ENDPOINT` means the app setting is empty
   (`deploySearch` was false at deploy time); anything else means the index is
   answering. `/ask` additionally needs `AZURE_OPENAI_ENDPOINT` configured.
7. **After enabling Easy Auth**: `curl -i https://gacon-dev-api.azurewebsites.net/health`
   should now return a **302 redirect** to `login.microsoftonline.com` — that
   is the success signal.

Next: [02-configuration.md](02-configuration.md) for the full settings
reference, then [03-ingestion-runbook.md](03-ingestion-runbook.md) to load
real data.
