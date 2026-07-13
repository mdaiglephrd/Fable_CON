# 02 — Configuration reference

Every setting the system reads, where it is consumed, and how to supply it in
each environment. Canonical names live in [`DESIGN.md`](../DESIGN.md)
("Environment variables") and [`.env.example`](../.env.example); this page adds
the per-module wiring, verified against the code.

---

## 1. Where configuration lives

| Environment | Mechanism |
|---|---|
| Local workstation (CLIs, `uvicorn`) | `.env` file — `cp .env.example .env` and fill in. Nothing auto-loads it; export the variables (`set -a; source .env; set +a`) or use your shell tooling. All config reads are lazy, so missing variables fail at call time with the variable named, never at import time. |
| Local Functions host (`func start`) | `functions/local.settings.json` — `cp functions/local.settings.json.example functions/local.settings.json` (gitignored; never commit). |
| Azure Function app / Web app | **App Settings**. `infra/main.bicep` sets the non-secret ones at deploy time (tables below say which). Change with `az webapp config appsettings set` / `az functionapp config appsettings set`. |
| Secrets in Azure | **Key Vault references** in App Settings — see [§5](#5-key-vault-references). |

---

## 2. Settings reference

### Database (read by `common/db.py:get_connection`, used by every DB-touching module: `schema.migrate`, `ingest.*`, `functions/`, `api/`, `api.search_sync`)

| Variable | Meaning | Set by Bicep? |
|---|---|---|
| `SQL_CONNECTION_STRING` | Full ODBC connection string. **Wins over the pair below when set.** | no |
| `SQL_SERVER` | Logical server FQDN, e.g. `gacon-dev-sql.database.windows.net` (the `sqlServerFqdn` output). | yes (both apps) |
| `SQL_DATABASE` | Database name, e.g. `condb`. | yes (both apps) |

When `SQL_CONNECTION_STRING` is absent, the connection string is built as
`Driver={ODBC Driver 18 for SQL Server};Server=tcp:<SQL_SERVER>,1433;Database=<SQL_DATABASE>;Encrypt=yes;TrustServerCertificate=no;Authentication=ActiveDirectoryDefault;`
— see [§7](#7-connection-auth-options) for the auth decision.

### Storage / ingestion (read by `functions/processing.py` and the trigger bindings in `functions/function_app.py`)

| Variable | Meaning | Set by Bicep? |
|---|---|---|
| `AzureWebJobsStorage` | Functions host storage **and** the connection the blob triggers listen on (`connection="AzureWebJobsStorage"` in `function_app.py`). Also the second fallback for downloads/listing. | yes (function app; full connection string with account key) |
| `STORAGE_CONNECTION` | Storage connection string used by `blob_service_client()` for blob downloads and container listing — first choice in the fallback chain. | yes (function app) |
| `STORAGE_ACCOUNT_URL` | `https://<account>.blob.core.windows.net`. Third fallback: used with `DefaultAzureCredential` (managed identity) when **neither** connection string is set. The identity-based hardening path (`infra/README.md` "Hardening"); the function MSI already holds Storage Blob Data Contributor. | no |
| `SNAPSHOT_CONTAINER` | Container watched for index snapshots. Code default `index-snapshots`; also used literally in the trigger path `%SNAPSHOT_CONTAINER%/{name}`, so the setting **must exist** on the function app. | yes (`index-snapshots`) |
| `REPORT_CONTAINER` | Container watched for weekly report PDFs. Code default `weekly-reports`; same binding-expression note. | yes (`weekly-reports`) |
| `SWEEP_CRON` | NCRONTAB schedule for the `daily_sweep` timer (`schedule="%SWEEP_CRON%"`). No in-code default — the value comes from the Bicep parameter `sweepCron` (default `0 0 6 * * *`) or `local.settings.json`; if the app setting is missing the timer binding fails to resolve. Format in [§6](#6-sweep_cron-ncrontab-format). | yes |

The third container created by Bicep, `tag-exports`, is a **drop zone only** —
no trigger watches it; tag exports are loaded manually with
`python -m ingest.load_tags` (see the runbook).

### API search behavior (read by `api/main.py` and `api/search_client.py`; also used by `api.search_sync`)

| Variable | Meaning | Default in code | Set by Bicep? |
|---|---|---|---|
| `FULLTEXT_ENABLED` | `true`/`1`/`yes` → `/search`, `/matters?q=`, `/documents?q=` use `CONTAINSTABLE`; anything else → LIKE fallback. Must match whether `0005_fulltext.sql` was applied. | `true` | yes (web app, from param `fulltextEnabled`) |
| `SEARCH_ENDPOINT` | `https://<name>.search.windows.net`. Required by `/search/semantic`, `/ask`, and `search_sync`; when missing those return HTTP 503 naming the setting. | — | yes (web app; empty string when `deploySearch = false`) |
| `SEARCH_API_KEY` | Optional; when absent `DefaultAzureCredential` is used (web app MSI has the Search roles). | — | no (secret — use a Key Vault reference if you opt for keys) |
| `SEARCH_INDEX` | AI Search index name. | `con-records` | yes (web app) |

### Azure OpenAI (read by `api/search_client.py`; used by `/ask`, hybrid-search embeddings, and `search_sync` vectors)

| Variable | Meaning | Default in code | Set by Bicep? |
|---|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | `https://<account>.openai.azure.com`. Required for `/ask`; optional for `/search/semantic` (without it, hybrid degrades to keyword + semantic ranking) and `search_sync` (vectors omitted). | — | yes (web app; empty when `deployOpenAI = false`) |
| `AZURE_OPENAI_API_KEY` | Optional; Entra token via `DefaultAzureCredential` when absent (web app MSI holds Cognitive Services OpenAI User when deployed by this Bicep). | — | no (secret) |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat model deployment name. | `gpt-4o-mini` | yes (web app) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment name (1536-dim expected by the index). | `text-embedding-3-small` | yes (web app) |
| `AZURE_OPENAI_API_VERSION` | AOAI API version. Note: read by `api/search_client.py` and documented in `api/README.md`, but absent from `.env.example` and DESIGN.md's env list — rarely needs changing. | `2024-06-01` | no |

### Research console + Document Intelligence (research layer v2)

| Variable | Meaning | Set by Bicep? |
|---|---|---|
| `DOCUMENT_INTELLIGENCE_ENDPOINT` | The Document Intelligence endpoint (`docIntelEndpoint` output), set as an **App Service (web app) setting**. Auth is the API's **managed identity** — the Bicep grants it Cognitive Services User on the account — so there is **no key**: a `DOCUMENT_INTELLIGENCE_KEY` would only ever be an out-of-band Key Vault reference, never in Bicep (`infra/README.md` step 8). The extraction run itself is **operator-driven** (docs/06 Phase 3); the repo's Python never calls Document Intelligence — `ingest/load_document_text.py` consumes the run's JSONL output. | yes (web app; empty when `deployDocIntel = false`) |
| `CONSOLE_ORIGIN` | The research console's origin(s) (`https://<staticWebAppHostname>`, comma-separated if you add more), read by `api/main.py` to configure `CORSMiddleware` (allow-origins = this list; GET/POST/DELETE; credentials on). Empty = same-origin only, no CORS headers. If you add a custom domain to the console, update this setting — `infra/README.md` step 7. | yes (web app; empty when `deployStaticWebApp = false`) |

Two related non-settings:

- **The console's own URL** is the `staticWebAppHostname` deployment output —
  not an env var any Python module reads. The SPA's Entra auth and API base URL
  are configured in `web/staticwebapp.config.json` + the SWA portal application
  settings (`infra/README.md` step 7).
- **`POST /deadlines/calculate` needs no configuration at all** — it is a pure
  computation over `common/deadline_rules.py` (no DB, no Azure service). The
  other research routers run on the same `SQL_*` settings as the v1 endpoints
  and add no new variables.

### Key Vault

| Variable | Meaning | Set by Bicep? |
|---|---|---|
| `KEY_VAULT_URI` | `https://<vault>.vault.azure.net`. DESIGN.md reserves this as "when set, missing secrets are read from Key Vault", and Bicep sets it on both apps (which also hold the Key Vault Secrets User role). **As of this writing no Python module reads it** — it is informational/reserved. To actually feed a secret into a process, use a Key Vault *reference* app setting ([§5](#5-key-vault-references)) or a plain env var locally. | yes (both apps) |

### Platform settings (set by Bicep; you normally never touch these)

| Variable | Where | Value |
|---|---|---|
| `FUNCTIONS_WORKER_RUNTIME` | function app | `python` |
| `FUNCTIONS_EXTENSION_VERSION` | function app | `~4` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | both apps | from the monitoring module |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | web app | `true` — makes `az webapp deploy --type zip` run the Oryx build that installs `requirements.txt` |

---

## 3. Which module reads what (quick matrix)

| | `SQL_*` | `STORAGE_*` / `AzureWebJobsStorage` | `SNAPSHOT/REPORT_CONTAINER`, `SWEEP_CRON` | `FULLTEXT_ENABLED` | `SEARCH_*` | `AZURE_OPENAI_*` |
|---|---|---|---|---|---|---|
| `schema/migrate.py` | ✔ | | | | | |
| `ingest/load_tags.py` | ✔ | | | | | |
| `ingest/index_diff.py --apply` | ✔ | | | | | |
| `ingest/weekly_report_parser.py --apply` | ✔ | | | | | |
| `functions/` | ✔ | ✔ | ✔ | | | |
| `api/main.py` (DB endpoints) | ✔ | | | ✔ | | |
| `api/routers/*` (research endpoints) | ✔ | | | | | |
| `api/semantic.py` (`/search/semantic`, `/ask`) | | | | | ✔ | ✔ |
| `api/search_sync.py` | ✔ | | | | ✔ | ✔ (vectors) |
| `ingest/load_document_text.py --apply` | ✔ | | | | | |

(`POST /deadlines/calculate` in `api/routers/deadlines.py` reads nothing —
pure computation.)

---

## 4. Local `.env` vs Azure App Settings

- **Local**: copy `.env.example` → `.env`. Minimum for DB work: `SQL_SERVER` +
  `SQL_DATABASE` (with `az login`) or `SQL_CONNECTION_STRING`. Add `SEARCH_*` /
  `AZURE_OPENAI_*` only when exercising those endpoints. For local Functions
  runs, use `functions/local.settings.json` instead (`Values` map — same names).
- **Azure**: the Bicep already set every non-secret setting listed above.
  Anything you change by hand:
  ```bash
  az webapp config appsettings set -g gacon-dev-rg -n gacon-dev-api \
    --settings FULLTEXT_ENABLED=true
  az functionapp config appsettings set -g gacon-dev-rg -n gacon-dev-func \
    --settings SWEEP_CRON="0 0 6 * * *"
  ```
  App-setting changes restart the app.

---

## 5. Key Vault references

To surface a Key Vault secret as an app-setting environment variable, set the
setting's **value** to a Key Vault reference:

```
@Microsoft.KeyVault(SecretUri=https://gacon-dev-kv.vault.azure.net/secrets/SEARCH-API-KEY/)
```

- The trailing slash / no version pins "latest"; append `<version>/` to pin one.
- Works because both app MSIs hold **Key Vault Secrets User** (assigned by
  `infra/modules/roles.bicep`).
- Secret names use dashes (`SEARCH-API-KEY`) — Key Vault forbids underscores —
  while the app-setting **name** keeps the underscore form the code reads:

```bash
az webapp config appsettings set -g gacon-dev-rg -n gacon-dev-api --settings \
  "SEARCH_API_KEY=@Microsoft.KeyVault(SecretUri=https://gacon-dev-kv.vault.azure.net/secrets/SEARCH-API-KEY/)"
```

Verify resolution in the portal (Configuration → the setting shows a green
check) — a red cross usually means the MSI lacks the role or the URI is wrong.

---

## 6. `SWEEP_CRON` (NCRONTAB) format

Azure Functions timers use **six-field NCRONTAB**, one field more than Unix
cron: `{second} {minute} {hour} {day} {month} {day-of-week}`, evaluated in
**UTC** on this Linux plan.

| Expression | Meaning |
|---|---|
| `0 0 6 * * *` | daily at 06:00:00 UTC (the default) |
| `0 30 */6 * * *` | every 6 hours at :30 |
| `0 0 6 * * 1-5` | 06:00 UTC, weekdays only |

Don't paste a five-field Unix cron string — the host rejects it at startup.

---

## 7. Connection-auth options

**Option A — `ActiveDirectoryDefault` (recommended, and the only option
against the deployed server).** Set `SQL_SERVER` + `SQL_DATABASE` and leave
`SQL_CONNECTION_STRING` unset. `DefaultAzureCredential` resolves, in order:
managed identity (in Azure), then developer credentials (`az login`, VS Code)
locally. Each principal must exist as a database user
(`CREATE USER [...] FROM EXTERNAL PROVIDER`).

**Option B — full `SQL_CONNECTION_STRING`.** Wins whenever set. The
`.env.example` sample shows SQL auth (`Uid=...;Pwd=...`) — note that **this
will not work against the server this repo deploys**, which is Entra-only
(`azureADOnlyAuthentication: true`; no SQL logins exist). Use Option B for:

- a local/dev SQL Server or container that does use SQL auth;
- overriding the ODBC driver name (e.g. a machine that only has
  `ODBC Driver 17 for SQL Server` — see `functions/README.md`'s ODBC section);
- Entra variants such as `Authentication=ActiveDirectoryInteractive` if
  `ActiveDirectoryDefault` misbehaves on your workstation.

---

## 8. Decision table

Each decision, its options, and a recommendation for a solo E7 owner:

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | **`deploySearch`** — pay ~$75/mo for Azure AI Search? | `true`: `/search/semantic` + `/ask` work, `search_sync` has a target. `false`: those endpoints return 503; SQL full-text (`/search`) still works; end-user NL search goes through the E7 Graph connector instead (see [04-m365-walkthrough.md](04-m365-walkthrough.md)). | **`false`** — this is the free-tier posture (docs/06): SQL full-text covers keyword search for the console and API at $0, and the E7-first principle sends natural-language questions to Microsoft Search/Copilot, which cost nothing extra. Flip to `true` later only for a concrete programmatic/embedded retrieval need (re-run `search_sync` after). Note the Bicep default is still `true` — set it explicitly. |
| 2 | **`deployOpenAI`** — deploy Azure OpenAI? | `true`: `/ask` answers and vectors get computed (per-token billing). `false` (default): `/ask` 503s; `/search/semantic` degrades gracefully to keyword+semantic. You may instead point `AZURE_OPENAI_ENDPOINT` at an existing account. | Stays **`false`** — the Copilot path (Graph connector + M365 Copilot, included in E7) is the ask-questions surface; `/ask` is the metered alternative for when answers must live inside the console. Enable only with `deploySearch = true`, in a region with `gpt-4o-mini` + `text-embedding-3-small` quota. Pointless without Search. |
| 3 | **`FULLTEXT_ENABLED`** (+ the `fulltextEnabled` Bicep param) | `true`: `CONTAINSTABLE` ranked search — requires `0005_fulltext.sql` applied. `false`: LIKE fallback (slower, unranked, but works anywhere). | **`true`**. Azure SQL Database supports full-text; only set `false` if you deliberately ran `migrate --skip-fulltext`. Keep the app setting and the migration state in agreement. |
| 4 | **`searchSemanticSearch`** — semantic ranker plan (only if `deploySearch=true`) | `free`: 1,000 semantic queries/month, then errors on semantic calls (the API auto-retries without semantic ranking — see `api/semantic.py`). `standard`: per-request billing, no cap. `disabled`. | **`free`**. A solo research workload rarely exceeds 1,000/month, and the API degrades gracefully. |
| 5 | **SQL auth mode** | A: `ActiveDirectoryDefault` (per-principal DB users, no secrets). B: `SQL_CONNECTION_STRING`. | **A** everywhere. B only for non-Azure dev databases or driver overrides (§7). |
| 6 | **Search/OpenAI credentials** | MSI via `DefaultAzureCredential` (roles already assigned by Bicep) vs `SEARCH_API_KEY`/`AZURE_OPENAI_API_KEY` (via Key Vault references). | **MSI**. Keys only as a break-glass or for the one-off local `search_sync` run (or grant yourself the roles instead). |
| 7 | **Functions storage auth** | Connection strings (`AzureWebJobsStorage`/`STORAGE_CONNECTION`, as deployed) vs `STORAGE_ACCOUNT_URL` + MSI. | Connection strings are fine to start; move to identity-based (`STORAGE_ACCOUNT_URL`, `allowSharedKeyAccess=false`) on the hardening pass (`infra/README.md`). |
| 8 | **`enablePublicNetworkAccess`** | `true` (default; public endpoint + AllowAzureServices rule) vs `false` (requires private endpoints + VNet integration first). | **`true`** for the research build; note the AllowAzureServices caveat (admits any Azure tenant's traffic) and plan the hardening pass before sensitive use. |
| 9 | **`sqlAdminPrincipalType`** | `User` (your account) vs `Group`. | **`User`** for a solo owner; `Group` the moment a second person might need admin. |
| 10 | **`appServicePlanSku`** — API plan | `F1` (Free): $0, 60 CPU-min/day, no Always-On, cold starts after idle. `B1`: ~$13/mo, Always-On, no daily CPU quota. | **`F1` for the pilot**, `B1` once cold starts hurt or you hit the daily CPU quota (the upgrade table in docs/06). Note the Bicep default is `B1` — set `F1` explicitly for the free posture. |
| 11 | **`docIntelSku`** — Document Intelligence tier | `F0` (free): capped at **500 pages/month** — fine for steady-state trickle extraction. `S0`: ~$1.50/1,000 pages, no cap. | **`F0`** steady-state. For the one-time corpus backfill (~24,290 documents far exceeds 500 pages/mo) either batch across months on F0 or temporarily redeploy with `S0`, run the extraction, then drop back to `F0` (`infra/README.md` step 8). |
