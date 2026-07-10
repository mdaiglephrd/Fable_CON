# 04 — Microsoft 365 (E7) integration walkthrough

The Azure side ([01](01-azure-deployment.md)–[03](03-ingestion-runbook.md))
gives you a populated database and an API. This guide is the top-level
narrative for the other half: surfacing that data to researchers **inside your
Microsoft 365 E7 tenant** — dashboards, a validation app, org-wide search,
Copilot grounding, and governance.

The authoritative, step-numbered build guides live under
[`m365/`](../m365/README.md); this page gives you the ordering, the licensing
decisions, the tenant prerequisites, and the end-to-end acceptance checklist.

---

## 1. How the Azure side connects to the E7 tenant

One identity fabric does all the work:

- **Same Entra tenant.** The Azure subscription hosting the SQL database and
  the M365 tenant must share the Entra tenant — the Microsoft-built Azure SQL
  Copilot connector requires it (`m365/graph-connector/README.md`), and it is
  what makes per-user database auth possible everywhere else.
- **Entra-only SQL auth.** The server has no SQL passwords. Every M365 surface
  reaches the database as an Entra principal that you create as a database
  user (`CREATE USER [...] FROM EXTERNAL PROVIDER`): analysts for Power BI,
  each Power App user, and one app registration for the Graph connector's
  crawls.
- **Firewall.** While `enablePublicNetworkAccess = true`, the
  `AllowAzureServices` rule admits the Power BI service and Power Platform;
  the Graph connector crawler needs either that rule or its published regional
  IP ranges (listed in `m365/graph-connector/README.md`, step 1.5).
- **Read vs write.** Power BI and the Graph connector are read-only
  (`db_datareader`); only Power App validators get write access — and even
  then, ideally a tighter custom role with UPDATE on `con.document` only
  (`m365/powerapp/README.md`, step 2.7).

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
- Purview: sensitivity labels, DLP, retention, audit, DSPM for AI, agent
  governance

**Extra purchase**:
- **All Azure consumption** — Azure SQL, Functions, App Service, AI Search
  (~$75/mo fixed for basic), Azure OpenAI (per token). E7 never covers Azure.
- **Power Apps SQL Server connector** — it's a *premium* connector, not
  covered by the Power Apps rights seeded in M365/E7. Every validation-app
  user needs Power Apps Premium / per-app / pay-as-you-go
  (`m365/powerapp/README.md` has the citations and license-free alternatives).
- Power BI Premium/Fabric capacity (not needed at this data size)
- Copilot Studio usage by unlicensed users or external channels
- Purview Data Map / Unified Catalog *scanning of Azure SQL* (Azure billing)

Practical consequence: an analyst typing "CON applications for freestanding
EDs in Gwinnett" into Copilot Chat costs nothing beyond licenses you already
own, while the same question through `POST /ask` meters AI Search + Azure
OpenAI. Prefer the connector path for humans; reserve `/ask` and
`/search/semantic` for scripts and embedded integrations. (This is also why
[02-configuration.md](02-configuration.md)'s decision table suggests
`deploySearch = false` unless you have that programmatic need.)

---

## 3. Tenant prerequisites

Have these sorted before starting; each sub-guide states its own in detail:

1. **Licenses**: Microsoft 365 E7 for the researchers (includes Power BI Pro
   and M365 Copilot). Budget for Power Apps premium licensing for validators
   (decision in `m365/powerapp/README.md`).
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
3. **Data**: the acceptance checklist (§6) assumes guides 01–03 are done and
   real data is loaded.

---

## 4. Build order (per `m365/README.md`)

Work through the folders in this order — later steps depend on earlier ones:

### Step 1 — Power BI report (`m365/powerbi/`)

*Delivers*: dashboards over `con.matter` / `con.document` /
`con.weekly_report_event` / `con.change_log` — filing trends, outcomes by
county/service type, and a completeness/validation audit page. Fastest value:
needs only read access to the database and the Pro license already in E7.

*Key choices made for you in the guide*: **Import mode** (not DirectQuery) with
up to 8 refreshes/day; Entra ("Microsoft account") auth; paste-in artifacts —
[`queries.pq`](../m365/powerbi/queries.pq),
[`measures.dax`](../m365/powerbi/measures.dax),
[`report-layout.md`](../m365/powerbi/report-layout.md). Follow
[`m365/powerbi/README.md`](../m365/powerbi/README.md) steps A–F.

### Step 2 — Graph connector / Microsoft Search (`m365/graph-connector/`)

*Delivers*: CON documents in the Microsoft Graph index — findable from
Microsoft Search (Office.com, SharePoint, Bing work results) with a dedicated
"CON Records" vertical, and the **grounding foundation for every Copilot
experience**, at no indexing cost on E7.

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

### Step 3 — Copilot Studio agent (`m365/copilot-studio/`)

*Delivers*: the "GA CON Research Assistant" — a conversational agent grounded
on the Step-2 connection, answering questions like "what happened with the
Fulton County NICU application?" with citations that deep-link to DocView.
Published to Teams and Microsoft 365 Copilot; usage by your E7 users is
covered. Build guide: `m365/copilot-studio/` (grounding depends on Step 2
being live and crawled).

### Step 4 — Power Apps validation app (`m365/powerapp/`)

*Delivers*: the researcher validation UI — browse/filter matters, open
documents in DocView, and work the `Unvalidated` queue with
Validate/Correct/Reject buttons that write back to `con.document`
(closing the re-validation loop from
[03-ingestion-runbook.md](03-ingestion-runbook.md#4-the-re-validation-loop)).

*Built last deliberately*: it is the one artifact with a real licensing
dependency (premium SQL Server connector — see §2). Read the licensing section
of [`m365/powerapp/README.md`](../m365/powerapp/README.md) **first**, decide on
per-app licenses vs the license-free alternatives it lists, then build the
three screens from `m365/powerapp/screens/*.fx.md`.

### Step 5 (parallel track) — Purview governance (`m365/purview/`)

*Delivers*: labels, retention, DLP, audit, and AI-agent oversight. Not a
sequential step — start it once the Graph connector and Copilot agent exist,
because those are the things Purview's AI governance features watch. Guide:
`m365/purview/` (the graph-connector guide already points at
`m365/purview/governance.md` for the "index as Everyone" public-records
decision).

---

## 5. Freshness model (how updates propagate)

- Database ← pipelines: batch (tag loads manual; snapshots/reports on upload +
  daily sweep).
- Power BI: scheduled refresh, up to 8×/day (Import mode).
- Microsoft Search / Copilot: incremental crawl default **every 15 min**, full
  crawl daily; the `con.search_view.updatedAt` watermark reflects both matter
  and document updates, so Power App validations and loader edits surface
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
5. **Copilot cites a document** — in Copilot Chat (and/or the published
   Copilot Studio agent), ask a question only a CON record answers; confirm
   the response carries a `GA CON Records` citation that opens the right
   document.
6. **Validation round-trips from the Power App** — pick an `Unvalidated`
   document in the app's ValidationScreen, mark it Validated, then confirm:
   `con.document.validation_status = 'Validated'` with `validated_by`/
   `validated_date` stamped (SQL or `GET /documents/{entry_id}`); the row
   drops out of the app's queue; and after the next incremental crawl the
   item's `validationStatus` refiner value updates in Microsoft Search.
7. **(Loop closure)** — when the next index snapshot modifies that document,
   it returns to `Unvalidated` (guide 03 §4) and reappears in the queue: the
   whole pipeline is now self-maintaining.
