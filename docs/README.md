# docs/ — implementation and operations guides

Connective tissue for the repo: these six guides give you the **order of
operations** across the modules and link into each module's README for depth.

Recommended reading order — **to build the platform**:
[06](06-research-console-buildout.md) → [01](01-azure-deployment.md) →
[02](02-configuration.md) → [03](03-ingestion-runbook.md) /
[05](05-metadata-extraction-spec.md) → [04](04-m365-walkthrough.md).
Guide 06 is the free-tier-first, account-to-running walkthrough that sequences
the rest; 03 and 05 are read side by side (05 says *what* to capture, 03 says
*how* to load it).

| Guide | One line |
|---|---|
| [01-azure-deployment.md](01-azure-deployment.md) | End-to-end Azure buildout: prerequisites, resource group, filling in `infra/main.bicepparam` (every parameter explained, incl. the research-layer params), the deploy command, the exact post-deploy sequence (SQL users for managed identities → Key Vault secrets → migrations 0001–0009 → Functions deploy → API zip deploy → `search_sync` → Easy Auth → console deploy), and smoke tests for every piece. |
| [02-configuration.md](02-configuration.md) | Complete settings reference: every environment variable and who reads it, local `.env` vs App Settings vs Key Vault references (`@Microsoft.KeyVault(SecretUri=...)`), the `SWEEP_CRON` NCRONTAB format, connection-auth options, the research-layer settings (`DOCUMENT_INTELLIGENCE_ENDPOINT`, `CONSOLE_ORIGIN`), and the numbered decision table (`deploySearch`? `deployOpenAI`? `appServicePlanSku`? `docIntelSku`? `FULLTEXT_ENABLED`?) with recommendations. |
| [03-ingestion-runbook.md](03-ingestion-runbook.md) | Operating the pipelines: the four input formats (tag export CSV/JSON, `.jsonl.gz` index snapshots, weekly report PDF, document-text JSONL), exact CLI commands with real flags, how the blob-triggered flow and the `con.processed_blob` ledger work, the re-validation loop and the editorial pass, monitoring queries, and a symptom → cause → fix troubleshooting table. |
| [04-m365-walkthrough.md](04-m365-walkthrough.md) | The Microsoft 365 E7 narrative: how the Azure side (and the research console) connect to the tenant, the build order across `m365/*` (Graph connector → Copilot Studio → Power BI → Purview; the Power App is retired), what E7 covers vs what's metered, tenant admin prerequisites, and the full-system acceptance checklist. |
| [05-metadata-extraction-spec.md](05-metadata-extraction-spec.md) | The extraction spec, by document type: what to capture from every CON record, which tag-export column / JSONL field / editorial screen it enters through, which table/column stores it, and which console view consumes it. Your ingestion contract. |
| [06-research-console-buildout.md](06-research-console-buildout.md) | Building the whole platform from a brand-new Azure account, free-tier-first: cost table up front, phase-by-phase (account → Bicep → data load → API + console → M365), and the "when you outgrow the free tiers" upgrade table. |

## Start here if you only want…

- **…to build the whole platform from zero (and know what it costs)**:
  [06-research-console-buildout.md](06-research-console-buildout.md) — it
  sequences everything else.
- **…to stand up Azure**: [01](01-azure-deployment.md), with
  [02](02-configuration.md) open beside it for the decision table.
- **…to know what an env var does / where a setting goes**:
  [02-configuration.md](02-configuration.md).
- **…to know what to extract from each document** (tag-export columns, the
  document-text JSONL, editorial fields):
  [05-metadata-extraction-spec.md](05-metadata-extraction-spec.md).
- **…to load data or debug a stuck blob**:
  [03-ingestion-runbook.md](03-ingestion-runbook.md) (troubleshooting table at
  the end).
- **…dashboards, Microsoft Search, or Copilot over the data**:
  [04-m365-walkthrough.md](04-m365-walkthrough.md), then the specific
  `m365/*/README.md`.
- **…to run everything locally first**: the Quickstart in the
  [repo-root README](../README.md), plus `functions/README.md` for the local
  Functions host.
- **…the internal contracts (schema, interfaces, env names)**:
  [`DESIGN.md`](../DESIGN.md) — the single source of truth the modules were
  built against; the research layer is specified in its "RESEARCH LAYER (v2)"
  section.
