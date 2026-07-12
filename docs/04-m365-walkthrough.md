# 04 — Microsoft 365 (E7) integration walkthrough

The Azure side ([01](01-azure-deployment.md)–[03](03-ingestion-runbook.md))
gives you a populated database, an API, and the **CON Research Console** — the
React SPA in `web/` that is the **primary researcher UI** (search, case reader,
citator, docket timelines, stats, and the validation workflow; build guide:
[06-research-console-buildout.md](06-research-console-buildout.md)). This guide
is the top-level narrative for the other half: wrapping that platform with your
**Microsoft 365 E7 tenant** — org-wide search, Copilot grounding, executive
dashboards, and governance.

The authoritative, step-numbered build guides live under
[`m365/`](../m365/README.md); this page gives you the ordering, the licensing
decisions, the tenant prerequisites, and the end-to-end acceptance checklist.

---

## 1. How the Azure side connects to the E7 tenant

One identity fabric does all the work:

- **Same Entra tenant.** The Azure subscription hosting the SQL database and
  the M365 tenant must share the Entra tenant — the Microsoft-built Azure SQL
  Copilot connector requires it (`m365/graph-connector/README.md`), and it is
  what lets the console, the API's Easy Auth, Power BI, and Copilot all share
  one identity world.
- **Entra-only SQL auth.** The server has no SQL passwords. Every surface
  reaches the database as an Entra principal that you create as a database
  user (`CREATE USER [...] FROM EXTERNAL PROVIDER`): analysts for Power BI and
  one app registration for the Graph connector's crawls. Researchers themselves
  never touch SQL — they sign in to the console, which calls the FastAPI app
  (its managed identity is the database user).
- **Firewall.** While `enablePublicNetworkAccess = true`, the
  `AllowAzureServices` rule admits the Power BI service; the Graph connector
  crawler needs either that rule or its published regional IP ranges (listed
  in `m365/graph-connector/README.md`, step 1.5).
- **Read vs write.** Power BI and the Graph connector are read-only
  (`db_datareader`). Writes — validation and editorial edits — flow **console
  → FastAPI → `con.document`** through the API's managed identity; no per-user
  write grants are needed anymore (the retired Power App required one per
  validator — see `m365/powerapp/README.md`).

---

## 2. The E7-first principle: what's covered, what's metered

E7 already pays for an end-user natural-language search stack, so the guides
steer researchers there and keep the metered Azure services for programmatic
use. Verified coverage table (with sources) in
[`m365/README.md`](../m365/README.md); the short version:

**Covered by E7** (no extra cost):
- Power BI Pro — authoring, publishing, sharing, up to 8 scheduled refreshes/day
- Copilot connectors (Graph connectors) — indexing into Microsoft Graph,
  Microsoft Search verticals/result types
- Microsoft 365 Copilot grounding on connector data (E7 includes the Copilot
  license)
- Copilot Studio agent **usage by Copilot-licensed users** (i.e. your E7 users)
- Entra ID P2 + the Entra Suite — Conditional Access for the console + API app
  surfaces
- Purview: sensitivity labels, DLP, retention, audit, DSPM for AI, agent
  governance

**Extra purchase**:
- **All Azure consumption** — Azure SQL, Functions, App Service, Static Web
  Apps, AI Search, Azure OpenAI. E7 never covers Azure — but the console/API
  free-tier posture keeps this at ~$0 (cost table in
  [06-research-console-buildout.md](06-research-console-buildout.md)).
- Power BI Premium/Fabric capacity (not needed at this data size)
- Copilot Studio usage by unlicensed users or external channels
- Purview Data Map / Unified Catalog *scanning of Azure SQL* (Azure billing)

**Removed cost line — Power Apps premium licensing.** Earlier revisions
budgeted a per-user extra purchase here: the Power Apps validation app used the
premium SQL Server connector, so every validator needed a Power Apps Premium /
per-app / pay-as-you-go license on top of E7. Retiring that app in favor of the
console (Static Web Apps Free + the existing API) **removes that licensing line
entirely** — the verified citations and the retirement note are preserved in
[`m365/powerapp/README.md`](../m365/powerapp/README.md).

Practical consequence: an analyst typing "CON applications for freestanding
EDs in Gwinnett" into Copilot Chat costs nothing beyond licenses you already
own, while the same question through `POST /ask` meters AI Search + Azure
OpenAI. Prefer the connector path for humans; reserve `/ask` and
`/search/semantic` for scripts and embedded integrations. (This is also why
[02-configuration.md](02-configuration.md)'s decision table suggests
`deploySearch = false` for the free posture.)

---

## 3. Tenant prerequisites

Have these sorted before starting; each sub-guide states its own in detail:

1. **Licenses**: Microsoft 365 E7 for the researchers (includes Power BI Pro
   and M365 Copilot). No Power Platform licensing is needed anymore — the
   validation UI is the console (see §2's removed cost line).
2. **Admin roles**:
   - **Graph connector**: the **AI administrator** Entra role to create the
     connection in the Microsoft 365 admin center (per
     `m365/graph-connector/README.md`; Search-customization pages are governed
     by Search administrator). You'll also create an Entra **app
     registration** + client secret for the connector's DB access.
   - **Copilot Studio**: maker access to a Power Platform environment to build
     and publish the agent; usage by your E7 (Copilot-licensed) users is
     covered. Details in `m365/copilot-studio/`.
   - **Purview**: admin access to the Microsoft Purview (compliance) portal —
     Compliance Administrator-level rights; specifics in `m365/purview/`.
   - **SQL**: you remain the Entra SQL admin from guide 01 — you'll be running
     `CREATE USER ... FROM EXTERNAL PROVIDER` several times.
3. **Data + platform**: the acceptance checklist (§6) assumes guides 01–03 are
   done, real data is loaded, and the console is deployed and signing users in
   (guide 01 step 12 / docs/06 Phase 4) — the M365 sequence below is docs/06's
   **Phase 5**.

---

## 4. Build order (per `m365/README.md`)

Prerequisite: the console and API are Azure-side deliverables built first
(docs/06 Phases 1–4). Then work through the folders in this order — later
steps depend on earlier ones:

### Step 1 — Graph connector / Microsoft Search (`m365/graph-connector/`)

*Delivers*: CON documents in the Microsoft Graph index — findable from
Microsoft Search (Office.com, SharePoint, Bing work results) with a dedicated
"CON Records" vertical, and the **grounding foundation for every Copilot
experience**, at no indexing cost on E7. This is the natural-language path E7
already pays for (and the reason Azure OpenAI stays off).

*What you'll do* (details in
[`m365/graph-connector/README.md`](../m365/graph-connector/README.md)): create
the `con.search_view` flattened view in the database (Step 0 — run once);
register an Entra app + create its read-only DB user; create the
Microsoft-built **Azure SQL connector** connection (`GA CON Records`, ID
`gaconrecords`) in the admin center; paste the full/incremental crawl queries
keyed on the `updatedAt` watermark; apply the property schema (title/URL
labels, refiners for county/doc type/outcome/validation status); add the
search vertical and result type. Path B (custom Graph API connector) exists
for when you want full OCR text indexed — the README explains when to bother.

### Step 2 — Copilot Studio agent (`m365/copilot-studio/`)

*Delivers*: the "GA CON Research Assistant" — a conversational agent grounded
on the Step-1 connection, answering questions like "what happened with the
Fulton County NICU application?" with citations, and **deep-linking its
answers into the console** (the agent is configured with the console URL —
the same value as the API's `CONSOLE_ORIGIN` setting). Published to Teams and
Microsoft 365 Copilot; usage by your E7 users is covered. Build guide:
`m365/copilot-studio/` (grounding depends on Step 1 being live and crawled).

### Step 3 — Power BI report (`m365/powerbi/`)

*Delivers*: executive dashboards over `con.matter` / `con.document` /
`con.weekly_report_event` / `con.change_log` — filing trends, outcomes by
county/service type, and a completeness/validation audit page. Needs nothing
but read access to the database and the Pro license already in E7.

*Key choices made for you in the guide*: **Import mode** (not DirectQuery) with
up to 8 refreshes/day; Entra ("Microsoft account") auth; paste-in artifacts —
[`queries.pq`](../m365/powerbi/queries.pq),
[`measures.dax`](../m365/powerbi/measures.dax),
[`report-layout.md`](../m365/powerbi/report-layout.md). Follow
[`m365/powerbi/README.md`](../m365/powerbi/README.md) steps A–F.

### Step 4 (parallel track) — Purview governance (`m365/purview/`)

*Delivers*: labels, retention, DLP, audit, and AI-agent oversight — now also
covering the **console + API as Entra-authenticated app surfaces**
(`m365/purview/governance.md` §8). Not a sequential step — start it once the
Graph connector and Copilot agent exist, because those are the things
Purview's AI governance features watch. The graph-connector guide already
points at `m365/purview/governance.md` for the "index as Everyone"
public-records decision.

> **No Power App step.** The Power Apps validation app has been removed from
> the build order — it is retired in favor of the console, which also deletes
> the per-user premium-license line this order used to end on. Historical
> reference: [`m365/powerapp/README.md`](../m365/powerapp/README.md).

---

## 5. Freshness model (how updates propagate)

- Database ← pipelines: batch (tag/text loads manual; snapshots/reports on
  upload + daily sweep).
- Console: live — it reads the API (and writes validations) directly.
- Power BI: scheduled refresh, up to 8×/day (Import mode).
- Microsoft Search / Copilot: incremental crawl default **every 15 min**, full
  crawl daily; the `con.search_view.updatedAt` watermark reflects both matter
  and document updates, so console validations and loader edits surface
  within one incremental cycle.
- Azure AI Search (`con-records`, if deployed): only when you run
  `python -m api.search_sync` — schedule it or run after each bulk load.

---

## 6. Full-system acceptance checklist

Run top to bottom; each line names its verification surface.

1. **Data loaded** — `python -m ingest.load_tags ... --rejects rejects.csv`
   completed with an acceptable reject count; SQL sanity:
   `SELECT COUNT(*) FROM con.matter;` and `... con.document;` look right;
   at least one snapshot registered in `con.index_snapshot` and one weekly
   report in `con.weekly_report_event` (blob path per guide 03).
2. **API answers** — authenticated `GET /matters?limit=1` returns rows;
   `GET /matters/{some docket}` rolls up variants, documents, and weekly
   events; `GET /search?q=<an applicant name>` ranks hits (full-text on).
3. **Power BI refreshes** — the published semantic model completes a scheduled
   refresh in app.powerbi.com (Settings → Refresh history) and the report
   pages show current counts matching the SQL sanity checks.
4. **Microsoft Search finds a docket** — after the first full crawl completes
   (admin center → the connection's status), search a known docket id or
   applicant at office.com; the "CON Records" vertical returns the item and
   its link opens DocView.
5. **Copilot cites a document — and deep-links to the console** — in Copilot
   Chat (and/or the published Copilot Studio agent), ask a question only a CON
   record answers; confirm the response carries a `GA CON Records` citation
   that opens the right document, **and** that the Copilot Studio agent's
   answer includes a console deep link that opens the matching record in the
   signed-in console (`m365/copilot-studio/` configures the agent with the
   console URL).
6. **Validation round-trips from the console** — sign in to the console, pick
   an `Unvalidated` document in its validation screen, mark it Validated, then
   confirm: `con.document.validation_status = 'Validated'` with
   `validated_by`/`validated_date` stamped (SQL or
   `GET /documents/{entry_id}`); the row drops out of the console's queue; and
   after the next incremental crawl the item's `validationStatus` refiner
   value updates in Microsoft Search.
7. **(Loop closure)** — when the next index snapshot modifies that document,
   it returns to `Unvalidated` (guide 03 §4) and reappears in the console's
   queue: the whole pipeline is now self-maintaining.
