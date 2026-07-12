# m365/ — Microsoft 365 integration layer

This directory documents how to surface the GA DCH CON research database (Azure SQL,
schema `con` — see `DESIGN.md` at the repo root) inside a Microsoft 365 E7 tenant.
Nothing in this directory runs from the repo: every artifact is **paste-in ready** and
is implemented by hand in your tenant following the step-numbered guides.

## Where the M365 layer sits now

The **primary researcher UI is the CON Research Console** — the React SPA in
`web/`, hosted on **Azure Static Web Apps (Free)** with Entra ID sign-in, backed by
the repo's FastAPI (`docs/06-research-console-buildout.md`, Phases 4–5). The console
owns browsing, search, the case reader, citator, docket timelines, stats, and the
validation workflow. The M365 layer wraps around it with the things a web app
cannot provide from inside the tenant:

- **Natural-language ask-anything** across Microsoft Search, Copilot Chat, and
  Teams (Graph connector + the Copilot Studio agent — the E7-included alternative
  to metered Azure OpenAI).
- **Executive dashboards** (Power BI).
- **Governance** over both the M365 surfaces *and* the console + API as
  Entra-authenticated app surfaces (Purview + Entra Conditional Access).

The Power Apps validation app is **retired**: the console replaces its three
screens outright and removes the per-user premium-connector license that
Power Apps + Azure SQL required. `powerapp/` stays in the tree as a clearly marked
historical reference — see the RETIRED banner in
[`powerapp/README.md`](powerapp/README.md).

## Which artifact serves which need

| User need | Artifact | Folder |
|---|---|---|
| Browse / data-entry / validation UI: search matters, read documents, work the `Unvalidated` queue | **CON Research Console** (`web/` SPA + FastAPI, Static Web Apps Free — not an M365 artifact) — **replaces Power Apps** | [`../web/`](../web/), built per [`docs/06`](../docs/06-research-console-buildout.md); the retired app is kept for reference in [`powerapp/`](powerapp/) |
| Org-wide search + Copilot grounding: find CON matters/documents from Microsoft Search, Copilot Chat, Office apps | **Microsoft 365 Copilot connector** (Graph connector) indexing a flattened SQL view | [`graph-connector/`](graph-connector/) |
| Conversational research agent: "what happened with the Fulton County NICU application?" with citations + console deep links | **Copilot Studio** agent grounded on the Graph connector | [`copilot-studio/`](copilot-studio/) |
| Dashboards: filing trends, outcomes by county/service type, completeness audit | **Power BI** report on Azure SQL (Import mode, scheduled refresh) | [`powerbi/`](powerbi/) |
| Governance: labels, retention, DLP, audit, AI-agent oversight — now also covering the console + API app surfaces | **Microsoft Purview** (+ Entra Conditional Access + Defender notes) | [`purview/`](purview/) |

## Recommended build order

Prerequisite: the console and API are Azure-side deliverables built first
(`docs/06-research-console-buildout.md` Phases 1–4). This M365 sequence is that
guide's **Phase 5**:

1. **`graph-connector/`** — creates the `con.search_view` view and the
   Microsoft-built Azure SQL connector connection. This is the foundation for both
   Microsoft Search and every Copilot experience — the natural-language path E7
   already pays for.
2. **`copilot-studio/`** — the "GA CON Research Assistant" agent, grounded on the
   connection from step 1 and deep-linking its answers into the console. Publish
   to Teams and Microsoft 365 Copilot.
3. **`powerbi/`** — executive dashboards; needs nothing but read access to the
   database and the Power BI Pro license already in E7.
4. **`purview/`** — governance is not a "step" so much as a track you run alongside
   1–3; start it once the Graph connector and the Copilot agent exist, because
   those are the things Purview's AI governance features watch — and register the
   console + API as governed app surfaces while you are there
   (`purview/governance.md` §8).

The Power Apps validation app has been **removed from the build order** — it is
retired in favor of the console (see `powerapp/README.md`), which also deletes the
one per-user licensing line this order used to end on.

## The E7-first principle

Microsoft 365 E7 already pays for an end-user natural-language search stack:
Copilot connectors index the database into Microsoft Graph at no additional indexing
cost, and Microsoft 365 Copilot (included in E7) grounds its answers on that index —
so an analyst typing "CON applications for freestanding EDs in Gwinnett" into
Copilot Chat or Microsoft Search costs nothing beyond the licenses you already own.
The repo's `POST /ask` endpoint reaches the same data through Azure AI Search plus
Azure OpenAI, both of which are **Azure consumption services metered outside E7**
(per-query, per-token, and per-hour index costs). Therefore: prefer the Graph
connector + Microsoft Search + M365 Copilot path for people asking questions in
natural language, and reserve `/ask` (and `/search/semantic`) for programmatic and
embedded use — scripted pipelines, the FastAPI surface, or apps that cannot present a
Microsoft 365 identity.

## E7 coverage at a glance (verified against Microsoft Learn, 2026-07)

Microsoft 365 E7 ("Frontier Suite", generally available May 1, 2026) is a strict
superset of E5: **E5 + Microsoft 365 Copilot + full Microsoft Entra Suite + Agent 365**
([license comparison](https://learn.microsoft.com/microsoft-365/copilot/microsoft-365-copilot-license-feature-overview)).

| Capability | Covered by E7? |
|---|---|
| Power BI Pro (publish, share, 8 scheduled refreshes/day) | **Covered** (via the E5 baseline) |
| Power BI Premium / Fabric capacity (48 refreshes/day, >1 GB models) | **Extra purchase** |
| Power Apps with *standard* connectors | **Covered** (M365-seeded plan) — no longer used by this project |
| Copilot connectors (synced) incl. indexing quota, Microsoft Search | **Covered** — "Indexing of synced connector data incurs no extra cost for tenants with Microsoft 365 licenses" ([prerequisites](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/prerequisites)) |
| Copilot grounding on connector data, federated connectors | **Covered** (requires the M365 Copilot license E7 includes) |
| Copilot Studio agent usage **by M365 Copilot-licensed users** | **Covered** — billed features show "No charge" for Copilot-licensed users ([billing rates](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates)) |
| Copilot Studio usage by unlicensed users / external channels | **Extra purchase** (Copilot Credits: prepaid packs or pay-as-you-go) |
| Entra ID P2 + Entra Suite (Conditional Access for the console/API apps) | **Covered** (P2 in the E5 baseline; E7 adds the full Entra Suite) |
| Purview: sensitivity labels, auto-labeling, DLP, records mgmt, Audit (Premium), Communication Compliance, DSPM for AI, agent governance | **Covered** (E5 Purview baseline + E7 agentic additions) |
| Purview Data Map / Unified Catalog **scanning of Azure SQL** | **Extra purchase** — Azure consumption billing, not an M365 license feature |
| Azure itself: Azure SQL Database, App Service (API), Static Web Apps (console — Free tier available), Azure Functions, Azure AI Search, Azure OpenAI | **Extra purchase** — Azure consumption is never part of E7 (the console/API free-tier posture keeps this at ~$0; see `docs/06`) |

**Removed cost line — Power Apps premium licensing.** Earlier revisions of this
table carried a per-user **extra purchase** row: the Power Apps validation app used
the **SQL Server connector**, a premium Power Platform connector *not* covered by
the Power Apps rights seeded into Microsoft 365/E7, so every validator needed a
Power Apps Premium / per-app / pay-as-you-go license. Retiring that app in favor of
the research console (Static Web Apps Free + the existing API) removes that
licensing requirement entirely — a real cost saving, not a shuffle. The verified
citations for the premium classification are preserved in
[`powerapp/README.md`](powerapp/README.md).

Where a claim below could not be verified from documentation, the guides say
"verify in your tenant" and tell you where to look, instead of guessing.
