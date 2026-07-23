# api/ — FastAPI service for the GA DCH CON database

HTTP layer over the `con` schema in Azure SQL: the v1 inventory endpoints, the
research-layer endpoints in `api/routers/*` (case reader, citator, proceedings,
topics, statutes, history, stats, deadlines, projects, alerts, wiki), plus
Azure AI Search / Azure OpenAI retrieval endpoints. Contracts live in the
repo-root `DESIGN.md` (research layer: its "RESEARCH LAYER (v2)" section).

The **primary consumer is the research console** (`web/` — the React SPA on
Static Web Apps; see `docs/06-research-console-buildout.md`).

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in SQL_* (and SEARCH_*/AZURE_OPENAI_* if used)
uvicorn api.main:app --reload
```

Interactive docs: <http://127.0.0.1:8000/docs>.

## Endpoints

| Method | Path | Description | Example |
|---|---|---|---|
| GET | `/health` | Liveness (no DB) | `curl localhost:8000/health` |
| GET | `/vocab/{name}` | Controlled vocab lists (no DB): `service_type`, `matter_type`, `action_type`, `doc_type`, `phase`, `outcome`, `decision_level`, `county`, `validation_status` | `curl localhost:8000/vocab/county` |
| GET | `/matters` | List/filter matters. Filters: `docket_id`, `applicant`, `facility`, `matter_type`, `action_type`, `county`, `service_area`, `bed_count_min/max`, `year_filed`, `final_outcome`, `final_decision_date_from/to`, `highest_review_level`, `service_type`, `phase`, `docket_variant`, `completeness_flag`, `q`. Paging: `limit` (default 50, max 500), `offset`; `sort` (prefix `-` for DESC) | `curl 'localhost:8000/matters?county=Fulton&service_type=PET&sort=-year_filed'` |
| GET | `/matters/{docket_id}` | Matter + variants + service types + phases + documents + weekly events; accepts any docket variant | `curl localhost:8000/matters/CON1234567` |
| GET | `/documents` | List/filter documents. Filters: `entry_id`, `docket_id`, `file_name`, `source_path`, `doc_type`, `decision_level`, `phase`, `outcome`, `validation_status`, `decision_maker`, `doc_date_from/to`, `page_count_min/max`, `repo_created_from/to`, `repo_modified_from/to`, `ocr_confidence_min/max`, `validated_by`, `validated_from/to`, `party`, `template_name`, `ocr_status`, `duplicate_of`, `q` | `curl 'localhost:8000/documents?doc_type=Order&doc_date_from=2024-01-01'` |
| GET | `/documents/{entry_id}` | Single document by Laserfiche entry id | `curl localhost:8000/documents/12345` |
| GET | `/dockets/{docket_id}/documents` | Documents for a docket; resolves any variant via `normalize_docket` + `con.matter_docket_variant` | `curl localhost:8000/dockets/GA-1234567/documents` |
| GET | `/search` | SQL full-text (`CONTAINSTABLE`) across matters/documents/events; `scope=matters\|documents\|events\|all`; LIKE fallback when `FULLTEXT_ENABLED=false` | `curl 'localhost:8000/search?q=hospice&scope=all'` |
| GET | `/changes` | Repository change log; `since=`, `change_type=added\|modified\|deleted`, `in_scope=` | `curl 'localhost:8000/changes?since=2026-01-01T00:00:00&in_scope=true'` |
| GET | `/watchlist` | Active watchlist entries (`?all=true` for inactive too) | `curl localhost:8000/watchlist` |
| POST | `/watchlist` | Add entry; requires at least one of `docket_id`/`entry_id`/`path_prefix` | `curl -X POST localhost:8000/watchlist -H 'content-type: application/json' -d '{"docket_id":"CON-1234567","reason":"client matter"}'` |
| DELETE | `/watchlist/{id}` | Soft-deactivate (sets `active=0`; never hard-deletes) | `curl -X DELETE localhost:8000/watchlist/7` |
| GET | `/reports/events` | Weekly DCH report events; `docket_id=`, `section=`, `since=` | `curl 'localhost:8000/reports/events?section=APPROVED&since=2026-06-01'` |
| GET | `/search/semantic` | Azure AI Search hybrid query (`q=`, `k=`): keyword + vector (when embeddings configured) + semantic ranking `con-semantic`; degrades to keyword-only | `curl 'localhost:8000/search/semantic?q=new+NICU+beds+in+Fulton'` |
| POST | `/ask` | Grounded Q&A: retrieve top-k from AI Search, answer via Azure OpenAI with `[entry_id or docket_id]` citations; unvalidated records flagged | `curl -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"Which hospice applications were denied in 2025?"}'` |

List responses are paginated: `{"items": [...], "total": <COUNT(*) with same filters>, "limit": n, "offset": n}`.
Endpoints needing Azure Search / Azure OpenAI return **503** naming the missing
setting when unconfigured.

### Research layer (v2) — console endpoints (`api/routers/*`)

| Method | Path | Description | Example |
|---|---|---|---|
| GET | `/cases/{entry_id}` | Case-reader payload: `con.opinion` + ordered paragraphs + headnotes + reporter citations + counsel + briefs + document/matter meta + citator flag counts; 404 when no opinion row exists | `curl localhost:8000/cases/9000030` |
| GET | `/dockets/{docket_id}/proceeding` | Docket-engine proceeding view (stored `con.proceeding_stage` rows when present, else synthesized from the matter via `common/proceeding.py`) + the `docket_event` timeline; accepts any docket variant | `curl localhost:8000/dockets/CON-1234567/proceeding` |
| GET | `/citator/{entry_id}` | How-cited report: `flags` (Citing/Positive/Cautionary/Negative counts), `citingCases`, `tableOfAuthorities` | `curl localhost:8000/citator/9000030` |
| GET | `/topics` | Full CON key-number topic tree | `curl localhost:8000/topics` |
| GET | `/topics/{topic_id}` | One topic: children, documents classified under it, headnote count | `curl localhost:8000/topics/vi-24` |
| GET | `/statutes` | Statute/rule index; optional `kind=OCGA\|RULE` | `curl 'localhost:8000/statutes?kind=OCGA'` |
| GET | `/statutes/{statute_id}` | Full text + subsections + cross-references + `citingCases` | `curl localhost:8000/statutes/31-6-43` |
| GET | `/history/{docket_id}` | `docket_event` timeline, newest first; optional `type=` one of `Filing\|Order\|Opinion\|Hearing\|Brief\|Notice`; accepts any docket variant | `curl 'localhost:8000/history/CON-1234567?type=Order'` |
| GET | `/stats` | Outcome aggregates over `con.matter`: grant/denial/reversal KPIs, `byService`/`byYear`/`byFamily`, appeal rates; `range=all\|3yr\|1yr` | `curl 'localhost:8000/stats?range=3yr'` |
| POST | `/deadlines/calculate` | Regulatory deadlines from a trigger event — **pure computation, no DB** (`common/deadline_rules.py`) | `curl -X POST localhost:8000/deadlines/calculate -H 'content-type: application/json' -d '{"family":"CON","triggerEvent":"Challenge filed","date":"2026-07-01"}'` |
| GET/POST | `/projects` | Research projects: list (`owner=`, `status=`) / create `{name, description?, tags?, owner?}` | `curl -X POST localhost:8000/projects -H 'content-type: application/json' -d '{"name":"NICU need methodology"}'` |
| GET | `/projects/{project_id}` | One project + its saved/flagged items | `curl localhost:8000/projects/nicu-need-methodology-3f9c1a` |
| POST | `/projects/{project_id}/items` | Add an item; requires `entryId` and/or `docketId` (dockets canonicalized) | `curl -X POST localhost:8000/projects/<id>/items -H 'content-type: application/json' -d '{"entryId":9000030,"flagged":true}'` |
| POST | `/projects/{project_id}/complete` | Mark a project complete | `curl -X POST localhost:8000/projects/<id>/complete` |
| GET/POST | `/alerts` | Saved alerts: list (active only; `?all=true`, `?owner=`) / create `{name, query, scope, frequency, owner?}` | `curl -X POST localhost:8000/alerts -H 'content-type: application/json' -d '{"name":"Fulton NICU","query":{"q":"NICU"},"scope":"matters","frequency":"weekly"}'` |
| DELETE | `/alerts/{alert_id}` | Soft-deactivate (sets `active=0`; never hard-deletes) | `curl -X DELETE localhost:8000/alerts/fulton-nicu-8b2d4e` |
| GET | `/wiki` | Wiki articles grouped by `group_name` | `curl localhost:8000/wiki` |
| GET | `/wiki/{article_id}` | One article: TOC + body + revision history | `curl localhost:8000/wiki/<article-id>` |
| POST | `/wiki/{article_id}/revisions` | Submit a **pending** revision `{author, diff}` | `curl -X POST localhost:8000/wiki/<id>/revisions -H 'content-type: application/json' -d '{"author":"you@tenant.com","diff":{"body":"..."}}'` |
| POST | `/wiki/{article_id}/revisions/{revision_id}/review` | Review a pending revision: `{action: "approve"\|"reject"}` | `curl -X POST localhost:8000/wiki/<id>/revisions/7/review -H 'content-type: application/json' -d '{"action":"approve"}'` |
| GET | `/me` | The platform-authenticated caller's profile; upserts `con.app_user` (identity + `last_seen_at`) on every hit. **401** when no identity header is present | `curl localhost:8000/me -H 'x-ms-client-principal: <base64>'` |

**camelCase convention**: research-endpoint JSON uses **camelCase keys**
(`docketId`, `citingCases`, `dueDate`, …) — the SPA contract from the design
handoff (`tests/fixtures/handoff/con-corpus.js`) — and omits `None`-valued
fields; DB columns stay snake_case and the routers map at the boundary. The v1
endpoints above keep their snake_case column names. `POST /deadlines/calculate`
accepts `triggerEvent` (alias) or `trigger_event`.

The console (`web/`) is the primary consumer of these endpoints. `/ask` stays
available but **optional** — the E7 Copilot path is preferred for end-user
natural-language questions (see the note at the bottom).

## Index sync CLI

```bash
python -m api.search_sync [--recreate] [--skip-vectors] [--batch-size 200]
```

Creates/updates the `con-records` index (semantic configuration `con-semantic`,
1536-dim HNSW `content_vector`) and pushes matters, documents (denormalized with
matter fields), and weekly events with `merge_or_upload`. Vectors are skipped
when `--skip-vectors` is passed or Azure OpenAI is unconfigured.

## Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `SQL_CONNECTION_STRING` | DB endpoints | Full ODBC string; wins when set |
| `SQL_SERVER`, `SQL_DATABASE` | DB endpoints | Used with `ActiveDirectoryDefault` when no connection string |
| `FULLTEXT_ENABLED` | `/matters`, `/documents`, `/search` | `true` (default) = `CONTAINSTABLE`; `false` = LIKE fallback |
| `SEARCH_ENDPOINT` | `/search/semantic`, `/ask`, `search_sync` | Required for those endpoints |
| `SEARCH_API_KEY` | same | Optional; `DefaultAzureCredential` when absent |
| `SEARCH_INDEX` | same | Default `con-records` |
| `AZURE_OPENAI_ENDPOINT` | `/ask`, embeddings | Required for `/ask`; optional for hybrid vectors |
| `AZURE_OPENAI_API_KEY` | same | Optional; Entra token when absent |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `/ask` | Default `gpt-4o-mini` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | vectors | Default `text-embedding-3-small` |
| `AZURE_OPENAI_API_VERSION` | AOAI client | Default `2024-06-01` |

## Auth

Deploy behind platform-level auth — the Static Web App's built-in **Entra ID
(AAD)** auth, or App Service **Easy Auth** with Entra ID (see DESIGN.md). All
endpoints assume the platform has already authenticated the caller; the API
never validates a token itself.

The platform forwards the authenticated identity via the base64-encoded JSON
`x-ms-client-principal` header (`{"identityProvider", "userId", "userDetails",
"userRoles", "claims"}`; `claims` may be absent). Plain App Service Easy Auth
headers (`x-ms-client-principal-name` / `x-ms-client-principal-id`) are used
as a fallback when that header is absent. `api/auth.py` parses these into a
`CurrentUser` (id, upn, email, name, provider, roles); the Entra object id
(`oid` claim) is preferred as the stable id, since UPN/email can change.

- **`GET /me`** requires an identity header (401 otherwise) and upserts
  `con.app_user` keyed on that stable id, returning
  `{"id", "upn", "email", "name", "provider", "roles"}`.
- **Ownership is server-authoritative** on `POST /watchlist`, `POST
  /projects`, and `POST /alerts`: when an identity header is present, it sets
  `created_by` / `owner` (upn, else email, else id) and any client-supplied
  owner value in the request body is ignored. When no identity header is
  present (local dev, or the API called directly without the platform in
  front of it), the client-supplied value from the request body is kept —
  unauthenticated local development is unaffected.
- Local dev and the test suite send neither header, so `parse_client_principal`
  returns `None` and every endpoint except `/me` behaves exactly as before.

## Note for E7 / Microsoft 365 users

End users should prefer **Microsoft Search / Copilot** via the Graph connector
(see `m365/`) for natural-language search over this data — it respects tenant
auth and surfaces results inside Office. This API's `/ask` endpoint is intended
for **programmatic / embedded scenarios** (scripts, internal tools, service
integrations), not as the primary end-user NL search experience.
