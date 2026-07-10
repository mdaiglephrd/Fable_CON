# docs/ — implementation and operations guides

Connective tissue for the repo: these four guides give you the **order of
operations** across the modules and link into each module's README for depth.

Recommended reading order: **01 → 02 → 03 → 04**.

| Guide | One line |
|---|---|
| [01-azure-deployment.md](01-azure-deployment.md) | End-to-end Azure buildout: prerequisites, resource group, filling in `infra/main.bicepparam` (every parameter explained), the deploy command, the exact post-deploy sequence (SQL users for managed identities → Key Vault secrets → migrations → Functions deploy → API zip deploy → `search_sync` → Easy Auth), and smoke tests for every piece. |
| [02-configuration.md](02-configuration.md) | Complete settings reference: every environment variable and who reads it, local `.env` vs App Settings vs Key Vault references (`@Microsoft.KeyVault(SecretUri=...)`), the `SWEEP_CRON` NCRONTAB format, connection-auth options, and the numbered decision table (`deploySearch`? `deployOpenAI`? `FULLTEXT_ENABLED`? semantic free vs standard?) with recommendations. |
| [03-ingestion-runbook.md](03-ingestion-runbook.md) | Operating the pipelines: the three input formats (tag export CSV/JSON, `.jsonl.gz` index snapshots, weekly report PDF), exact CLI commands with real flags, how the blob-triggered flow and the `con.processed_blob` ledger work, the re-validation loop, monitoring queries, and a symptom → cause → fix troubleshooting table. |
| [04-m365-walkthrough.md](04-m365-walkthrough.md) | The Microsoft 365 E7 narrative: how the Azure side connects to the tenant, the build order across `m365/*` (Power BI → Graph connector → Copilot Studio → Power App → Purview), what E7 covers vs what's metered, tenant admin prerequisites, and the full-system acceptance checklist. |

## Start here if you only want…

- **…to stand up Azure**: [01](01-azure-deployment.md), with
  [02](02-configuration.md) open beside it for the decision table.
- **…to know what an env var does / where a setting goes**:
  [02-configuration.md](02-configuration.md).
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
  built against.
