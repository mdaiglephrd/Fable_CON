# Microsoft 365 Copilot connector (Graph connector) for the CON database

Puts CON matters/documents into the Microsoft Graph index so they surface in
**Microsoft Search** (Office.com, SharePoint, Bing work results) and ground
**Microsoft 365 Copilot** and the Copilot Studio agent (`../copilot-studio/`).

> Naming: Microsoft renamed "Microsoft Graph connectors" to **"Microsoft 365
> Copilot connectors"**. Admin center labels vary by tenant ring: you may see
> **Search & intelligence > Data sources** or **Copilot > Data connections**.
> Both lead to the same connector gallery.

## E7 licensing (verified 2026-07)

- **Covered by E7** — synced connectors, including this Azure SQL one:
  "Indexing of synced connector data incurs no extra cost for tenants with
  Microsoft 365 licenses," and the licensing table shows Microsoft 365 E7 with
  full support for synced connectors in Microsoft Search **and** Copilot
  grounding/agents, plus federated connectors.
  Source: [Prerequisites for deploying connectors](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/prerequisites)
  (this page is also where `https://learn.microsoft.com/microsoftsearch/licensing` now lands).
- The Copilot Search FAQ additionally states that Microsoft 365 enterprise
  customers with eligible licenses (for example, Microsoft 365 E5 — E7 is a
  strict E5 superset) "are entitled to **unlimited index quota**" for Copilot
  connector ingestion.
  Source: [Copilot Search FAQ — licensing](https://learn.microsoft.com/microsoft-365/copilot/microsoft-365-copilot-search-faq#is-there-an-additional-cost-for-microsoft-365-copilot-search).
- Older pages still describe a per-license index-quota model; if you see quota
  warnings, verify in your tenant: Microsoft 365 admin center > the connectors
  page shows current quota/usage, and connector error codes 1008/1009 indicate a
  quota ceiling ([error reference](https://learn.microsoft.com/microsoft-365/copilot/connectors/error-responses)).
- **Extra purchase (Azure)**: the Azure SQL Database itself — crawls run read
  queries against it (Azure consumption, small for this data size).

## Two paths

| | Path A — Microsoft-built **Azure SQL connector** (recommended) | Path B — custom connector via the Graph API |
|---|---|---|
| Effort | Wizard in the admin center, no code | App registration + code/scripts that push items |
| Content | Rows from a SQL query (our `con.search_view`) | Anything you can PUT — e.g. the FastAPI's enriched JSON |
| Freshness | Scheduled crawls (incremental default 15 min, full daily) | Whenever your pusher runs |
| Body text | Column values only (no rich content/blob parsing) | Full `content` field per item (e.g. OCR text) |
| Maintenance | Microsoft-maintained | Yours |

**Recommendation: Path A.** The searchable payload here is metadata (docket,
applicant, facility, county, outcomes, file names) plus the DocView URL — exactly
what a flattened SQL view can serve, and the wizard handles crawling, schema, and
deletes. Choose Path B only when you want to index *document text* (OCR output)
or API-computed fields — then use [`schema.json`](schema.json) and
[`register-connection.http`](register-connection.http).

---

## Path A — Azure SQL Copilot connector (recommended)

Primary doc: [Azure SQL and Microsoft SQL Server connectors](https://learn.microsoft.com/microsoft-365/copilot/connectors/mssql-connector).

Connector constraints that shaped this design (from that doc):

- Azure SQL path supports **Microsoft Entra ID (OIDC) auth only**, via an app
  registration + client secret; the M365 tenant and the Azure subscription
  hosting the DB must be the **same Entra tenant**.
- Queries must finish in **40 seconds** (OLTP-style); ours is a simple view scan.
- **Column names in the SELECT must be alphanumeric** — hence the camelCase
  aliases in the view.
- No rich-content indexing from columns (HTML/JSON/blob parsing) — metadata only.

### Step 0 — create the view (run once against the database)

One row per **document**, denormalized with its matter's fields (documents are
the natural search item because each has the DocView URL users need to open).
`updatedAt` is the incremental-crawl watermark: the greater of the document's and
matter's `updated_at`.

```sql
CREATE VIEW con.search_view
AS
SELECT
    d.entry_id                                        AS entryId,
    d.docket_id                                       AS docketId,
    CONCAT(d.docket_id, N': ',
           COALESCE(NULLIF(d.file_name, N''), N'Document ' +
                    CAST(d.entry_id AS NVARCHAR(20)))) AS title,
    d.docview_url                                     AS docviewUrl,
    d.file_name                                       AS fileName,
    d.doc_type                                        AS docType,
    d.phase                                           AS phase,
    d.outcome                                         AS outcome,
    d.doc_date                                        AS docDate,
    d.decision_maker                                  AS decisionMaker,
    d.validation_status                               AS validationStatus,
    m.applicant                                       AS applicant,
    m.facility                                        AS facility,
    m.matter_type                                     AS matterType,
    m.action_type                                     AS actionType,
    m.county                                          AS county,
    m.service_area                                    AS serviceArea,
    m.year_filed                                      AS yearFiled,
    m.final_outcome                                   AS finalOutcome,
    st.service_types                                  AS serviceTypes,
    CASE WHEN d.updated_at >= m.updated_at
         THEN d.updated_at ELSE m.updated_at END      AS updatedAt
FROM con.document AS d
JOIN con.matter  AS m ON m.docket_id = d.docket_id
OUTER APPLY (
    SELECT STRING_AGG(mst.service_type, N'; ')
               WITHIN GROUP (ORDER BY mst.service_type) AS service_types
    FROM con.matter_service_type AS mst
    WHERE mst.docket_id = m.docket_id
) AS st;
```

(Matters with zero documents aren't in the view; they're still reachable through
the API/Power BI. If you want them searchable too, that is Path B territory or a
second connection over a matter-level view.)

### Step 1 — Entra app registration (for the connector's DB access)

1. Entra admin center (entra.microsoft.com) > **App registrations > New
   registration**. Name e.g. `con-graph-connector-sql`. Single tenant. Register.
2. Note the **Application (client) ID** and **Directory (tenant) ID**.
3. **Certificates & secrets > New client secret** — note the secret value
   immediately (shown once).
4. Grant the app read access in the database (run in the DB):

   ```sql
   CREATE USER [con-graph-connector-sql] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [con-graph-connector-sql];
   ```

5. Azure SQL firewall: allow the Microsoft 365 crawler ranges for your region
   (NAM: `52.250.92.252/30`, `52.224.250.216/30` per the connector doc — check
   the doc's table for your region) or "Allow Azure services".

### Step 2 — create the connection in the admin center

You must hold the **AI administrator** role (per the connector doc; Search
administrator governs the older Search customization pages).

1. Microsoft 365 admin center (admin.microsoft.com) > **Search & intelligence >
   Data sources** (or **Copilot > Data connections**) > **+ Add** > choose
   **Azure SQL** from the gallery.
2. **Display name**: `GA CON Records` (this labels citations in Copilot).
   Connection ID: `gaconrecords`.
3. **Server / database**: your `SQL_SERVER` and `SQL_DATABASE` values.
4. **Authentication**: Microsoft Entra ID OIDC — paste the client ID + client
   secret from Step 1. Test connection.
5. Optional **Roll out to limited audience** first if you want a pilot group to
   validate results before everyone sees them.

### Step 3 — full crawl query

Paste as the full-crawl SQL (the wizard supplies `@watermark`; ascending sort
means `>` per the doc):

```sql
SELECT entryId, docketId, title, docviewUrl, fileName, docType, phase, outcome,
       docDate, decisionMaker, validationStatus, applicant, facility,
       matterType, actionType, county, serviceArea, yearFiled, finalOutcome,
       serviceTypes, updatedAt
FROM con.search_view
WHERE updatedAt > @watermark
ORDER BY updatedAt ASC
```

- Watermark column: `updatedAt`, data type `DateTime`.
- ACL columns: none — leave unselected; in the **Users** step choose
  **Everyone** (this is public-record data; that decision is documented in
  `../purview/governance.md`).
- In **Edit datatypes**, optionally mark `serviceTypes` as **StringCollection**
  with delimiter `;` so each service type becomes a separate refinable value.

### Step 4 — incremental crawl query (optional but recommended)

Same query, same watermark column (`updatedAt`). Because `updatedAt` already
reflects both matter and document updates, edits made by the validation Power
App and the tag/diff loaders appear in search within one incremental cycle.
No soft-delete column exists in scope (deleted repo docs are only logged in
`con.change_log`, never deleted from `con.document` per DESIGN.md), so skip the
soft-delete settings; the daily full crawl trues everything up.

### Step 5 — Manage properties (schema mapping)

Set these annotations (wizard's "Manage properties" step). Semantic **labels**
are what Search/Copilot key on — `title` and `url` matter most.

| Column | Label | Searchable | Queryable | Retrievable | Refinable | Why |
|---|---|---|---|---|---|---|
| `title` | **Title** | ✔ | ✔ | ✔ | — | The result headline: docket + file name |
| `docviewUrl` | **URL** | — | — | ✔ | — | Clicking the result opens DocView — this is the item URL |
| `updatedAt` | **Last modified date** | — | ✔ | ✔ | — | Freshness ranking + incremental sanity |
| `entryId` | — | — | ✔ | ✔ | — | Exact lookup by Laserfiche entry |
| `docketId` | — | ✔ | ✔ | ✔ | — | People search raw docket strings |
| `fileName` | — | ✔ | ✔ | ✔ | — | |
| `applicant` | — | ✔ | ✔ | ✔ | — | Main free-text hook |
| `facility` | — | ✔ | ✔ | ✔ | — | |
| `decisionMaker` | — | ✔ | ✔ | ✔ | — | |
| `serviceArea` | — | ✔ | — | ✔ | — | |
| `docType` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `phase` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `outcome` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `matterType` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `actionType` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `county` | — | — | ✔ | ✔ | ✔ | 159 counties → refiner |
| `finalOutcome` | — | — | ✔ | ✔ | ✔ | Vocab value → refiner |
| `validationStatus` | — | — | ✔ | ✔ | ✔ | Lets the agent/users filter unverified rows |
| `yearFiled` | — | — | ✔ | ✔ | ✔ | |
| `docDate` | — | — | ✔ | ✔ | ✔ | Date refiner |
| `serviceTypes` | — | ✔ | ✔ | ✔ | ✔ (as StringCollection) | Slice by service type |

Rule of thumb applied above: refiners (vocab-valued columns) are *not* marked
searchable — refinable and searchable are generally mutually exclusive in the
connector schema, and vocab codes belong in filters, not fuzzy text match.

### Step 6 — sync schedule and create

- Incremental crawl: default **every 15 min** is fine (each crawl is one cheap
  view query).
- Full crawl: default **daily**.
- **Create**. First full crawl indexes ~24k items; watch status under the same
  Data sources page.

### Step 7 — surface it (Search verticals + Copilot)

1. **Search vertical** — admin center > Search & intelligence >
   **Customizations > Verticals > + Add**: name `CON Records`, content source =
   the `GA CON Records` connection, enable. Users then get a "CON Records" tab
   in Microsoft Search.
2. **Result type** — Customizations > Result types > + Add: bind to the
   connection and design a layout showing `title`, `applicant`, `county`,
   `finalOutcome`, `validationStatus`, with the link to `docviewUrl`.
3. **Copilot enablement** — connector content is available to Microsoft 365
   Copilot for licensed users once indexed; on current tenants the
   connection-creation wizard/connection settings include the toggle for
   surfacing the connection's data to Copilot experiences ("Copilot
   grounding" / inline results). Verify in your tenant: open the connection in
   the admin center and check its settings page; then in Copilot Chat ask a
   question a CON record answers and confirm a `GA CON Records` citation
   appears. Semantic indexing of connector items requires at least one M365
   Copilot license in the tenant — E7 satisfies this.

---

## Path B — custom connector via the Graph API (index the REST API instead)

**When to bother**: you want items to carry *full document text* (OCR output the
API can serve), matter-level items with aggregated children, or fields computed
by `api/` (e.g. resolved docket variants) — none of which a flat SQL row gives
you. Otherwise Path A wins on maintenance.

How it fits this repo: a small pusher (cron/Azure Function) reads
`GET /matters` and `GET /documents` from the FastAPI app and PUTs items to
Graph. Items consume the same included/"no extra cost" index entitlement as
Path A (same licensing sources above).

1. **App registration**: as Step 1 above, but instead of DB access grant Graph
   **application permission** `ExternalConnection.ReadWrite.OwnedBy` and
   `ExternalItem.ReadWrite.OwnedBy` (admin consent required).
2. **Create the connection, register the schema, push items** — exact raw REST
   calls in [`register-connection.http`](register-connection.http); the schema
   payload (flags matching the Path A table) is [`schema.json`](schema.json).
   Notes:
   - Schema registration is async: the `PATCH .../schema` returns
     `202 Accepted` with an operation URL in the `Location` header — poll it
     until `completed` before pushing items.
   - Each item is `PUT /external/connections/gaconrecords/items/{entry_id}` with
     `properties` (matching the schema), `content` (the free text: OCR excerpt
     or a composed summary), and an `acl` (grant to `everyone` for this
     public-record data).
   - Push updates whenever `GET /changes?since=...` reports in-scope changes,
     mirroring the incremental crawl.
3. Verticals/result types/Copilot surfacing work exactly as in Path A Step 7.
