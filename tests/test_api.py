"""Tests for api/ — FastAPI TestClient + FakeConnection. No live DB, no Azure."""

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
from api import search_sync
from tests.fakes import FakeConnection

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_conn() -> FakeConnection:
    return FakeConnection()


@pytest.fixture()
def client(fake_conn: FakeConnection):
    api_main.app.dependency_overrides[api_main.get_db] = lambda: fake_conn
    with TestClient(api_main.app) as test_client:
        yield test_client
    api_main.app.dependency_overrides.clear()


def executed_with(conn: FakeConnection, fragment: str) -> list[tuple[str, tuple]]:
    return [(sql, params) for sql, params in conn.executed if fragment in sql]


# ---------------------------------------------------------------------------
# /health and /vocab
# ---------------------------------------------------------------------------


def test_health_no_db(client, fake_conn):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_conn.executed == []


def test_vocab_county_has_159(client, fake_conn):
    response = client.get("/vocab/county")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 159
    assert len(body["items"]) == 159
    assert "Ben Hill" in body["items"]
    assert fake_conn.executed == []  # vocab never touches the DB


def test_vocab_decision_level(client):
    body = client.get("/vocab/decision_level").json()
    assert {"level": 2, "label": "Hearing Officer Decision"} in body["items"]


def test_vocab_unknown_name_404(client):
    response = client.get("/vocab/badname")
    assert response.status_code == 404
    assert "badname" in response.json()["detail"]


# ---------------------------------------------------------------------------
# /matters list
# ---------------------------------------------------------------------------

MATTER_COLUMNS = [
    "docket_id",
    "applicant",
    "facility",
    "county",
    "year_filed",
    "completeness_flags",
]
MATTER_ROW = (
    "CON-1234567",
    "Piedmont Healthcare",
    "Piedmont Atlanta Hospital",
    "Fulton",
    2024,
    json.dumps(["stub_from_weekly_report"]),
)


def test_matters_filters_are_parameterized(client, fake_conn):
    fake_conn.script("COUNT(*)", rows=[(1,)])
    fake_conn.script("SELECT m.*", rows=[MATTER_ROW], columns=MATTER_COLUMNS)

    response = client.get(
        "/matters", params={"applicant": "Piedmont Healthcare", "county": "Fulton"}
    )
    assert response.status_code == 200

    items_calls = executed_with(fake_conn, "SELECT m.*")
    assert len(items_calls) == 1
    sql, params = items_calls[0]
    # Parameter placeholders present; user values never interpolated into SQL.
    assert "?" in sql
    assert "Piedmont" not in sql
    assert "Fulton" not in sql
    assert "m.applicant LIKE ?" in sql
    assert "m.county = ?" in sql
    assert "%Piedmont Healthcare%" in params
    assert "Fulton" in params

    # COUNT(*) runs with the same WHERE and the same filter values.
    count_sql, count_params = executed_with(fake_conn, "COUNT(*)")[0]
    assert "Fulton" not in count_sql
    assert "Fulton" in count_params

    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 50 and body["offset"] == 0
    assert body["items"][0]["docket_id"] == "CON-1234567"
    # JSON column parsed to a list in the response.
    assert body["items"][0]["completeness_flags"] == ["stub_from_weekly_report"]


def test_matters_service_type_filters_via_exists(client, fake_conn):
    fake_conn.script("COUNT(*)", rows=[(0,)])
    fake_conn.script("SELECT m.*", rows=[], columns=MATTER_COLUMNS)

    response = client.get("/matters", params={"service_type": "PET", "phase": "Initial Application"})
    assert response.status_code == 200

    sql, params = executed_with(fake_conn, "SELECT m.*")[0]
    assert "EXISTS" in sql
    assert "con.matter_service_type" in sql
    assert "con.matter_phase" in sql
    assert "PET" not in sql  # value parameterized, not interpolated
    assert "PET" in params
    assert "Initial Application" in params


def test_matters_limit_clamped_at_500(client, fake_conn):
    fake_conn.script("COUNT(*)", rows=[(0,)])
    fake_conn.script("SELECT m.*", rows=[], columns=MATTER_COLUMNS)

    body = client.get("/matters", params={"limit": 9999}).json()
    assert body["limit"] == 500

    _, params = executed_with(fake_conn, "SELECT m.*")[0]
    assert params[-1] == 500  # FETCH NEXT ? ROWS ONLY
    assert 9999 not in params


def test_matters_q_uses_containstable_when_fulltext_enabled(client, fake_conn, monkeypatch):
    monkeypatch.setenv("FULLTEXT_ENABLED", "true")
    fake_conn.script("COUNT(*)", rows=[(0,)])
    fake_conn.script("SELECT m.*", rows=[], columns=MATTER_COLUMNS)

    assert client.get("/matters", params={"q": "hospice"}).status_code == 200
    sql, params = executed_with(fake_conn, "SELECT m.*")[0]
    assert "CONTAINSTABLE(con.matter" in sql
    assert "hospice" not in sql
    assert '"hospice*"' in params


def test_matters_rejects_unknown_sort_column(client, fake_conn):
    response = client.get("/matters", params={"sort": "docket_id; DROP TABLE con.matter"})
    assert response.status_code == 400
    assert fake_conn.executed == []


# ---------------------------------------------------------------------------
# /matters/{docket_id} — docket resolution
# ---------------------------------------------------------------------------


def test_matter_detail_resolves_variant_form(client, fake_conn):
    # The compact form CON1234567 is not a con.matter key; resolution must fall
    # through to con.matter_docket_variant, which owns it under CON-1234567.
    fake_conn.script(
        "SELECT docket_id FROM con.matter WHERE docket_id IN", rows=[], columns=["docket_id"]
    )
    fake_conn.script(
        "FROM con.matter_docket_variant WHERE variant IN",
        rows=[("CON-1234567",)],
        columns=["docket_id"],
    )
    fake_conn.script(
        "SELECT * FROM con.matter WHERE docket_id = ?", rows=[MATTER_ROW], columns=MATTER_COLUMNS
    )
    fake_conn.script(
        "SELECT variant FROM con.matter_docket_variant",
        rows=[("CON1234567",), ("GA-1234567",)],
        columns=["variant"],
    )
    fake_conn.script(
        "SELECT service_type FROM con.matter_service_type",
        rows=[("PET",)],
        columns=["service_type"],
    )
    fake_conn.script(
        "SELECT phase FROM con.matter_phase", rows=[("Initial Application",)], columns=["phase"]
    )
    fake_conn.script(
        "SELECT * FROM con.document WHERE docket_id = ?",
        rows=[(101, "CON-1234567", json.dumps(["Piedmont", "DCH"]))],
        columns=["entry_id", "docket_id", "parties"],
    )
    fake_conn.script("FROM con.weekly_report_event WHERE docket_id", rows=[], columns=["event_id"])

    response = client.get("/matters/CON1234567")
    assert response.status_code == 200

    # The variant lookup was queried with both the given string and the canonical.
    _, variant_params = executed_with(fake_conn, "WHERE variant IN")[0]
    assert set(variant_params) == {"CON1234567", "CON-1234567"}

    body = response.json()
    assert body["docket_id"] == "CON-1234567"
    assert body["docket_variants"] == ["CON1234567", "GA-1234567"]
    assert body["service_types"] == ["PET"]
    assert body["phases_present"] == ["Initial Application"]
    assert body["documents"][0]["entry_id"] == 101
    assert body["documents"][0]["parties"] == ["Piedmont", "DCH"]  # JSON parsed
    assert body["weekly_report_events"] == []


def test_matter_detail_unknown_docket_404(client, fake_conn):
    response = client.get("/matters/CON-9999999")  # nothing scripted -> no rows anywhere
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "CON-9999999" in detail
    assert "matter_docket_variant" in detail  # helpful detail names what was checked


def test_docket_documents_resolves_variant(client, fake_conn):
    fake_conn.script(
        "SELECT docket_id FROM con.matter WHERE docket_id IN",
        rows=[("CON-1234567",)],
        columns=["docket_id"],
    )
    fake_conn.script(
        "SELECT * FROM con.document WHERE docket_id = ?",
        rows=[(101, "CON-1234567", None)],
        columns=["entry_id", "docket_id", "parties"],
    )
    body = client.get("/dockets/GA-1234567/documents").json()
    assert body["docket_id"] == "CON-1234567"
    assert body["total"] == 1
    assert body["items"][0]["entry_id"] == 101


# ---------------------------------------------------------------------------
# /documents
# ---------------------------------------------------------------------------


def test_documents_date_range_filter(client, fake_conn):
    fake_conn.script("COUNT(*)", rows=[(0,)])
    fake_conn.script("SELECT d.*", rows=[], columns=["entry_id"])

    response = client.get(
        "/documents", params={"doc_date_from": "2024-01-01", "doc_date_to": "2024-12-31"}
    )
    assert response.status_code == 200

    sql, params = executed_with(fake_conn, "SELECT d.*")[0]
    assert "d.doc_date >= ?" in sql
    assert "d.doc_date <= ?" in sql
    assert "2024-01-01" not in sql and "2024-12-31" not in sql
    assert date(2024, 1, 1) in params
    assert date(2024, 12, 31) in params


def test_document_detail_parses_parties_and_404s(client, fake_conn):
    fake_conn.script(
        "SELECT * FROM con.document WHERE entry_id = ?",
        rows=[(101, "CON-1234567", json.dumps(["A", "B"]))],
        columns=["entry_id", "docket_id", "parties"],
    )
    body = client.get("/documents/101").json()
    assert body["parties"] == ["A", "B"]

    empty = FakeConnection()
    api_main.app.dependency_overrides[api_main.get_db] = lambda: empty
    assert client.get("/documents/999").status_code == 404


# ---------------------------------------------------------------------------
# /watchlist
# ---------------------------------------------------------------------------


def test_watchlist_post_requires_a_target(client, fake_conn):
    response = client.post("/watchlist", json={"reason": "no target keys at all"})
    assert response.status_code == 422
    assert fake_conn.executed == []


def test_watchlist_post_inserts_parameterized(client, fake_conn):
    fake_conn.script("OUTPUT INSERTED.watch_id", rows=[(42,)], columns=["watch_id"])
    response = client.post(
        "/watchlist", json={"docket_id": "CON1234567", "reason": "client matter"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["watch_id"] == 42
    assert body["docket_id"] == "CON-1234567"  # normalized to canonical
    assert body["active"] is True

    sql, params = executed_with(fake_conn, "INSERT INTO con.watchlist")[0]
    assert "?" in sql and "client matter" not in sql
    assert "client matter" in params
    assert fake_conn.committed == 1


def test_watchlist_delete_soft_deactivates_never_deletes(client, fake_conn):
    response = client.delete("/watchlist/7")
    assert response.status_code == 200
    assert response.json() == {"watch_id": 7, "active": False}

    update_calls = executed_with(fake_conn, "UPDATE con.watchlist SET active = 0")
    assert len(update_calls) == 1
    assert update_calls[0][1] == (7,)
    assert not any("DELETE" in sql.upper() for sql in fake_conn.executed_sql())
    assert fake_conn.committed == 1


def test_watchlist_get_defaults_to_active_only(client, fake_conn):
    fake_conn.script(
        "SELECT w.* FROM con.watchlist",
        rows=[(1, "CON-1234567", True)],
        columns=["watch_id", "docket_id", "active"],
    )
    assert client.get("/watchlist").json()["total"] == 1
    sql, params = executed_with(fake_conn, "SELECT w.*")[0]
    assert "w.active = ?" in sql and params == (1,)

    client.get("/watchlist", params={"all": "true"})
    sql_all = executed_with(fake_conn, "SELECT w.*")[1][0]
    assert "w.active" not in sql_all


# ---------------------------------------------------------------------------
# /search — LIKE fallback
# ---------------------------------------------------------------------------


def test_search_like_fallback_when_fulltext_disabled(client, fake_conn, monkeypatch):
    monkeypatch.setenv("FULLTEXT_ENABLED", "false")
    fake_conn.script(
        "SELECT m.* FROM con.matter m WHERE",
        rows=[("CON-1234567", "Hospice of Georgia")],
        columns=["docket_id", "applicant"],
    )

    response = client.get("/search", params={"q": "hospice", "scope": "matters"})
    assert response.status_code == 200

    sql, params = executed_with(fake_conn, "FROM con.matter m WHERE")[0]
    assert "LIKE" in sql
    assert "CONTAINSTABLE" not in sql
    assert "hospice" not in sql  # parameterized
    assert "%hospice%" in params

    body = response.json()
    assert body["fulltext"] is False
    assert body["hits"][0]["type"] == "matter"
    assert body["hits"][0]["rank"] is None
    assert body["hits"][0]["record"]["docket_id"] == "CON-1234567"


def test_search_rejects_unknown_scope(client, fake_conn):
    assert client.get("/search", params={"q": "x", "scope": "everything"}).status_code == 400
    assert fake_conn.executed == []


# ---------------------------------------------------------------------------
# /ask and /search/semantic — 503 when Azure Search is unconfigured
# ---------------------------------------------------------------------------


def test_ask_503_when_search_env_missing(client, monkeypatch):
    monkeypatch.delenv("SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    response = client.post("/ask", json={"question": "Which NICU applications were approved?"})
    assert response.status_code == 503
    assert "SEARCH_ENDPOINT" in response.json()["detail"]


def test_semantic_search_503_when_search_env_missing(client, monkeypatch):
    monkeypatch.delenv("SEARCH_ENDPOINT", raising=False)
    response = client.get("/search/semantic", params={"q": "NICU beds"})
    assert response.status_code == 503
    assert "SEARCH_ENDPOINT" in response.json()["detail"]


# ---------------------------------------------------------------------------
# api.search_sync — pure row -> search-doc shaping
# ---------------------------------------------------------------------------


def test_matter_row_shapes_to_search_doc():
    row = {
        "docket_id": "CON-1234567",
        "applicant": "Piedmont Healthcare",
        "facility": "Piedmont Atlanta Hospital",
        "matter_type": "CON Application",
        "action_type": "Bed or capacity addition",
        "county": "Fulton",
        "service_area": "Service Area 3",
        "bed_count": 24,
        "year_filed": 2024,
        "final_outcome": "Approved",
        "final_decision_date": date(2024, 11, 2),
        "highest_review_level": 1,
        "service_types": "Acute-care/general hospital beds;PET",
        "phases": "Initial Application",
    }
    doc = search_sync.matter_to_search_doc(row)
    assert doc["key"] == "matter_CON-1234567"
    assert doc["record_type"] == "matter"
    assert doc["docket_id"] == "CON-1234567"
    assert doc["service_types"] == ["Acute-care/general hospital beds", "PET"]
    assert doc["year_filed"] == 2024
    assert doc["outcome"] == "Approved"
    assert doc["doc_date"] == "2024-11-02T00:00:00Z"
    assert "CON-1234567" in doc["title"]
    # content is a readable concatenation of the record's fields
    assert "Applicant: Piedmont Healthcare" in doc["content"]
    assert "County: Fulton" in doc["content"]
    assert "Bed count: 24" in doc["content"]
    assert "Service types: Acute-care/general hospital beds, PET" in doc["content"]


def test_document_row_shapes_to_search_doc_with_matter_fields():
    row = {
        "entry_id": 4711,
        "docket_id": "CON-1234567",
        "docview_url": "https://laserfiche/docview/4711",
        "file_name": "Final Agency Decision.pdf",
        "doc_type": "Final Agency Decision",
        "decision_level": 2,
        "phase": "Administrative Appeal",
        "doc_date": date(2025, 3, 15),
        "decision_maker": "Hearing Officer Smith",
        "outcome": "Denied",
        "template_name": "CON Decision",
        "source_path": r"\CON\2024\CON-1234567",
        "validation_status": "Validated",
        "applicant": "Piedmont Healthcare",  # denormalized from the matter
        "facility": "Piedmont Atlanta Hospital",
        "county": "Fulton",
        "matter_type": "CON Application",
        "action_type": "Bed or capacity addition",
        "year_filed": 2024,
        "service_types": "PET",
    }
    doc = search_sync.document_to_search_doc(row)
    assert doc["key"] == "document_4711"
    assert doc["record_type"] == "document"
    assert doc["entry_id"] == 4711
    assert doc["applicant"] == "Piedmont Healthcare"
    assert doc["service_types"] == ["PET"]
    assert doc["doc_date"] == "2025-03-15T00:00:00Z"
    assert doc["validation_status"] == "Validated"
    assert doc["docview_url"] == "https://laserfiche/docview/4711"
    assert "Decision maker: Hearing Officer Smith" in doc["content"]
    assert "Outcome: Denied" in doc["content"]


def test_event_row_shapes_to_search_doc():
    row = {
        "event_id": 88,
        "report_date": date(2026, 6, 26),
        "section": "APPROVED",
        "docket_id": "CON-7654321",
        "docket_raw": "CON 7654321",
        "applicant": "Wellstar Health System",
        "project_description": "Add 12 NICU beds",
        "county": "Cobb",
        "cost": 12500000,
        "opposition": "None",
        "filing_date": date(2026, 1, 5),
        "decision_deadline": None,
        "decision_date": date(2026, 6, 20),
    }
    doc = search_sync.event_to_search_doc(row)
    assert doc["key"] == "event_88"
    assert doc["record_type"] == "event"
    assert doc["docket_id"] == "CON-7654321"
    assert doc["doc_date"] == "2026-06-26T00:00:00Z"
    assert "Project description: Add 12 NICU beds" in doc["content"]
    assert "Weekly report section: APPROVED" in doc["content"]
