# Building the CON Research Platform — from zero to running, free-tier-first

This is the top-to-bottom walkthrough for standing up the whole platform — database, ingestion,
API, and the research console — starting from **creating your Azure account**, staying on
**free or E7-included tiers** wherever one exists. Every step says what it costs.

Deeper references (this guide sequences them; they carry the exact commands):
- `infra/README.md` — resource-by-resource deploy + post-deploy steps 1–9, free-tier cost table
- `docs/05-metadata-extraction-spec.md` — **what you extract from each document** (your ingestion spec)
- `docs/03-ingestion-runbook.md` — running the loaders
- `docs/02-configuration.md` — every setting
- `docs/04-m365-walkthrough.md` — connecting the M365 E7 layer

**Cost summary up front** (details in `infra/README.md`):

| Layer | Tier | Cost |
|---|---|---|
| Azure SQL Database | Free offer (serverless) | $0 (100k vCore-sec + 32 GB/mo) |
| Functions (ingestion) | Consumption | $0 (1M exec/mo grant) |
| Console hosting | Static Web Apps **Free** | $0 |
| API hosting | App Service **F1** (pilot) or B1 | $0 pilot / ~$13/mo steady |
| Blob Storage | 5 GB LRS free 12 mo | $0 |
| Document Intelligence (OCR) | **F0** | $0 (500 pages/mo — see step 8 caveat) |
| Search | SQL full-text (skip AI Search) | $0 |
| Identity (Entra ID P2), Copilot, Power BI Pro, Purview | **Included in your M365 E7** | $0 extra |
| Azure OpenAI | Off by default | $0 (metered only if you turn it on) |

---

## Phase 1 — Azure account and subscription

1. **Create the Azure account.** Go to https://azure.microsoft.com/free and click *Start free*.
   **Sign in with your Microsoft 365 E7 work account** (same Entra tenant) — this is what lets the
   console, API auth, Copilot, and Purview all share one identity world. The free account gives you
   $200 credit for 30 days, 12 months of free-tier services, and always-free services.
   You'll need a credit card for identity verification; nothing is charged on the free tier.
2. **Install the tooling on your machine:**
   - Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli, then `az login`
   - Bicep: `az bicep install`
   - Python 3.11 + ODBC Driver 18 for SQL Server (to run migrations/loaders locally)
   - Node.js 20+ (only needed later for the console build)
3. **Pick your subscription and region.** `az account show` confirms the subscription. Choose one
   region and stay in it (e.g. `eastus2`). Check that the region supports the SQL free offer and
   Document Intelligence (both are broadly available; `eastus`/`eastus2` are safe).
4. **Create the resource group:**
   ```bash
   az group create -n gacon-dev-rg -l eastus2
   ```

## Phase 2 — Deploy the infrastructure (Bicep)

5. **Fill in `infra/main.bicepparam`.** Every parameter is documented; the two you must set:
   - `sqlAdminObjectId` — your Entra object id: `az ad signed-in-user show --query id -o tsv`
   - `sqlAdminLogin` — your UPN (email)
   Free-tier posture is the default: `sqlUseFreeOffer=true`, `docIntelSku='F0'`,
   `deployStaticWebApp=true`, `deployOpenAI=false`. Two decisions:
   - `appServicePlanSku`: **`F1`** ($0, fine for pilot; cold starts, 60 CPU-min/day) or `B1` (~$13/mo).
   - `deploySearch`: **`false`** for the free posture — the API's SQL full-text search covers keyword
     search at $0. (Turn AI Search on later only if you want vector/semantic ranking.)
6. **Deploy:**
   ```bash
   az deployment group create -g gacon-dev-rg -f infra/main.bicep -p infra/main.bicepparam
   ```
   Then follow **`infra/README.md` → Post-deploy steps 1–3** in order:
   create the SQL users for the managed identities (exact T-SQL there), put the two or three
   secrets in Key Vault, and run the migrations:
   ```bash
   python -m schema.migrate     # applies 0001–0009: inventory + research layer + seeds
   ```

## Phase 3 — Load the data (you drive this; the specs tell you what to capture)

7. **Produce the tag export** per **`docs/05-metadata-extraction-spec.md` §A** (the v1 columns plus
   the new research-layer columns) and load it:
   ```bash
   python -m ingest.load_tags export.csv --rejects rejects.csv
   ```
8. **Extract document text.** Stage your PDFs/OCR output, run them through **Document Intelligence**
   (endpoint is in the deployment outputs), and emit the JSONL format in **docs/05 §B**. Because you
   run the extraction yourself, grant *your own* identity data-plane access first:
   `az role assignment create --assignee <your-object-id> --role "Cognitive Services User" --scope <doc-intel-resource-id>`
   (the API's managed identity already has this role). Then:
   ```bash
   python -m ingest.load_document_text extracted.jsonl --apply
   ```
   **F0 caveat:** free tier = 500 pages/month. The ~24,290-document corpus exceeds that; either batch
   the backfill across months at $0, or temporarily redeploy with `docIntelSku='S0'`
   (~$1.50/1,000 pages — a one-time cost measured in tens of dollars), then drop back to F0.
9. **Keep the pipelines running** (optional but recommended): drop weekly report PDFs and index
   snapshots into their Storage containers — the Functions app ingests them automatically
   (`docs/03-ingestion-runbook.md`).
10. **Editorial pass.** Headnotes, treatment flags, topic classification, synopses, and citation
    treatments are entered/verified in the console's validation screens (docs/05 "Editorial fields —
    minimum viable vs. full" gives the priority order).

## Phase 4 — API + console

11. **Deploy the API** — `infra/README.md` step 5 (zip deploy) and step 6 (Easy Auth via Entra —
    included in E7).
12. **Deploy the console** — `infra/README.md` step 7: build `web/` (`npm ci && npm run build`),
    deploy to the Static Web App (Free), and wire **Entra ID sign-in** via
    `web/staticwebapp.config.json`. Set `CONSOLE_ORIGIN` on the API if you customized the domain.
13. **Smoke test:** sign in to the console → search a docket → open a document → open its docket
    timeline → check the citator tab. (API-level checks: `curl .../health`, `/cases/{entry_id}`,
    `/dockets/{docket}/proceeding`.)

## Phase 5 — Connect the M365 E7 layer (all included in your license)

14. Follow **`docs/04-m365-walkthrough.md`**:
    - **Graph connector → Microsoft Search / M365 Copilot** — the natural-language ask-questions
      path, included with E7 (this is why Azure OpenAI stays off).
    - **Power BI Pro** dashboards over the same database.
    - **Purview** labels, retention, audit, and AI-agent governance.
    - **Power Apps is retired** — the console's own screens replace it (and remove the premium
      connector license that Power Apps + Azure SQL would have required).

## When you outgrow the free tiers

| Signal | Move |
|---|---|
| SQL free vCore-seconds exhausted mid-month (DB auto-pauses) | Set `freeLimitExhaustionBehavior='BillOverUsage'` or move off the free offer |
| API cold starts hurt / F1 CPU quota hit | `appServicePlanSku='B1'` (~$13/mo) |
| Keyword search isn't enough | `deploySearch=true` (AI Search basic ~$75/mo) + `api/search_sync.py` |
| Copilot answers need to live inside the console UI | `deployOpenAI=true` (metered) — `/ask` endpoint is already built |
