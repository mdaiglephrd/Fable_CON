# Power Apps canvas app — CON browse & validation

A tablet-layout canvas app with three screens over the `con` schema:

| Screen | File | Purpose |
|---|---|---|
| BrowseScreen | [`screens/BrowseScreen.fx.md`](screens/BrowseScreen.fx.md) | Search + filter matters (county / matter type / outcome / year / service type) |
| MatterDetailScreen | [`screens/MatterDetailScreen.fx.md`](screens/MatterDetailScreen.fx.md) | One matter: fields, documents (with DocView launch links), weekly events |
| ValidationScreen | [`screens/ValidationScreen.fx.md`](screens/ValidationScreen.fx.md) | Work queue of `validation_status = 'Unvalidated'` documents; Validate / Correct / Reject buttons that `Patch()` the row |

Each `.fx.md` file gives the screen purpose, the control tree, then each
control's relevant properties as paste-in Power Fx.

## Licensing — read this first (verified 2026-07)

The app connects to Azure SQL through the **SQL Server connector**, and that
connector is classified **Premium**:

- The Microsoft connector reference marks SQL Server as a Premium-tier connector:
  [SQL Server connector](https://learn.microsoft.com/connectors/sql/) (listed under
  [Premium connectors](https://learn.microsoft.com/connectors/connector-reference/connector-reference-premium-connectors)).
- The Power Platform licensing FAQ states: "The SQL, Azure, and Dynamics 365
  connectors ... are now classified as Premium ... A standalone Power Apps or Power
  Automate plan license is required to access all Premium, on-premises, and custom
  connectors."
  ([Power Platform licensing FAQs](https://learn.microsoft.com/power-platform/admin/powerapps-flow-licensing-faq))
- The Power Apps plan seeded into Microsoft 365 (and therefore into E7) explicitly
  lists "Access on-premises data or use premium or custom connectors" as **not
  included** ([Licensing overview for Microsoft Power Platform](https://learn.microsoft.com/power-platform/admin/pricing-billing-skus#power-apps-and-power-automate-for-microsoft-365)).
- The E3/E5/E7 comparison page carries the footnote "Power Platform licenses are
  not included with Microsoft 365 Copilot"
  ([license feature overview](https://learn.microsoft.com/microsoft-365/copilot/microsoft-365-copilot-license-feature-overview)).

**Honest conclusion: this app is NOT covered by E7 alone.** Every user who runs it
needs one of (current names; check the
[Power Apps pricing page](https://www.powerapps.com/pricing) for prices):

1. **Power Apps Premium** (per user, all premium apps),
2. **Power Apps per app** (this one app only — usually the cheapest fit for a small
   validation team), or
3. **Power Platform pay-as-you-go** (per active user per app per month, billed to an
   Azure subscription).

Note the same is true of the workaround ideas: a *custom connector* calling the
repo's FastAPI is also premium, so it does not dodge the license. Genuinely
license-free alternatives are: do validation edits through a small web page served
by the existing FastAPI app (no Power Platform involved), or keep validation in the
Power BI audit page + SQL scripts. If your tenant already holds standalone Power
Platform licenses on top of E7, verify in your tenant: Microsoft 365 admin center >
Billing > Licenses — look for "Power Apps Premium" or "Power Apps per app" entries.

Everything else in this guide (the connector setup, Entra auth, the Power Fx) is
identical whichever license you land on.

## Build guide

### 1. Create the app

1. Go to https://make.powerapps.com, pick the target **environment** (default
   environment is fine for a first build; a dedicated environment is better
   governance — see `../purview/governance.md`).
2. **+ Create > Start with a blank canvas > Tablet** (tablet layout gives room for
   the gallery + detail panes these screens assume).
3. **Settings > Display**: confirm orientation Landscape. Name the app
   `GA CON Validation`.

### 2. Add the Azure SQL connection (SQL Server connector + Entra auth)

1. In the app: left rail **Data > Add data > search "SQL Server"**.
2. Choose the **SQL Server** connector (this one connector serves both Azure SQL
   and on-prem SQL; for Azure SQL no gateway is needed).
3. Authentication type: choose **Microsoft Entra ID Integrated** — each user's own
   Entra identity is used at runtime, which matches the repo's auth posture and
   means SQL permissions are enforced per user. (Avoid "SQL Server Authentication";
   apart from being against the repo convention, an implicitly-shared SQL-auth
   connection embeds shared credentials in the app.)
4. Server: `<yourserver>.database.windows.net`, Database: your `SQL_DATABASE`.
5. Pick tables. You need:
   - `con.matter`, `con.document`, `con.weekly_report_event`
   - vocab tables for the filter dropdowns: `con.county`, `con.vocab_matter_type`,
     `con.vocab_outcome`, `con.vocab_service_type`
   - `con.matter_service_type` (service-type filtering)
6. **Naming**: Power Apps displays the table as `[con].[matter]` in the data pane
   but in formulas you reference it as `'con.matter'` (single quotes because of the
   dot). All formulas in `screens/` use that form.
7. Every app user must also be a database user:
   `CREATE USER [user@tenant.com] FROM EXTERNAL PROVIDER;` then
   `ALTER ROLE db_datareader ADD MEMBER [user@tenant.com];` and, for validators,
   `ALTER ROLE db_datawriter ADD MEMBER [user@tenant.com];` (or a tighter custom
   role with UPDATE only on `con.document`). Azure SQL firewall must allow the
   Power Platform outbound IPs or "Allow Azure services".

### 3. Build the screens

Rename `Screen1` to `BrowseScreen`, add `MatterDetailScreen` and
`ValidationScreen` (**New screen > Blank**), then follow the three `.fx.md` files
in order. They are written so you can add each control, then paste each property
formula from the code blocks.

### 4. Delegation settings

- **Settings > General > Data row limit** — leave at 500 or raise to the max
  **2000**. This limit only applies to *non-delegable* portions of queries; the
  screens are written to keep the hot paths delegable (notes in each file).
- Watch for blue-underline delegation warnings in the formula bar as you paste;
  the `.fx.md` files call out the one intentional non-delegable spot (service-type
  filter) and its mitigations.

### 5. Patch semantics (ValidationScreen)

`Patch('con.document', <record>, {...})` issues an UPDATE keyed on the table's
primary key (`entry_id`) — the SQL connector requires a primary key for writes,
which `con.document` has. The formulas stamp `validated_by` with `User().Email`
and `validated_date` with UTC now (see the file for the timezone note: the DB
convention is `SYSUTCDATETIME()`).

### 6. Publish & share

1. **File > Save**, then **Publish**.
2. **Share**: add the validation team as users. Sharing does not grant SQL access —
   step 2.7 above and the license in the Licensing section are both still required
   per user.
3. Optional: add the app to Teams (Apps > upload from Power Apps) so validation
   happens where the team already works.
