# infra/ — Azure infrastructure (Bicep)

Bicep templates for the Georgia DCH CON research database. Resource-group scope:
`main.bicep` orchestrates the modules in `modules/`; `main.bicepparam` is the
example parameter file.

## What gets created

All names follow `<namePrefix>-<environment>-<suffix>` (default prefix `gacon`,
environment `dev`), tagged `{ project: 'ga-con-database', environment: <env> }`.

| Resource | Name (dev default) | Tier | Ballpark cost / month* |
| --- | --- | --- | --- |
| Log Analytics workspace | `gacon-dev-log` | PerGB2018, 30-day retention | ~$2.30–2.76/GB ingested; $0–5 at this scale |
| Application Insights (workspace-based) | `gacon-dev-appi` | — | billed via the workspace |
| Storage account + containers `index-snapshots`, `weekly-reports`, `tag-exports`, `document-text` | `gacondevst<unique>` | StorageV2, LRS, TLS 1.2, no public blob access | ~$0.02/GB + transactions; $1–5 (first 5 GB free for 12 months) |
| Key Vault | `gacon-dev-kv` | standard, RBAC, soft delete | ~$0.03/10k operations; <$1 |
| SQL logical server + `condb` | `gacon-dev-sql` | GP_S_Gen5_1 serverless, auto-pause 60 min, 32 GB max | ~$0.52/vCore-hour while active + ~$0.12/GB storage; $5–30 for intermittent research use (auto-pause keeps idle compute at $0) |
| Function app + Y1 plan | `gacon-dev-func` | Linux Consumption, Python 3.11 | free grant covers this workload; $0–2 |
| Web app + B1 plan (FastAPI `api/`) | `gacon-dev-api` | Linux Basic B1, Python 3.11 | ~$13 |
| Azure AI Search (`deploySearch=true`) | `gacon-dev-search` | basic, semantic ranker `free` | ~$75 — the biggest fixed cost; set `deploySearch=false` to skip |
| Azure OpenAI (`deployOpenAI=false` by default) | `gacon-dev-aoai` | S0; `gpt-4o-mini` + `text-embedding-3-small` Standard deployments | per-token (gpt-4o-mini ≈ $0.15/1M input, $0.60/1M output; embeddings ≈ $0.02/1M) |
| Static Web App (`deployStaticWebApp=true`) | `gacon-dev-web` | **Free** plan (Microsoft.Web/staticSites) | **$0** — hosts the React console (`web/`); Free plan includes Entra ID auth |
| Document Intelligence (`deployDocIntel=true`) | `gacon-dev-di` | `docIntelSku` **F0** (free) by default | **$0** at F0 (500 pages/month cap); S0 ≈ $1.50/1,000 pages for the initial backfill |

\* US-region list prices, rough planning numbers only — check the
[pricing calculator](https://azure.microsoft.com/pricing/calculator/).

## Free-tier-first cost posture

This deployment is tuned to stay at or near **$0** for intermittent research use. The
only unavoidable fixed cost is the App Service B1 plan (~$13/mo); everything else has a
free tier or free monthly grant:

| Component | Free lever | Notes / honest caveats |
| --- | --- | --- |
| **Azure SQL Database** | Free offer (`sqlUseFreeOffer=true`): GP serverless, **100,000 vCore-seconds + 32 GB data + 32 GB backup free/month** per DB (up to 10 DBs/subscription) | `freeLimitExhaustionBehavior='AutoPause'` pauses the DB until next month once the free vCore-seconds run out (stays $0); switch to `BillOverUsage` to keep it online at standard GP serverless rates. See enablement step below. |
| **Azure Functions** | Consumption (Y1) free grant: 1M executions + 400,000 GB-s/month | The ingestion workload fits comfortably inside the grant. |
| **Static Web Apps** | **Free** plan | $0 hosting for the console; includes free auto-renewing TLS and Entra ID auth. Managed-identity *use* (e.g. Key Vault references) needs the Standard plan — not required here. |
| **Blob Storage** | First **5 GB LRS free for 12 months** | `document-text` extraction output + snapshots/reports are small; well within free/low-cost range. |
| **Document Intelligence** | **F0** free tier: **500 pages/month** | **Honest caveat:** the ~24,290-document CON corpus far exceeds 500 pages/month. Options: (a) batch extraction across many months on F0, or (b) temporarily set `docIntelSku='S0'` for the one-time backfill (~$1.50/1,000 pages ≈ tens of dollars for the corpus), then redeploy at F0 for steady-state. |
| **AI Search vs SQL full-text** | AI Search **Free** tier (50 MB, 3 indexes) *or* skip Search entirely | The module deploys the **basic** tier (~$75/mo — the biggest cost). For a free posture, set `deploySearch=false` and rely on **SQL full-text search** (`fulltextEnabled=true`), or drop to the Search Free tier manually if 50 MB fits your index. Semantic ranker stays on the `free` plan (1,000 requests/month). |
| **Microsoft Entra ID (P2)** | **Included in Microsoft 365 E7** | Conditional Access / PIM / auth features used by the console + API Easy Auth are already covered by the tenant's E7 licensing — no separate Entra premium spend. |
| **Azure OpenAI** | Metered, **optional** (`deployOpenAI=false`) | Only the `/ask` copilot needs it and it is off by default; when enabled it is pure per-token metered usage (no fixed cost). |

Also created: RBAC role assignments (module `roles*.bicep`):

- function app MSI → **Storage Blob Data Contributor** on the storage account
- function app + web app MSI → **Key Vault Secrets User** on the vault
- web app MSI → **Search Index Data Contributor** + **Search Service Contributor**
  on the search service (index management via `api/search_sync.py`)
- web app MSI → **Cognitive Services OpenAI User** on the OpenAI account (when deployed)
- web app MSI → **Cognitive Services User** (`a97b65f3-24c7-4388-baec-2e87135dc908`)
  on the Document Intelligence account (analyze documents via MSI; when deployed)
- the Static Web App identity is granted **nothing** — the console calls the API over HTTPS

`deployOpenAI` defaults to **false** because model availability and quota for
`gpt-4o-mini` / `text-embedding-3-small` vary by region and subscription. Enable
it in a region where you have quota (check *Azure OpenAI → Quotas* in the portal),
or point `AZURE_OPENAI_ENDPOINT` at an existing account instead.

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) ≥ 2.60 with
  Bicep (`az bicep install`), logged in: `az login`
- A subscription where you can create resource groups and role assignments
  (role assignments require `Owner` or `User Access Administrator` on the RG)
- An Entra ID user or group to act as the SQL administrator (the server is
  **Entra-only**; there is no SQL password)

```bash
az account set --subscription <subscription-id>
az group create --name gacon-dev-rg --location eastus2
```

## Deploy

Edit `infra/main.bicepparam` (at minimum `sqlAdminObjectId` + `sqlAdminLogin`):

```bash
# object ID of the admin group (or use `az ad signed-in-user show --query id -o tsv`)
az ad group show --group <group-name> --query id -o tsv
```

Then:

```bash
# validate / preview
az deployment group what-if -g gacon-dev-rg -f infra/main.bicep -p infra/main.bicepparam

# deploy
az deployment group create -g gacon-dev-rg -f infra/main.bicep -p infra/main.bicepparam

# grab the outputs (SQL_SERVER, SEARCH_ENDPOINT, KEY_VAULT_URI, ...)
az deployment group show -g gacon-dev-rg -n main --query properties.outputs
```

## Post-deploy steps (in order)

### 1. Create SQL users for the managed identities

Database access for the MSIs is granted via **T-SQL, not ARM**. Connect to
`condb` as the Entra admin (portal Query Editor, `sqlcmd -G`, or Azure Data
Studio with AAD auth) and run — the bracketed names are the **app names**:

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

(Adjust names if you changed `namePrefix`/`environment`. `db_datareader` +
`db_datawriter` cover the app workloads; migrations run as the admin.)

### 2. Put secrets in Key Vault (out-of-band, never in Bicep)

Both apps get `KEY_VAULT_URI` and the **Key Vault Secrets User** role; secrets
are optional fallbacks (the apps prefer `DefaultAzureCredential`). Key Vault
secret names cannot contain underscores — use dashes in place of `_`:

```bash
az keyvault secret set --vault-name gacon-dev-kv --name SEARCH-API-KEY --value <key>
az keyvault secret set --vault-name gacon-dev-kv --name AZURE-OPENAI-API-KEY --value <key>
```

You need **Key Vault Secrets Officer** (or Administrator) on the vault to write
secrets — RBAC authorization is enabled, so being subscription Owner alone is
not enough for data-plane writes.

### 3. Run schema migrations

As the Entra SQL admin (migrations create schema/tables; the app MSIs cannot):

```bash
export SQL_SERVER=<sqlServerFqdn output>   # e.g. gacon-dev-sql.database.windows.net
export SQL_DATABASE=condb
python -m schema.migrate            # applies schema/migrations/*.sql
# add --skip-fulltext only for environments without full-text support
```

If you run migrations from a local machine, add your client IP to the SQL
firewall first: `az sql server firewall-rule create -g gacon-dev-rg -s gacon-dev-sql -n dev-client --start-ip-address <ip> --end-ip-address <ip>`.

### 4. Deploy the function code

```bash
./functions/deploy.sh gacon-dev-func   # stages common/ + ingest/ into the app folder and publishes
```

### 5. Deploy the API code

The startup command (`gunicorn -k uvicorn.workers.UvicornWorker api.main:app`)
and `SCM_DO_BUILD_DURING_DEPLOYMENT=true` are already configured, so a zip
deploy from the repo root works:

```bash
zip -r api.zip api/ common/ requirements.txt
az webapp deploy -g gacon-dev-rg -n gacon-dev-api --src-path api.zip --type zip
# (or: az webapp up -g gacon-dev-rg -n gacon-dev-api --runtime PYTHON:3.11)
```

Then build/push the search index (when `deploySearch=true`):

```bash
python -m api.search_sync   # creates/updates the con-records index and pushes rows
```

### 6. Configure Easy Auth (Entra) on the web app

The API has **no auth in code**; protect it at the platform level:

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

See [Configure Microsoft Entra authentication](https://learn.microsoft.com/azure/app-service/configure-authentication-provider-aad)
for client-secret/certificate options and restricting access to specific users.

### 7. Deploy the research console (Static Web App) + Entra auth

The `gacon-dev-web` Static Web App (Free plan) is provisioned empty — Bicep does not
link a repo or push content. Build `web/` and deploy the static output with the SWA CLI
(the deployment token comes from the portal → *Static Web App → Manage deployment token*,
or `az staticwebapp secrets list`):

```bash
cd web
npm ci && npm run build            # Vite build -> web/dist
npx @azure/static-web-apps-cli deploy ./dist \
  --deployment-token <swa-deployment-token> --env production
# (or wire a GitHub Actions workflow with the token stored as a repo secret)
```

Auth and API/CORS linkage are configured outside Bicep:

- **Entra ID auth** — the Free plan supports Microsoft Entra ID. Put the auth block in
  `web/staticwebapp.config.json` (route protection + the `azureActiveDirectory` identity
  provider, `openIdIssuer` = `https://login.microsoftonline.com/<tenant-id>/v2.0`) and set
  `AZURE_CLIENT_ID` / the client-secret app-setting name in the SWA portal
  (*Configuration → Application settings*). See
  [Custom authentication](https://learn.microsoft.com/azure/static-web-apps/authentication-custom).
- **API base URL + CORS** — point the SPA at the FastAPI app
  (`https://gacon-dev-api.azurewebsites.net`). The API already receives the console origin as
  `CONSOLE_ORIGIN` (see below); make sure the app's CORS allow-list honors it (add any custom
  domain origins there too). The console calls the API over HTTPS with the signed-in user's
  token — the SWA has no data-plane RBAC of its own.

The console's default hostname is emitted as the `staticWebAppHostname` deployment output.

### 8. Configure Document Intelligence extraction

`deployDocIntel=true` creates `gacon-dev-di` (kind `FormRecognizer`, tier `docIntelSku`,
default **F0**) with a custom subdomain and a system-assigned identity, and grants the API
web app **Cognitive Services User** on it. The API authenticates with its managed identity
(`DefaultAzureCredential`) using the `DOCUMENT_INTELLIGENCE_ENDPOINT` app setting — **no key
is stored** (a `DOCUMENT_INTELLIGENCE_KEY` would only ever be an out-of-band Key Vault
reference, never in Bicep).

Run the extraction (see the runbook in `docs/06`) to produce the JSONL that
`ingest/load_document_text.py` loads into `con.document_text`; extraction output blobs land in
the `document-text` container.

> **F0 page limit:** F0 caps at **500 pages/month**, which the ~24,290-document corpus far
> exceeds. For the one-time backfill, set `param docIntelSku = 'S0'`, redeploy, run the
> extraction, then redeploy at `'F0'` for steady-state — or batch the backfill across months
> on F0.

### 9. Confirm the SQL free offer

`sqlUseFreeOffer=true` (the default) deploys `condb` with the **Azure SQL Database free offer**
(`useFreeLimit=true`, `freeLimitExhaustionBehavior='AutoPause'`): **100,000 vCore-seconds +
32 GB data + 32 GB backup free per month**, per database, up to 10 free databases per
subscription. The existing GP serverless / 32 GB / auto-pause SKU already satisfies the offer's
requirements, so no SKU change is needed.

Confirm and monitor in the portal: *SQL database → Overview* shows a **Free monthly vCore
amount** tile; drill in for the **Free amount remaining / consumed** metrics and (optionally)
set a metric alert near 10,000 vCore-seconds remaining. With `AutoPause`, the database becomes
inaccessible once the monthly free vCore-seconds are used up and resumes at the start of the
next calendar month; set `param sqlUseFreeOffer` / `freeLimitExhaustionBehavior` accordingly, or
switch to `BillOverUsage` on the *Compute + Storage* blade to keep it online for paid overage.
See [Deploy Azure SQL Database for free](https://learn.microsoft.com/azure/azure-sql/database/free-offer).

> Set `sqlUseFreeOffer=false` if this subscription already has its 10 free databases in use, or
> to run `condb` as an ordinary (billed) GP serverless database.

## Hardening (production path)

The defaults favor a low-friction research deployment. Before handling anything
sensitive:

- **Private endpoints**: deploy a VNet and private endpoints for SQL, Storage,
  Key Vault, Search, and OpenAI; integrate the web/function apps with the VNet;
  then set `enablePublicNetworkAccess=false` (removes the SQL public endpoint
  and the `AllowAzureServices` 0.0.0.0 rule — note that rule admits traffic from
  *any* Azure tenant, not just yours).
- **SQL firewall**: while public access is on, prefer per-IP rules over broad ones;
  remove stale developer-IP rules.
- **Storage**: set `allowSharedKeyAccess=false` and move the function app to
  [identity-based connections](https://learn.microsoft.com/azure/azure-functions/functions-reference#connecting-to-host-storage-with-an-identity)
  (`AzureWebJobsStorage__accountName` instead of the connection string; the blob
  data role is already assigned).
- **Key Vault**: pass `enablePurgeProtection=true` to the keyvault module (irreversible),
  restrict `publicNetworkAccess`.
- **Search / OpenAI**: disable key-based auth (`disableLocalAuth` / API keys) once
  everything uses managed identity.
- Restrict SCM/FTPS endpoints and pin CORS on the web app as needed.

## Files

```
infra/
├── main.bicep              # orchestrator (params, modules, outputs)
├── main.bicepparam         # example parameters — edit before deploying
├── README.md
└── modules/
    ├── monitoring.bicep    # Log Analytics + workspace-based App Insights
    ├── storage.bicep       # StorageV2 + blob containers
    ├── keyvault.bicep      # Key Vault (RBAC, soft delete)
    ├── sql.bicep           # SQL server (Entra-only) + condb serverless + firewall
    ├── functions.bicep     # Y1 Linux plan + Python 3.11 function app
    ├── appservice.bicep    # B1 Linux plan + Python 3.11 FastAPI web app
    ├── search.bicep        # Azure AI Search basic (conditional)
    ├── openai.bicep        # Azure OpenAI + model deployments (conditional)
    ├── staticwebapp.bicep  # Static Web App (Free) for the React console (conditional)
    ├── docintelligence.bicep # Document Intelligence (FormRecognizer, F0) (conditional)
    ├── roles.bicep         # storage + key vault role assignments
    ├── roles-search.bicep  # search role assignments (conditional)
    ├── roles-openai.bicep  # OpenAI role assignment (conditional)
    └── roles-docintel.bicep # Document Intelligence role assignment (conditional)
```
