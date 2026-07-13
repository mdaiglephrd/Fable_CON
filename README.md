# Georgia DCH CON Research Database

A research database for Georgia Department of Community Health (DCH) **Certificate of
Need (CON)** records — applications, decisions, appeals, and court rulings for regulated
healthcare projects in Georgia. Researchers use it to search records, relate documents
within a matter, and analyze outcomes. The primary researcher UI is the
**CON Research Console** — a React SPA in `web/` (Azure Static Web Apps Free, Entra
sign-in) over the FastAPI research endpoints: case reader, citator, docket timelines,
topics & key numbers, statutes, deadline calculator, stats, and the validation
workflow (build guide: `docs/06-research-console-buildout.md`).

## Data model

Two levels, related by docket:

- **Matter** — one per CON docket (`con.matter`, keyed by canonical `docket_id`), with
  applicant, facility, service type(s), matter/action type, county, outcome, phases, and
  completeness metadata. Docket ids are normalized from all the forms they appear in
  (`CON#######`, `CON-#######`, `DET…`, `LNR-…`, legacy `GA-#######`, county ids like
  `FULTON-213`) by `common/docket.py`; every observed variant is kept in
  `con.matter_docket_variant`.
- **Document** — one per repository Entry ID (`con.document`), with doc type, phase,
  decision level, outcome, parties, OCR and validation status, and a DocView URL back to
  the source repository.

Around those sit a **change log** (repository index diffs over time), a **watchlist**,
and **weekly-report events** (docket-keyed lifecycle events parsed from DCH's weekly
CON Tracking Report PDF). Controlled vocabularies (26 service types, matter/action/doc
types, phases, outcomes, decision levels, the 159 Georgia counties) live in seeded
vocab tables and `common/vocab.py`.

## Repository map

| Path | What it is |
|---|---|
| `schema/` | Azure SQL DDL migrations + `migrate.py` runner (vocab seeds, core tables, indexes, full-text; research layer + seeds in `0006`–`0009`) |
| `common/` | Shared code: docket normalization, vocabularies, DB connection helper, docket-family classifier, deadline rules, proceeding engine |
| `ingest/load_tags.py` | Idempotent, resumable loader for metadata-tag exports (CSV/JSON) → Matters + Documents (incl. the research-layer columns) |
| `ingest/load_document_text.py` | Loader for the document-text JSONL (Document Intelligence output) → `con.document_text` + `con.opinion_paragraph` |
| `ingest/index_diff.py` | Diffs two repository index snapshots (gzipped JSONL); writes the change log; flags re-validation |
| `ingest/weekly_report_parser.py` | Parses the weekly CON Tracking Report PDF into lifecycle events |
| `ingest/tag_*.py` | Bulk SSD-corpus ETL (Phase 1): enumerate → OCR/native-text extract → crosswalk to Laserfiche Entry ID → idempotent load into `con.matter`/`con.document`/`con.document_text` (`docs/07`) |
| `ingest/load_axis_tags.py` | Loader for Harvey's Georgia CON Tagging Taxonomy (Axis 1–4) exports → `con.document_axis1`–`4` (Phase 2, `docs/08`) |
| `functions/` | Azure Functions app: blob-triggered snapshot diff + report ingestion, daily catch-up sweep |
| `api/` | FastAPI query/search API: filter on any field, full-text search, docket rollups, Azure AI Search semantic/vector search, `/ask` Q&A with citations |
| `api/routers/` | Research-layer endpoints for the console: cases (reader), citator, proceedings, topics, statutes, history, stats, deadlines, projects, alerts, wiki |
| `web/` | The CON Research Console (React SPA, Static Web Apps Free); `web/design-reference/` holds the design handoff it is built from |
| `infra/` | Bicep for every Azure resource (SQL, Storage, Functions, App Service, Static Web App, Document Intelligence, AI Search, optional Azure OpenAI, Key Vault, monitoring) |
| `m365/` | Microsoft 365 E7 integration artifacts: Graph connector / Microsoft Search, Copilot Studio agent, Power BI, Purview governance (the Power App is retired — see `m365/powerapp/`) |
| `docs/` | Implementation and operations guides 01–06, incl. the metadata-extraction spec (`05`) and the free-tier console buildout (`06`); the tag ETL runbook (`07`) and Harvey tagging guide (`08`) |
| `tests/` | Unit tests (no live Azure needed) + synthetic fixtures |
| `DESIGN.md` | Internal contracts: schema, module interfaces, env var names (research layer: "RESEARCH LAYER (v2)") |
| `LESSONS.md` | Running log of lessons learned |

## Quickstart (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                        # everything runs against fakes; no Azure needed

cp .env.example .env             # fill in your values
python -m schema.migrate         # apply DDL (0001–0009: inventory + research layer)
python -m ingest.load_tags export.csv --rejects rejects.csv
python -m ingest.load_document_text extracted.jsonl --apply
python -m ingest.index_diff old.jsonl.gz new.jsonl.gz --apply
python -m ingest.weekly_report_parser report.pdf --apply
uvicorn api.main:app --reload    # query/search/research API on :8000

cd web && npm ci && npm run dev  # research console (Vite dev server)
```

## Deploying

1. **Azure**: `infra/README.md` — deploy the Bicep, run post-deploy steps 1–9 (SQL users
   for managed identities, Key Vault secrets, migrations, code deploy, console deploy,
   Document Intelligence, SQL free offer). The free-tier-first, end-to-end walkthrough
   is `docs/06-research-console-buildout.md`.
2. **Ingestion**: drop tag exports / index snapshots / weekly report PDFs into the
   Storage containers; the Functions app ingests snapshots and reports automatically
   (tag exports and document-text JSONL are loaded by CLI — see
   `docs/03-ingestion-runbook.md`).
3. **Microsoft 365**: `docs/04-m365-walkthrough.md` + `m365/*/README.md` —
   Graph connector into Microsoft Search/Copilot, Copilot Studio agent, Power BI
   report, Purview governance. Everything is tailored to what an E7 subscription
   already includes; the Power App is retired in favor of the console.

## Design principles

- **No secrets in code** — config via environment variables / Key Vault references.
- **Idempotent ingestion** — every loader converges on rerun; blob processing is
  tracked in `con.processed_blob` so triggers and the catch-up sweep never double-apply.
- **Validation is data, not code** — documents carry
  `Unvalidated | Validated | Corrected | Rejected`; changed documents get flagged back
  to Unvalidated by the index diff, and every API/Copilot surface flags unvalidated data.
- **E7-first** — where Microsoft 365 E7 already covers a capability (Microsoft Search,
  Copilot grounding via Graph connector), the guides steer there instead of duplicating
  it with metered Azure services.
