# Power BI over the CON database (Azure SQL)

Builds a Power BI semantic model + report on `con.matter`, `con.document`,
`con.weekly_report_event`, and `con.change_log`. Companion files:

- [`queries.pq`](queries.pq) — Power Query M for every table (paste into Advanced Editor)
- [`measures.dax`](measures.dax) — all DAX measures (paste one measure at a time)
- [`report-layout.md`](report-layout.md) — recommended report pages and visuals

## Licensing: what E7 covers

- **Covered by E7**: Power BI Pro (part of the E5 baseline inside E7) — authoring in
  Power BI Desktop (free download), publishing to the service, sharing with other
  Pro-licensed users, and **up to 8 scheduled refreshes per day** on shared capacity.
  Shared-capacity limits that matter here: 1 GB max published model size, 2-hour
  refresh timeout, 10 GB uncompressed data processed per refresh.
  Source: [Data refresh in Power BI](https://learn.microsoft.com/power-bi/connect-data/refresh-data).
- **Requires extra purchase**: Power BI Premium / Fabric capacity or Premium Per User
  (48 refreshes/day, >1 GB models, XMLA endpoint). Not needed for this dataset.
- **Requires extra purchase (Azure)**: the Azure SQL Database itself is Azure
  consumption — Power BI queries add negligible load on Import mode, but the DB is
  billed by Azure regardless.

## Import vs DirectQuery: use Import

Recommendation for this database (~24k documents, a few thousand matters, weekly
report events in the low tens of thousands):

- **Import** (recommended). The whole model will compress to a few tens of MB — far
  below the 1 GB shared-capacity cap. Visuals are fast (all in-memory), every DAX
  function works, and you avoid holding the Azure SQL tier hot for every slicer click
  (DirectQuery fires SQL per visual — that is Azure consumption and latency).
  Data freshness: the pipeline loads tags/snapshots/weekly reports in batches, not in
  real time, so "8 scheduled refreshes per day" (every ~2–3 working hours) is more
  than the data actually changes.
- **DirectQuery** only makes sense if you need sub-hour freshness on a dataset too
  big to import. Neither applies here. DirectQuery also disallows some M/DAX
  constructs and has a 1M-row-per-query result limit.

Configure the schedule for 8 slots spread across the working day (e.g. 06:00, 08:00,
10:00, 12:00, 14:00, 16:00, 18:00, 20:00 local) — that is exactly the Pro maximum.

## Step-by-step

### A. Prerequisites

1. Install **Power BI Desktop** (Microsoft Store or https://aka.ms/pbidesktop). Free.
2. Have the Azure SQL server/database names from the repo's environment:
   `SQL_SERVER` (e.g. `myserver.database.windows.net`) and `SQL_DATABASE` (e.g. `condb`).
3. Make sure your Entra user can read the DB. Run in the database (as an admin):

   ```sql
   CREATE USER [analyst@yourtenant.com] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [analyst@yourtenant.com];
   ```

4. Azure SQL firewall must allow your client IP (Azure portal > SQL server >
   Networking) or "Allow Azure services" for the service-side refresh (see step E).

### B. Connect (Get Data)

1. Power BI Desktop > **Home > Get data > SQL Server** (this same connector is used
   for Azure SQL).
2. **Server** = your `SQL_SERVER` value; **Database** = your `SQL_DATABASE` value.
3. **Data connectivity mode** = `Import` (see above).
4. In the credential dialog choose **Microsoft account** (this is the Entra ID /
   organizational sign-in option) and sign in with your E7 account. Do not use
   Database (SQL auth) — the repo standardizes on Entra auth (`ActiveDirectoryDefault`).
5. When the Navigator opens, do **not** tick tables yet — select **Transform Data**
   to open Power Query, then build the queries from [`queries.pq`](queries.pq):
   - **Home > Manage Parameters > New Parameter** twice: `SqlServer` (Text, your
     server) and `SqlDatabase` (Text, your database).
   - For each query in `queries.pq`: **Home > New Source > Blank Query**, open
     **Advanced Editor**, paste the block, rename the query to the name given in the
     file (`Matters`, `Documents`, `WeeklyEvents`, `ChangeLog`, `MatterServiceTypes`,
     `Dates`).
   - The `Matters` query uses `Value.NativeQuery` (a documented SQL text with
     `STRING_AGG` over `con.matter_service_type`). Power BI will prompt to approve
     the **native database query** — review and approve; it is read-only `SELECT`.
6. **Close & Apply**.

### C. Model

1. Model view — create these relationships (single direction, many-to-one unless noted):
   - `Documents[docket_id]` → `Matters[docket_id]`
   - `WeeklyEvents[docket_id]` → `Matters[docket_id]`
     (rows with NULL docket simply do not relate — expected)
   - `MatterServiceTypes[docket_id]` → `Matters[docket_id]`
     (set **cross-filter direction = Both**, or keep Single and use the
     `CROSSFILTER` measure pattern in `measures.dax`)
   - `Documents[doc_date]` → `Dates[Date]`
   - `WeeklyEvents[report_date]` → `Dates[Date]` (mark inactive if you prefer one
     active date path; measures can activate it with `USERELATIONSHIP`)
   - `ChangeLog[detected_date]` → `Dates[Date]`
2. Select the `Dates` table > **Table tools > Mark as date table** > column `Date`.
3. Hide foreign-key columns from report view to keep the field list clean.
4. Paste measures from [`measures.dax`](measures.dax) (Modeling > New measure, one at
   a time; comments in the file explain each).

### D. Publish

1. Save the .pbix. **Home > Publish** > choose a workspace (create one, e.g.
   "GA CON Research" — with Pro you can create workspaces and share to other
   Pro/E7 users).
2. Publishing uploads both the report and the semantic model.

### E. Service-side refresh credentials + schedule

1. In app.powerbi.com open the workspace > semantic model **Settings** (… menu).
2. **Data source credentials** > Edit credentials > Authentication method =
   **OAuth2** (Entra ID), Privacy level = Organizational > sign in. This stores a
   token the service refreshes; if the account's password/policies change, revisit
   this screen (expired credentials are the #1 refresh failure).
3. Azure SQL firewall: the Power BI service connects from Azure — enable
   **"Allow Azure services and resources to access this server"** on the SQL server,
   or add the Power BI region IPs. (No on-premises gateway is needed for Azure SQL.)
4. **Refresh** section > Configure a refresh schedule > add up to **8** time slots
   (Pro/shared-capacity max), local time zone. Enable failure notification emails.
5. Optional: a workspace member with build permission can now create additional
   reports on the same semantic model instead of new imports.

### F. Sharing

- Share the report/app to colleagues: they need Power BI Pro too — every E7 user has
  it. Guests or unlicensed users would need licenses or Premium capacity
  (extra purchase).

## Research layer (v2) tables — richer dashboards

Additive note: the research layer (DESIGN.md "RESEARCH LAYER (v2)", migrations
0006+) adds content tables the model above does not import — most usefully
`con.opinion` (decision metadata: decided dates, published flag, treatment
level), `con.citation` (the citator graph: who cites whom, with a `treatment`
code), and `con.proceeding_stage` (per-docket stage history with outcomes and
durations). Once the editorial pass populates them, add them as Import-mode
queries (same pattern as `queries.pq`) for measures such as:

- **Reversal rate** — of matters that reach an appellate/judicial-review stage
  in `con.proceeding_stage`, the share whose stage outcome is
  `Reversed (appeal)` (optionally counting `Vacated (appeal)` — state the
  definition on the visual, as the existing measures do for approval rate).
- **Citator treatment mix** — count of `con.citation` rows by `treatment`
  (Followed / Distinguished / Criticized / Reversed / Overruled / Cited /
  Neutral), sliced by the cited document's year or topic — a health check on
  which decisions the corpus still relies on.
- **Stage duration** — median `duration_days` by `stage_label` from
  `con.proceeding_stage`, sliceable by service type or county — how long each
  phase of a proceeding actually takes.

Deliberately left as suggestions rather than shipped DAX: these tables fill
during the editorial pass, so build and validate the measures once the data is
real.
