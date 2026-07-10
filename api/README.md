# api/ — FastAPI service for the GA DCH CON database

HTTP layer over the `con` schema in Azure SQL, plus Azure AI Search / Azure
OpenAI retrieval endpoints. Contracts live in the repo-root `DESIGN.md`.

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

No auth in code. Deploy behind platform-level auth — App Service **Easy Auth**
with Entra ID (see DESIGN.md). All endpoints assume the platform has already
authenticated the caller.

## Note for E7 / Microsoft 365 users

End users should prefer **Microsoft Search / Copilot** via the Graph connector
(see `m365/`) for natural-language search over this data — it respects tenant
auth and surfaces results inside Office. This API's `/ask` endpoint is intended
for **programmatic / embedded scenarios** (scripts, internal tools, service
integrations), not as the primary end-user NL search experience.
