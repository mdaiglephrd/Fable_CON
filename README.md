# Georgia DCH CON Research Database

A research database for Georgia Department of Community Health (DCH) **Certificate of
Need (CON)** records — applications, decisions, appeals, and court rulings for regulated
healthcare projects in Georgia. Researchers use it to search records, relate documents
within a matter, and analyze outcomes.

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
| `schema/` | Azure SQL DDL migrations + `migrate.py` runner (vocab seeds, core tables, indexes, full-text) |
| `common/` | Shared code: docket normalization, vocabularies, DB connection helper |
| `ingest/load_tags.py` | Idempotent, resumable loader for metadata-tag exports (CSV/JSON) → Matters + Documents |
| `ingest/index_diff.py` | Diffs two repository index snapshots (gzipped JSONL); writes the change log; flags re-validation |
| `ingest/weekly_report_parser.py` | Parses the weekly CON Tracking Report PDF into lifecycle events |
| `functions/` | Azure Functions app: blob-triggered snapshot diff + report ingestion, daily catch-up sweep |
| `api/` | FastAPI query/search API: filter on any field, full-text search, docket rollups, Azure AI Search semantic/vector search, `/ask` Q&A with citations |
| `infra/` | Bicep for every Azure resource (SQL, Storage, Functions, App Service, AI Search, optional Azure OpenAI, Key Vault, monitoring) |
| `m365/` | Microsoft 365 E7 integration artifacts: Power BI, Power Apps, Graph connector / Microsoft Search, Copilot Studio agent, Purview governance |
| `docs/` | Implementation and operations guides, end-to-end walkthrough |
| `tests/` | Unit tests (no live Azure needed) + synthetic fixtures |
| `DESIGN.md` | Internal contracts: schema, module interfaces, env var names |
| `LESSONS.md` | Running log of lessons learned |

## Quickstart (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                        # everything runs against fakes; no Azure needed

cp .env.example .env             # fill in your values
python -m schema.migrate         # apply DDL to your Azure SQL database
python -m ingest.load_tags export.csv --rejects rejects.csv
python -m ingest.index_diff old.jsonl.gz new.jsonl.gz --apply
python -m ingest.weekly_report_parser report.pdf --apply
uvicorn api.main:app --reload    # query/search API on :8000
```

## Deploying

1. **Azure**: `infra/README.md` — deploy the Bicep, run post-deploy steps (SQL users for
   managed identities, Key Vault secrets, migrations, code deploy).
2. **Ingestion**: drop tag exports / index snapshots / weekly report PDFs into the
   Storage containers; the Functions app ingests them (see `docs/03-ingestion-runbook.md`).
3. **Microsoft 365**: `docs/04-m365-integration-walkthrough.md` + `m365/*/README.md` —
   Power BI report, Power App, Graph connector into Microsoft Search/Copilot, Copilot
   Studio agent, Purview governance. Everything is tailored to what an E7 subscription
   already includes.

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
