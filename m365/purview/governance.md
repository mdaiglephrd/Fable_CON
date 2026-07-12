# Purview governance for the CON research database

Governance recommendations for this system using the Microsoft Purview
capabilities in E7, plus the adjacent Defender/Azure pieces. Context that
shapes everything below: **the core data is Georgia public-record material**
(DCH CON filings and decisions). The sensitive surface is small and specific:
analyst work product (`con.watchlist` reasons, validation attributions
`validated_by`/`validated_date`), and the AI surfaces built on top (Copilot
agent, connector).

All portal steps below start at the **Microsoft Purview portal**
(https://purview.microsoft.com). Purview's navigation gets renamed
periodically; if a path below doesn't match, use the portal's search box with
the solution name — the solution names are stable.

E7 baseline for this whole file: E7 includes E5 Purview (auto-labeling, DLP
across workloads, Records Management, Audit Premium, Insider Risk,
Communication Compliance, DSPM for AI) **plus** the E7 agentic additions
(label-aware agent interactions, DLP extended to agent interactions, agentic
audit trails, agent content-safety controls). Source:
[E3/E5/E7 license feature comparison](https://learn.microsoft.com/microsoft-365/copilot/microsoft-365-copilot-license-feature-overview).

---

## 1. Sensitivity labels

**What to configure** — a small taxonomy that separates public record from
work product:

| Label | Applies to | Protection |
|---|---|---|
| `General \ Public Record - CON` | Exports of CON records: Power BI exports, Excel pulls, PDFs re-shared from DocView, connector-sourced content | No encryption, no content marking (it's public record); the label's value is *classification* — it tells DLP/analytics "this is the public dataset" and prevents over-restrictive defaults from blocking sharing |
| `Confidential \ CON Analyst Notes` | Watchlist rationales, validation notes, internal memos, draft analyses | Encryption optional but recommended (org-internal rights), header marking "Internal analyst work product" |

Keep it to these two; more granularity than people can choose correctly is
governance theater.

**Exact steps**

1. Purview portal > **Information protection > Sensitivity labels > + Create a
   label**.
2. Create parent `General` (or reuse your existing General) with sublabel
   `Public Record - CON`: scope = Files & other data assets + Emails; no
   encryption; no marking; description for users: "Georgia DCH CON
   public-record data exported from the CON research database."
3. Create `Confidential \ CON Analyst Notes`: same scopes; enable
   encryption (assign permissions: your analyst group, Co-Author); header
   marking.
4. **Publish** both via a label policy targeting the analyst group; set the
   *default label for documents* to none (don't force-label everything) but
   require justification to remove `CON Analyst Notes`.

**E7 coverage** — Covered. Custom labels are E3+; automatic application (next
section) and container labels are E5+, both inside E7. E7 additionally makes
labels flow into agent interactions ("label-aware agent interactions"), which
is exactly what you want if analyst notes ever end up in a grounding source.

---

## 2. Auto-labeling

**What to configure** — scope auto-labeling narrowly:

- Service-side auto-labeling policy applying `General \ Public Record - CON`
  to SharePoint/OneDrive/Exchange content that clearly originates from this
  system. Reliable detectors: the docket-ID shapes from `common/docket.py`
  (`CON-#######`, `DET-YYYY-###`, `LNR-YYYY-###`) and the DocView host name.
- Do **not** auto-apply `CON Analyst Notes` — intent can't be detected
  reliably; leave it manual with the policy default above.

**Exact steps**

1. Purview portal > **Information protection > Classifiers > Sensitive info
   types > + Create**: name `GA CON Docket ID`, primary element = regex
   `\b(?:CON|GA)[- ]?\d{7}\b|\b(?:DET|LNR)[- ]?\d{4}[- ]?\d{1,4}\b`,
   confidence medium; add the DocView hostname as supporting keyword.
   Test with real docket strings (the canonicalizer tolerates more separator
   variants than this regex; extend it if your exports keep raw forms).
2. **Information protection > Auto-labeling policies (Policies > Auto-labeling) >
   + Create**: label `Public Record - CON`; locations SharePoint + OneDrive +
   Exchange; condition = the custom sensitive info type; start in
   **simulation mode**, review a week of matches, then turn on.

**E7 coverage** — Covered (auto-labeling is an E5 capability, included in E7).
No extra purchase.

---

## 3. Data Loss Prevention (DLP)

**What to configure** — deliberately light. Public-record data should not be
DLP-blocked; that would just train users to fight the tooling. Two policies:

- **Analyst-notes policy**: content labeled `Confidential \ CON Analyst
  Notes` leaving the org (Exchange, Teams, SharePoint/OneDrive sharing to
  external) → policy tip + block with override + incident report. Watchlist
  reasons and validation attributions are the things that could embarrass
  (they reveal what you're monitoring and who signed off on what).
- **Copilot/agent guardrail**: extend DLP to AI interactions so
  `CON Analyst Notes`-labeled content can't be surfaced/pasted into agent
  conversations outside the analyst group. In current Purview this lives
  under DLP's Microsoft 365 Copilot location / DSPM-for-AI-created policies —
  E7's "DLP policies extend to agent interactions" is precisely this knob.
  Verify in your tenant: Purview > Data loss prevention > + Create policy —
  check the available locations list for Copilot/agent interactions.

Nothing else: no credit-card/SSN templates, no policies on the CON dataset
itself.

**Exact steps**

1. Purview portal > **Data loss prevention > Policies > + Create policy** >
   Custom.
2. Locations: Exchange, Teams chat/channel, SharePoint, OneDrive (+
   Copilot/agent interactions location if present — see above).
3. Condition: content contains sensitivity label `CON Analyst Notes` AND
   shared outside the organization.
4. Actions: show policy tip; block with allow-override-with-justification;
   send incident reports to the data owner. Start in test-with-tips mode.

**E7 coverage** — Covered (DLP across SPO/EXO/OD/Teams/endpoints is E5;
agent-interaction DLP is the E7 addition). Endpoint DLP needs onboarded
devices (Defender onboarding) — included licensing-wise in E5/E7, but requires
device enrollment work.

---

## 4. Records management (retention)

**What to configure** — retention labels per record class, applied to the M365
copies of this material (the SQL database itself is governed by backups/Azure,
not M365 retention):

| Record class | Suggested label | Retention (CONFIRM — see warning) |
|---|---|---|
| CON record exports (public-record copies) | `CON Public Record Copy` | Retain N years then delete — these are *copies*; the authoritative record is DCH's. A short retention (e.g. 3 years) keeps SharePoint from becoming a shadow archive |
| Analyst work product | `CON Analyst Work Product` | Retain per your organization's research-records schedule, then review before deletion |
| Weekly report PDFs (ingest inputs) | `CON Ingest Source` | Retain until superseded + a safety window; they're reproducible from DCH |

> **Warning — do not take retention periods from this file.** If your
> organization is (or serves) a Georgia agency, align with the **Georgia
> records retention schedules** administered under the Georgia Archives /
> University System of Georgia records management program: look up the
> applicable schedule for regulatory/health-planning records and adopt its
> periods. This file deliberately cites no statute or schedule numbers —
> confirm the current schedule with your records officer before configuring.
> If you are a private organization, your own counsel's retention policy
> governs; the DCH originals remain with DCH either way.

**Exact steps**

1. Purview portal > **Records management > File plan > + Create a label**:
   create the three labels; set retention period and end-of-retention action
   (delete vs. review). Mark `CON Analyst Work Product` as a **record** only
   if you truly need immutability — it locks editing behaviors.
2. Publish to the SharePoint sites / Teams where CON material lives.
3. Auto-apply (optional, E5+): auto-apply `CON Public Record Copy` to content
   matching the `GA CON Docket ID` sensitive info type in the export library.
4. Set a **disposition reviewer** for work product.

**E7 coverage** — Covered: retention policies are E3; auto-apply, Records
Management proper, and disposition review are E5; E7 adds agentic audit
trails on records lifecycle. No extra purchase for M365 content. (Retention
for the Azure SQL data itself = Azure backup/PITR configuration — Azure cost,
outside Purview.)

---

## 5. Data Map / Unified Catalog — register the Azure SQL DB

**What to configure** — register and scan the CON database so it's
discoverable/classified in your data estate: asset `con` schema with its
tables (`con.matter`, `con.document`, `con.weekly_report_event`,
`con.change_log`, `con.watchlist`, vocab tables), schema-level classifications
and glossary terms ("docket", "DocView URL"), lineage stubs to the Power
BI model.

**Exact steps**

1. Purview portal > **Data Map > Data sources > Register** > Azure SQL
   Database; select the subscription/server hosting your `SQL_DATABASE`.
2. Auth for scanning: managed identity of the Purview account; grant it
   `db_datareader` in the DB (`CREATE USER [purview-account-name] FROM
   EXTERNAL PROVIDER; ALTER ROLE db_datareader ADD MEMBER
   [purview-account-name];`) and allow it through the SQL firewall.
3. **New scan**: scope to the `con` schema; scan rule set: system default +
   a custom rule adding the `GA CON Docket ID` classifier from §2.
4. Schedule: **weekly** is plenty — the schema changes only via numbered
   migrations in `schema/migrations/`; also re-run after applying a new
   migration.
5. In **Unified Catalog**, curate: assign a data owner, attach glossary terms,
   and mark the dataset's classification as public-record.

**E7 coverage** — **Extra purchase.** This is the one Purview area NOT covered
by M365 licensing: Data Map scanning / Unified Catalog data-governance
features for Azure data sources are **Azure consumption-billed** (pay-as-you-go
against an Azure subscription). The E5/E7 Purview entitlements cover the
M365-side compliance solutions in the other sections, not Azure data-estate
scanning. Costs at this scale (one small DB, weekly scans) are small but real —
verify current meters on the
[Microsoft Purview pricing page](https://azure.microsoft.com/pricing/details/purview/)
before scheduling aggressive scans.

---

## 6. Audit

**What to configure** — three audit trails, stitched:

1. **Purview Audit** for M365-side actions: Power BI activities (report
   viewed, exported), Copilot & agent interactions ("Interacted with Copilot"
   events, and E7's agent-action logging). Confirm auditing is enabled
   (default on for new tenants). (Power Apps/Power Platform activity events
   only apply if you still run any Power Platform artifact — the validation
   Power App is retired; see `../powerapp/README.md`.)
2. **Azure SQL auditing** for the writes that matter most — validation
   actions flow **console → FastAPI → SQL** (an `UPDATE` on `con.document`),
   and Purview cannot see row-level SQL changes. Enable server-level auditing
   to a Log Analytics workspace; the `UPDATE` on `con.document` carrying
   `validation_status`/`validated_by`/`validated_date` is your
   who-validated-what trail (complementing the columns themselves). This is
   the **same audit SQL as before** the console replaced the Power App — the
   write shape didn't change, only the client. See §8 for the one caveat
   (the SQL principal is now the API's identity).
3. **Application-level**: the repo already records pipeline provenance
   (`con.change_log`, `con.processed_blob`) — surface it in the Power BI
   audit page rather than duplicating it in Purview.

**Exact steps**

1. Purview portal > **Audit** > confirm "Start recording user and admin
   activity" is already on; test with **Audit > New search** filtering
   Workload = PowerApps / Power BI, and (after the agent ships) activity
   "Interacted with Copilot" / agent interaction events.
2. Set retention: Audit Premium (E5/E7) allows long retention policies —
   create an audit retention policy (up to 10-year options exist at E5;
   1 year is a sensible default here).
3. Azure portal (not Purview) > your SQL server > **Auditing** > enable, sink
   = Log Analytics; optionally add a database-level audit spec narrowed to
   UPDATE on `con.document` and writes to `con.watchlist`. (Azure cost:
   Log Analytics ingestion/retention — small.)
4. Document the mapping in your runbook: "who validated entry X" = the
   `validated_by` column, corroborated by the SQL audit log, corroborated by
   the Entra sign-in logs for the console/API apps (§8).

**E7 coverage** — Purview Audit (incl. Premium's longer retention and richer
events, plus E7's agent traceability) is covered. Azure SQL auditing + Log
Analytics is **Azure consumption** (small, but not E7).

---

## 7. AI-agent governance (DSPM for AI, Communication Compliance, Defender)

**What to configure** — oversight of the two AI surfaces this repo creates
(the `GA CON Research Assistant` agent and connector-grounded M365 Copilot):

- **DSPM for AI** (Purview's AI hub): turn on the AI activity/analytics so
  prompts and responses involving the agent are visible, run its assessments,
  and adopt its recommended one-click policies (e.g. detect sensitive info in
  AI interactions). E5 lets you view prompt/response; E7 extends visibility
  into agent data exposure and protects data agents create/use.
- **Communication Compliance**: add the Copilot/agent interaction location to
  a policy so the agent's conversations are sampled for policy violations;
  E7 adds the agent content-safety controls ("detect, retain, and investigate
  unethical agent interactions"). For a public-records assistant the realistic
  risks are prompt-injection-driven off-mission behavior and users pushing for
  legal advice — both worth sampling, not blocking.
- **Agent inventory/lifecycle**: E7 includes **Agent 365** — register the
  Copilot Studio agent there for identity, Conditional Access, and lifecycle
  management (Microsoft 365 admin center > agent settings), so the agent has
  an owned identity and can be disabled centrally.
- **Defender**: Microsoft Defender XDR (E5/E7) already watches the M365 side.
  "Defender for AI" style *threat protection for AI services* on the Azure
  side (protecting your Azure OpenAI `/ask` endpoint against jailbreak/abuse
  signals) is **Microsoft Defender for Cloud — AI threat protection**, enabled
  per Azure subscription and **Azure consumption-billed**, not part of E7.
  Only relevant if you keep the `/ask` endpoint in service.

**Exact steps**

1. Purview portal > **DSPM for AI** (search "DSPM" if renamed) > complete the
   "Get started" checklist: enable Purview Audit (done in §6), install/enable
   the recommended policies, review the **Reports** blade after a week of
   agent pilot use. Scope to the analyst group first.
2. Purview portal > **Communication compliance > + Create policy**: start from
   the AI-interactions template if offered; reviewers = compliance owner;
   sample rate modest (10%).
3. Microsoft 365 admin center > **Settings > Agents** (Agent 365 /
   agent-management area; naming still settling — verify in your tenant):
   confirm the published agent appears in the inventory, assign an owner,
   and apply Conditional Access for agents if your Entra policies use it.
4. (Only if `/ask` stays in production) Azure portal > Defender for Cloud >
   Environment settings > your subscription > enable the AI workloads plan.
   Azure cost — weigh against how much `/ask` is actually used.

**E7 coverage** — DSPM for AI, Communication Compliance (incl. agent
content-safety), Purview agent governance, and Agent 365 are covered by E7.
Defender for Cloud AI threat protection is **extra purchase (Azure)**.

---

## 8. The research console + API as governed surfaces

The primary researcher UI is the **CON Research Console** (`web/`, Azure Static
Web Apps Free) backed by the FastAPI app (App Service with Entra "Easy Auth").
Both are Entra-authenticated applications in the same tenant, which puts them
squarely inside the identity-governance tooling E7 already includes. This
section is additive to §§1–7 — nothing above changes.

**What to configure**

- **Entra Conditional Access for the console + API apps.** Target the two app
  registrations that the Static Web App's Entra sign-in and the App Service
  Authentication blade use: require MFA for the analyst group, add a
  compliant-device condition if you manage devices, and add sign-in-risk
  conditions if you run risk-based policies. Conditional Access is an Entra ID
  P1/P2 capability — **covered**: E7's E5 baseline includes Entra ID P2, and
  E7 adds the full Microsoft Entra Suite on top (`../README.md` coverage
  table). Which app registrations exist and what they are named depends on how
  auth was wired — verify in your tenant (Entra admin center > App
  registrations) before targeting policies.
- **Audit trail for validation actions.** Validation writes no longer come
  from a Power Platform connector: they flow **console → FastAPI → SQL**. The
  Azure SQL auditing configured in §6 is unchanged and remains the row-level
  trail — the **same audit SQL as before** (the database-level audit spec
  narrowed to `UPDATE` on `con.document` and writes to `con.watchlist` still
  captures everything). One difference to record in your runbook: the SQL
  principal in the audit log is the API application's identity, not the end
  user — the human actor is the `validated_by` column the API stamps,
  corroborated by the Entra sign-in logs for the console/API applications.
- **DSPM for AI — the agent's console deep links.** The Copilot Studio agent
  now cites research-console deep links (`/docket/{docket_id}`,
  `/document/{entry_id}`) alongside DocView links
  (`../copilot-studio/agent-instructions.md`). The DSPM-for-AI
  prompt/response visibility you enabled in §7 therefore also covers the
  console-bound traffic the agent generates: its responses show which console
  records users are being steered into. When reviewing DSPM reports, treat
  console URLs as part of the agent's output surface, and keep the agent's
  link domains limited to DocView and the console origin (any other domain in
  an agent response is a red flag worth investigating — likely fabrication or
  prompt injection).

**E7 coverage** — Conditional Access (Entra ID P2 via the E5 baseline, plus
the E7 Entra Suite) and DSPM for AI are covered. The hosting itself is Azure:
Static Web Apps Free keeps the console at $0 and App Service is F1 ($0 pilot)
or B1 (paid) per `docs/06-research-console-buildout.md`; Azure SQL auditing +
Log Analytics remain Azure consumption exactly as in §6.

---

## Quick coverage recap

| Section | Covered by E7 | Extra purchase |
|---|---|---|
| 1–2 Labels + auto-labeling | ✔ | — |
| 3 DLP (incl. agent interactions) | ✔ | Endpoint DLP needs device onboarding effort (no extra license) |
| 4 Records management | ✔ (M365 content) | Azure SQL backup/retention = Azure |
| 5 Data Map / Unified Catalog | — | ✔ Azure consumption |
| 6 Audit | ✔ (Purview Audit) | Azure SQL auditing + Log Analytics = Azure |
| 7 AI governance | ✔ (DSPM, CommCompliance, Agent 365) | Defender for Cloud AI plan = Azure |
| 8 Console + API surfaces | ✔ (Conditional Access via Entra ID P2/Entra Suite; DSPM link coverage) | Console/API hosting + SQL auditing = Azure (free-tier posture ≈ $0, see docs/06) |
