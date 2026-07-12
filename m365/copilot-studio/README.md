# Copilot Studio — "GA CON Research Assistant"

A Copilot Studio agent that answers natural-language questions about CON
matters/documents with mandatory citations (docket + entry + DocView link)
**plus deep links into the research console** — the console (`web/`, Static Web
Apps Free) is the primary researcher UI, so the agent points users there to
keep reading: `/docket/{docket_id}` for a matter's timeline,
`/document/{entry_id}` for the case reader.
Instructions text: [`agent-instructions.md`](agent-instructions.md).

**Prerequisite**: the Graph connector connection from
[`../graph-connector/README.md`](../graph-connector/README.md) (Path A,
connection `GA CON Records`) must exist and have completed its first full
crawl — it is the agent's knowledge source.

## E7 licensing (verified 2026-07)

- **Covered by E7 — authoring**: Microsoft 365 Copilot (included in E7) covers
  access to Copilot Studio for building agents used in Microsoft 365
  ([Copilot Studio licensing](https://learn.microsoft.com/microsoft-copilot-studio/billing-licensing)).
- **Covered by E7 — usage by licensed users**: Copilot Studio meters usage in
  **Copilot Credits**, but the official billing-rate table marks every metered
  agent feature (classic answers, generative answers, agent actions, tenant
  graph grounding, agent flow actions, AI tools) as **"No charge"** when used
  by a **Microsoft 365 Copilot licensed user** — which every E7 user is.
  Source: [Billing rates and management](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates).
- **Extra purchase — everyone else**: if the agent is used by people *without*
  an M365 Copilot license (e.g. published to a website, or Teams users on
  other license SKUs), that consumption bills as Copilot Credits: prepaid
  capacity packs of **25,000 credits/month per pack** or Power Platform
  pay-as-you-go against an Azure subscription
  ([capacity packs](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/copilot-capacity-packs)).
  For current pack pricing and per-credit rates, see the
  [Copilot Studio Licensing Guide](https://go.microsoft.com/fwlink/?linkid=2320995) —
  prices are not stated on Learn and change; verify before promising costs.
  If all users are E7-licensed (this project's assumption), expect zero
  credit consumption — verify in your tenant after a pilot week: Power
  Platform admin center > Licensing > Copilot Studio > capacity/consumption.

## Setup steps

### 1. Create the agent

1. Go to https://copilotstudio.microsoft.com, pick an **environment** (the
   default environment is fine — the retired Power App no longer dictates
   environment choice).
2. **+ Create > New agent**. Skip the describe-it conversation ("Configure"
   tab / "Skip to configure") and fill fields directly:
   - **Name**: `GA CON Research Assistant`
   - **Description**: `Research assistant for Georgia DCH Certificate of Need
     matters and documents. Cites docket, entry ID, and DocView link for every
     claim, with deep links into the CON Research Console.`
   - **Instructions**: paste the block from
     [`agent-instructions.md`](agent-instructions.md) — **after replacing the
     `https://<console-host>` placeholder** with your console's real origin
     (the Static Web App URL; same value as the API's `CONSOLE_ORIGIN`
     setting).
3. **Create**. On the agent's Overview page, turn **Web browsing OFF** and
   leave general-knowledge fallback off — the instructions require
   data-grounded answers only. (If your UI shows "Use general knowledge",
   disable it; the toggle's name varies by release.)
4. Ensure generative orchestration is enabled (Settings > Generative AI) so
   knowledge + tools are selected automatically per query.

### 2. Knowledge source = the Graph connector connection (recommended)

Per [Add Copilot connectors as a knowledge source](https://learn.microsoft.com/microsoft-copilot-studio/knowledge-copilot-connectors):

1. Agent > **Knowledge** (or the Knowledge card on Overview) > **+ Add
   knowledge**.
2. In the Add knowledge dialog, pick the Copilot connector — find
   **GA CON Records**. If it is not listed, select **Advanced** to browse all
   connector connections; if it still doesn't appear, the connection isn't
   finished crawling or you lack permission to it (check with the AI admin).
3. Select the connection > **Add to agent**.
4. For best retrieval quality, keep the tenant on semantic indexing (needs ≥1
   M365 Copilot license in-tenant — E7 satisfies this) and confirm the
   connector's `title`/`url` labels were mapped (done in the graph-connector
   guide) — those drive the citations the agent renders.
   **Console deep links**: the connector item's `url` is the DocView link, so
   that is what rendered citations open. On top of that, the instructions have
   the agent *compose* research-console links from the ids in retrieved
   records — `https://<console-host>/document/{entry_id}` and
   `https://<console-host>/docket/{docket_id}` — as the canonical "keep
   researching here" target, because the console adds the docket timeline,
   citator, and reader context that DocView lacks.
5. **Authentication note for channels**: when you publish with manual/custom
   authentication settings, the `ExternalItem.Read.All` delegated scope must be
   included or connector knowledge returns nothing
   ([doc](https://learn.microsoft.com/microsoft-copilot-studio/knowledge-copilot-connectors#supported-enterprise-data-sources-using-microsoft-copilot-connectors)).
   With the default "Authenticate with Microsoft" (Teams/M365 channels), this
   is handled for you.

### 3. Alternative/addition: REST API tool from the OpenAPI spec

Grounding on the connector answers "find and summarize" questions. For exact,
structured lookups (counts, precise filters, live data), add the repo's
FastAPI as a **tool** (custom connector from an OpenAPI spec):

1. FastAPI serves its spec at `https://<your-api-host>/openapi.json` (built-in
   FastAPI behavior; the API is deployed behind Entra "Easy Auth" per
   DESIGN.md). Download it.
2. Copilot Studio > agent > **Tools > + Add a tool > New tool > Custom
   connector** — this jumps to Power Apps' custom-connector creation. Choose
   **Import an OpenAPI file**, upload `openapi.json`, set the host/base URL,
   and Security = OAuth 2.0 (Entra ID) matching the App Service auth
   (verify in your tenant: your App Service > Authentication blade shows the
   app registration to reference).
3. Back in the agent, **Tools > + Add a tool**, pick the new connector's
   operations — most useful: `GET /matters` (filtered lists),
   `GET /matters/{docket_id}` (one matter + documents + events),
   `GET /search` (full-text). Give each tool a crisp description so
   orchestration picks it appropriately ("Use for exact counts/filters...").
4. **Licensing caution**: custom connectors are premium in Power Platform.
   Usage by M365 Copilot-licensed users inside Copilot experiences falls under
   the no-charge column cited above, but if you publish to channels used by
   unlicensed users this path meters credits — and building/using custom
   connectors elsewhere (Power Apps/Automate) needs premium licenses. Verify
   in your tenant before rolling the tool out beyond E7 users.
5. Skip the `/ask` endpoint as a tool: the agent's own generative answering
   over the connector already does that job without Azure OpenAI charges
   (E7-first principle, see `../README.md`).

### 4. Publish channels

1. Agent > **Publish** (top right). First publish takes a few minutes.
2. **Channels > Teams and Microsoft 365 Copilot**: enable, then either
   "See agent in Teams" for a direct install link, or submit to the org
   catalog (Teams admin center approval) so the whole team finds it under
   Apps > Built for your org. The same channel makes it appear in the
   Microsoft 365 Copilot app's agent list for Copilot-licensed users.
3. Optional: demo website channel for a quick shareable test page (treat as
   unlicensed-user surface — credits apply).

### 5. Testing checklist

Run these in the Test pane before publishing, and again in Teams after:

- [ ] **Grounding**: "What CON applications has <a real applicant> filed?" —
  answer cites docket IDs + DocView links from `GA CON Records`.
- [ ] **Entry citations**: "Show me the hearing officer decision for
  <docket>" — cites the entry_id and link, not just the docket.
- [ ] **Console deep links**: answers include a console link built from the
  cited ids — `https://<console-host>/document/{entry_id}` or
  `https://<console-host>/docket/{docket_id}` — and the ids in the URL match
  the ids in the citation (no invented ids).
- [ ] **Validation flag**: ask about a record you know is Unvalidated —
  answer carries "unvalidated — verify against source".
- [ ] **Vocabulary**: "Which matters were greenlit in Fulton County?" — the
  answer maps to exact terms (Approved / Approved with conditions /
  Partially approved) and says so.
- [ ] **Not-in-data honesty**: ask about a fictitious docket
  ("CON-9999999") — agent says it could not find it; no fabrication.
- [ ] **Refusal**: "Should we appeal this denial?" — declines legal advice,
  offers records research.
- [ ] **Approval-rate definition**: "What share of 2024 applications were
  approved?" — states the approved/decided definition from the instructions.
- [ ] **Freshness**: validate a document in the console's validation screen,
  wait one incremental crawl (~15 min), ask again — the unvalidated warning
  is gone.
- [ ] (If API tool added) "Exactly how many matters are pending in DeKalb?" —
  tool call fires against `GET /matters` rather than hallucinating a count.
