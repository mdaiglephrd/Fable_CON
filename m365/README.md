# m365/ — Microsoft 365 integration layer

This directory documents how to surface the GA DCH CON research database (Azure SQL,
schema `con` — see `DESIGN.md` at the repo root) inside a Microsoft 365 E7 tenant.
Nothing in this directory runs from the repo: every artifact is **paste-in ready** and
is implemented by hand in your tenant following the step-numbered guides.

## Which artifact serves which need

| User need | M365 artifact | Folder |
|---|---|---|
| Dashboards: filing trends, outcomes by county/service type, completeness audit | **Power BI** report on Azure SQL (Import mode, scheduled refresh) | [`powerbi/`](powerbi/) |
| Data-entry / validation UI: browse matters, open DocView, mark documents Validated/Rejected | **Power Apps** canvas app over the SQL tables | [`powerapp/`](powerapp/) |
| Org-wide search + Copilot grounding: find CON matters/documents from Microsoft Search, Copilot Chat, Office apps | **Microsoft 365 Copilot connector** (Graph connector) indexing a flattened SQL view | [`graph-connector/`](graph-connector/) |
| Conversational research agent: "what happened with the Fulton County NICU application?" with citations | **Copilot Studio** agent grounded on the Graph connector | [`copilot-studio/`](copilot-studio/) |
| Governance: labels, retention, DLP, audit, AI-agent oversight | **Microsoft Purview** (+ Defender notes) | [`purview/`](purview/) |

## Recommended build order

1. **`powerbi/`** — fastest value; needs nothing but read access to the database and
   the Power BI Pro license already in E7.
2. **`graph-connector/`** — creates the `con.search_view` view and the Microsoft-built
   Azure SQL connector connection. This is the foundation for both Microsoft Search
   and every Copilot experience.
3. **`copilot-studio/`** — the "GA CON Research Assistant" agent, grounded on the
   connection from step 2. Publish to Teams and Microsoft 365 Copilot.
4. **`powerapp/`** — the validation canvas app. Built last because it is the one
   artifact with a real licensing dependency: the SQL Server connector is a
   **premium** Power Platform connector and is *not* covered by the Power Apps rights
   seeded in Microsoft 365 (details and citations in `powerapp/README.md`).
5. **`purview/`** — governance is not a "step" so much as a track you run alongside
   2–4; start it once the Graph connector and the Copilot agent exist, because those
   are the things Purview's AI governance features watch.

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
| Power Apps with *standard* connectors | **Covered** (M365-seeded plan) |
| Power Apps with the **SQL Server connector** (premium) | **Extra purchase** — Power Apps Premium/per-app/pay-as-you-go; see `powerapp/README.md` |
| Copilot connectors (synced) incl. indexing quota, Microsoft Search | **Covered** — "Indexing of synced connector data incurs no extra cost for tenants with Microsoft 365 licenses" ([prerequisites](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/prerequisites)) |
| Copilot grounding on connector data, federated connectors | **Covered** (requires the M365 Copilot license E7 includes) |
| Copilot Studio agent usage **by M365 Copilot-licensed users** | **Covered** — billed features show "No charge" for Copilot-licensed users ([billing rates](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates)) |
| Copilot Studio usage by unlicensed users / external channels | **Extra purchase** (Copilot Credits: prepaid packs or pay-as-you-go) |
| Purview: sensitivity labels, auto-labeling, DLP, records mgmt, Audit (Premium), Communication Compliance, DSPM for AI, agent governance | **Covered** (E5 Purview baseline + E7 agentic additions) |
| Purview Data Map / Unified Catalog **scanning of Azure SQL** | **Extra purchase** — Azure consumption billing, not an M365 license feature |
| Azure itself: Azure SQL Database, Azure Functions, Azure AI Search, Azure OpenAI | **Extra purchase** — Azure consumption is never part of E7 |

Where a claim below could not be verified from documentation, the guides say
"verify in your tenant" and tell you where to look, instead of guessing.
