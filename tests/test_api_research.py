"""Tests for the research-layer routers (api/routers/*) — TestClient + FakeConnection.

Same pattern as tests/test_api.py: no live DB, dependency_overrides swap in a
FakeConnection, and every test asserts parameterized SQL (user values appear
in params, never interpolated into the SQL text).
"""

import base64
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
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


def script_docket_resolution(conn: FakeConnection, canonical: str = "CON-1234567") -> None:
    conn.script(
        "SELECT docket_id FROM con.matter WHERE docket_id IN",
        rows=[(canonical,)],
        columns=["docket_id"],
    )


def principal_headers(payload: dict) -> dict[str, str]:
    """A forged x-ms-client-principal header, as SWA/Entra would send it."""
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {"x-ms-client-principal": encoded}


# ---------------------------------------------------------------------------
# /cases/{entry_id}
# ---------------------------------------------------------------------------

OPINION_COLUMNS = [
    "entry_id",
    "caption_json",
    "tribunal_line",
    "byline",
    "intro_text",
    "disposition_json",
    "editorial_synopsis",
    "decided_date",
    "argued_date",
    "court_docket_no",
    "subsequent_history",
    "is_published",
    "standard_of_review",
    "treatment_level",
    "treatment_note_json",
]

OPINION_ROW = (
    101,
    json.dumps([["i", "Riverstone Imaging, LLC"], " v. ", ["i", "Ga. Dep't of Cmty. Health"]]),
    "Court of Appeals of Georgia · Fifth Division · Published Opinion",
    "PIPKIN, Judge.",
    "Riverstone Imaging, LLC appeals from the final order…",
    json.dumps([["b", "Judgment affirmed."]]),
    "Court of Appeals affirmed the Superior Court's reversal…",
    "2025-12-04",
    "2025-09-09",
    "No. A25A0917",
    "Cert. denied, Mar. 12, 2026",
    1,
    "Substantial evidence",
    "caution",
    json.dumps({"word": "Caution.", "text": [" Distinguished by ", ["case", "Three Rivers", "three-rivers"]]}),
)


def test_case_404_when_no_opinion(client, fake_conn):
    response = client.get("/cases/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]
    sql, params = executed_with(fake_conn, "FROM con.opinion o")[0]
    assert "?" in sql and params == (999,)


def test_case_reader_payload_camelcase(client, fake_conn):
    fake_conn.script("FROM con.opinion o", rows=[OPINION_ROW], columns=OPINION_COLUMNS)
    fake_conn.script(
        "FROM con.document d WHERE",
        rows=[(101, "CON-1234567", "Riverstone Imaging, LLC v. DCH")],
        columns=["entry_id", "docket_id", "title"],
    )
    fake_conn.script(
        "FROM con.matter m WHERE",
        rows=[("CON-1234567", "Riverstone Imaging, LLC", "Riverstone Imaging Center", "Bartow", "CON")],
        columns=["docket_id", "applicant", "facility", "county", "docket_family"],
    )
    fake_conn.script("con.matter_service_type st", rows=[("MRI",)], columns=["service_type"])
    fake_conn.script(
        "con.opinion_paragraph",
        rows=[
            ("1", json.dumps(["In February 2023, ", ["stat", "O.C.G.A. § 31-6-43", "31-6-43"]])),
            ("2", json.dumps(["The Department redefined the service area."])),
        ],
        columns=["para_num", "segs_json"],
    )
    fake_conn.script(
        "FROM con.headnote h",
        rows=[("1", "vi-24", "Substantial Evidence — Standard of Review",
               "Judicial review is confined to substantial evidence…", "CON VI · 24")],
        columns=["num", "topic_id", "topic_label", "text", "key_number"],
    )
    fake_conn.script(
        "con.reporter_citation rc",
        rows=[("372 Ga. App. 488",), ("902 S.E.2d 144",)],
        columns=["citation"],
    )
    fake_conn.script(
        "FROM con.counsel c",
        rows=[("For Appellee Riverstone", "Andrew T. Halverson", "Parker, Hudson, Rainer & Dobbs LLP")],
        columns=["role", "attorney_name", "firm"],
    )
    fake_conn.script(
        "FROM con.brief b",
        rows=[("Brief of Appellee Riverstone Imaging, LLC", "Appellee",
               "Andrew T. Halverson", "Parker, Hudson, Rainer & Dobbs LLP", "2025-07-22", 48)],
        columns=["title", "party_side", "attorney_name", "firm", "filed_date", "page_count"],
    )
    fake_conn.script(
        "GROUP BY treatment", rows=[("Followed", 2), ("Distinguished", 1)], columns=["treatment", "n"]
    )

    response = client.get("/cases/101")
    assert response.status_code == 200
    body = response.json()

    # camelCase keys mirroring con-corpus.js field names.
    assert body["captionParts"][0] == ["i", "Riverstone Imaging, LLC"]
    assert body["tribunalLine"].startswith("Court of Appeals of Georgia")
    assert body["citations"] == ["372 Ga. App. 488", "902 S.E.2d 144"]
    assert body["docketNo"] == "No. A25A0917"
    assert body["decided"] == "2025-12-04"
    assert body["subsequent"] == "Cert. denied, Mar. 12, 2026"
    assert body["treatment"]["level"] == "caution"
    assert body["treatment"]["word"] == "Caution."
    assert body["treatment"]["text"][1] == ["case", "Three Rivers", "three-rivers"]
    assert body["editorial"].startswith("Court of Appeals affirmed")
    assert body["headnotes"] == [
        {
            "num": "1",
            "key": "CON VI · 24",
            "keyId": "vi-24",
            "topic": "Substantial Evidence — Standard of Review",
            "text": "Judicial review is confined to substantial evidence…",
        }
    ]
    assert body["byline"] == "PIPKIN, Judge."
    assert body["intro"].startswith("Riverstone Imaging, LLC appeals")
    # paragraphs[].segs parsed from segs_json.
    assert body["paragraphs"][0]["num"] == "1"
    assert body["paragraphs"][0]["segs"][1] == ["stat", "O.C.G.A. § 31-6-43", "31-6-43"]
    assert body["paragraphs"][1]["segs"] == ["The Department redefined the service area."]
    assert body["disposition"] == [["b", "Judgment affirmed."]]
    assert body["meta"]["Applicant"] == "Riverstone Imaging, LLC"
    assert body["meta"]["Service"] == "MRI"
    assert body["meta"]["CON No."] == "CON-1234567"
    assert body["counsel"] == [
        {
            "role": "For Appellee Riverstone",
            "name": "Andrew T. Halverson",
            "firm": "Parker, Hudson, Rainer & Dobbs LLP",
        }
    ]
    assert body["briefs"][0]["title"] == "Brief of Appellee Riverstone Imaging, LLC"
    assert body["briefs"][0]["pageCount"] == 48
    assert body["badge"] == "CON"
    assert body["citator"]["flags"] == [
        {"label": "Citing", "count": 3},
        {"label": "Positive", "count": 2},
        {"label": "Cautionary", "count": 1},
        {"label": "Negative", "count": 0},
    ]

    # Parameterized SQL: the entry id is bound, never interpolated.
    sql, params = executed_with(fake_conn, "FROM con.opinion o")[0]
    assert "101" not in sql and params == (101,)


# ---------------------------------------------------------------------------
# /dockets/{docket_id}/proceeding
# ---------------------------------------------------------------------------

MATTER_RESEARCH_COLUMNS = [
    "docket_id",
    "docket_family",
    "facility",
    "project_description",
    "letter_of_intent_date",
    "year_filed",
    "final_decision_date",
    "final_outcome",
    "county",
]


def test_proceeding_synthesized_for_con(client, fake_conn):
    script_docket_resolution(fake_conn)
    fake_conn.script(
        "FROM con.matter m WHERE",
        rows=[("CON-1234567", "CON", "Riverstone Imaging Center", "Fixed MRI (1.5T)",
               "2023-01-15", 2023, "2025-12-04", "Approved", "Bartow")],
        columns=MATTER_RESEARCH_COLUMNS,
    )
    fake_conn.script("FROM con.proceeding_stage s", rows=[], columns=["stage_id"])
    fake_conn.script(
        "FROM con.docket_event e",
        rows=[(1, "2025-12-04", "Opinion", "Court of Appeals of Georgia",
               "OPINION — Judgment Affirmed", "Pipkin, J.", 101)],
        columns=["event_id", "event_date", "event_type", "court", "description", "actor", "entry_id"],
    )

    response = client.get("/dockets/CON1234567/proceeding")
    assert response.status_code == 200
    body = response.json()

    assert body["docketId"] == "CON-1234567"
    assert body["source"] == "synthesized"
    # Engine shape keys (common.proceeding.build_proceeding / docket-engine.js).
    for key in ("badge", "isClosed", "isActive", "filedLine", "compact", "stages"):
        assert key in body
    assert body["badge"] == {"label": "CON", "color": "#F43F5E"}
    assert body["isClosed"] is True and body["isActive"] is False
    assert body["filedLine"] == "Filed Jan 15, 2023"
    assert body["closedLine"] == "Closed Dec 4, 2025"
    assert len(body["stages"]) == 8  # CON engine stages 0-7
    assert body["stages"][0]["title"] == "Letter of Intent"
    assert body["precedent"]["key"] in ("valid", "questioned", "overturned")
    # Timeline included, mapped to camelCase.
    assert body["events"][0]["type"] == "Opinion"
    assert body["events"][0]["entryId"] == 101

    # Docket resolution used parameterized variants, not interpolation.
    sql, params = executed_with(fake_conn, "WHERE docket_id IN")[0]
    assert "CON1234567" not in sql and "CON1234567" in params


def test_proceeding_stored_stages_win(client, fake_conn):
    script_docket_resolution(fake_conn)
    fake_conn.script(
        "FROM con.matter m WHERE",
        rows=[("CON-1234567", "CON", None, None, None, 2023, "2025-12-04", "Denied", "Bartow")],
        columns=MATTER_RESEARCH_COLUMNS,
    )
    fake_conn.script(
        "FROM con.proceeding_stage s",
        rows=[
            ("01", "Application", "DCH Planning Section", "CON Application Filed",
             "CON 23-0118", "2023-03-01", "Filed", "Filed Mar 1, 2023", 14,
             "M. Patel, Planning Officer", None, 0, 0, None, 0),
            ("02", "Initial Decision", "DCH Planning Section", "Initial Decision — Denied",
             None, "2023-06-30", "Denied", "Issued Jun 30, 2023", 3, None, 121, 1, 1, 101, 1),
        ],
        columns=["stage_num", "stage_label", "court", "title", "cite", "stage_date",
                 "outcome", "summary", "filings_count", "decision_maker", "duration_days",
                 "is_current", "has_opinion", "opinion_entry_id", "sort_order"],
    )
    fake_conn.script("FROM con.docket_event e", rows=[], columns=["event_id"])

    body = client.get("/dockets/CON-1234567/proceeding").json()
    assert body["source"] == "stored"
    assert body["isClosed"] is True
    assert len(body["stages"]) == 2
    first, second = body["stages"]
    assert first["n"] == "01" and first["status"] == "complete"
    assert first["title"] == "CON Application Filed"
    assert first["dateLine"] == "Filed Mar 1, 2023"
    assert second["status"] == "active"  # is_current
    assert second["opinionEntryId"] == 101
    assert "cite" not in second  # None values dropped


# ---------------------------------------------------------------------------
# /citator/{entry_id}
# ---------------------------------------------------------------------------


def test_citator_flags_and_lists(client, fake_conn):
    fake_conn.script(
        "GROUP BY treatment",
        rows=[("Followed", 2), ("Distinguished", 1), ("Reversed", 1), (None, 3)],
        columns=["treatment", "n"],
    )
    fake_conn.script(
        "m.docket_family",
        rows=[(202, "Followed", 4, "Following Riverstone; population-based methodology…",
               "p. 214", "vi-24", "CON VI · 24", "CON-2026004",
               "Magnolia Behavioral Health, LLC v. DCH", "CON", "No. 2024CV-3318",
               "Fulton Super. Ct. (2024)")],
        columns=["citing_entry_id", "treatment", "depth", "snippet", "pinpoint", "topic_id",
                 "key_number", "docket_id", "case_title", "docket_family", "court_docket_no",
                 "case_cite"],
    )
    fake_conn.script(
        "s.citation_label",
        rows=[
            (1, 303, None, None, "pp. 213-217",
             "Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC",
             "358 Ga. App. 211", None, None, None),
            (2, None, "31-6-44.1", None, "subsection (b)", None, None,
             "OCGA", "O.C.G.A. § 31-6-44.1", "Judicial Review"),
            (3, None, None, "5 U.S.C. § 706", None, None, None, None, None, None),
        ],
        columns=["citation_id", "cited_entry_id", "cited_statute_id", "cited_external",
                 "pinpoint", "case_title", "case_cite", "statute_kind", "citation_label",
                 "statute_title"],
    )

    response = client.get("/citator/101")
    assert response.status_code == 200
    body = response.json()

    assert body["entryId"] == 101
    assert body["flags"] == [
        {"label": "Citing", "count": 7},
        {"label": "Positive", "count": 2},
        {"label": "Cautionary", "count": 1},
        {"label": "Negative", "count": 1},
    ]

    citing = body["citingCases"][0]
    assert citing["badge"] == "CON"
    assert citing["dktNum"] == "No. 2024CV-3318"  # court docket no wins over matter id
    assert citing["treat"] == "Followed" and citing["level"] == "positive"
    assert citing["title"] == "Magnolia Behavioral Health, LLC v. DCH"
    assert citing["cite"] == "Fulton Super. Ct. (2024)"
    assert citing["depth"] == 4
    assert citing["keys"] == [["CON VI · 24", "vi-24"]]
    assert citing["target"] == 202

    toa = body["tableOfAuthorities"]
    assert toa[0]["kind"] == "case" and toa[0]["target"] == 303
    assert toa[0]["cite"] == "358 Ga. App. 211"
    assert toa[1] == {
        "title": "O.C.G.A. § 31-6-44.1 — Judicial Review",
        "cite": "Ga. Code Ann.",
        "pinpoint": "subsection (b)",
        "target": "31-6-44.1",
        "kind": "stat",
    }
    assert toa[2]["kind"] == "external" and toa[2]["title"] == "5 U.S.C. § 706"

    # Flag counts come from one parameterized GROUP BY query.
    flag_calls = executed_with(fake_conn, "GROUP BY treatment")
    assert len(flag_calls) == 1
    assert flag_calls[0][1] == (101,)


# ---------------------------------------------------------------------------
# /topics
# ---------------------------------------------------------------------------


def test_topics_tree_nesting(client, fake_conn):
    fake_conn.script(
        "FROM con.topic t ORDER BY",
        rows=[
            ("iii", None, "CON III", "Need / Utilization", None),
            ("iii-7", "iii", "CON III · 7", "Service Area Methodology", "Referral patterns…"),
            ("vi", None, "CON VI", "Judicial Review", None),
            ("vi-24", "vi", "CON VI · 24", "Substantial Evidence", None),
        ],
        columns=["topic_id", "parent_topic_id", "key_number", "title", "description"],
    )
    body = client.get("/topics").json()
    assert body["total"] == 4
    roots = body["topics"]
    assert [r["topicId"] for r in roots] == ["iii", "vi"]
    assert roots[0]["children"][0]["topicId"] == "iii-7"
    assert roots[0]["children"][0]["keyNumber"] == "CON III · 7"
    assert roots[1]["children"][0]["topicId"] == "vi-24"
    assert "description" not in roots[0]  # None dropped


def test_topic_detail_documents_and_headnote_count(client, fake_conn):
    fake_conn.script(
        "FROM con.topic t WHERE t.topic_id = ?",
        rows=[("vi-24", "vi", "CON VI · 24", "Substantial Evidence", None)],
        columns=["topic_id", "parent_topic_id", "key_number", "title", "description"],
    )
    fake_conn.script(
        "con.document_topic",
        rows=[(101, "CON-1234567", "Riverstone Imaging, LLC v. DCH", "Court Order/Opinion",
               "2025-12-04", "CON", "Riverstone Imaging, LLC", "Riverstone Imaging Center")],
        columns=["entry_id", "docket_id", "title", "doc_type", "doc_date", "docket_family",
                 "applicant", "facility"],
    )
    fake_conn.script("SELECT COUNT(*) FROM con.headnote", rows=[(5,)])
    fake_conn.script("t.parent_topic_id = ?", rows=[], columns=["topic_id"])

    body = client.get("/topics/vi-24").json()
    assert body["topicId"] == "vi-24"
    assert body["keyNumber"] == "CON VI · 24"
    assert body["headnoteCount"] == 5
    assert body["documents"][0]["entryId"] == 101
    assert body["documents"][0]["badge"] == "CON"

    sql, params = executed_with(fake_conn, "con.document_topic")[0]
    assert "vi-24" not in sql and params == ("vi-24",)


# ---------------------------------------------------------------------------
# /statutes
# ---------------------------------------------------------------------------


def test_statutes_list_kind_filter(client, fake_conn):
    fake_conn.script(
        "FROM con.statute s",
        rows=[("rule-111-2-2-.40", "RULE", "Ga. Comp. R. & Regs. 111-2-2-.40",
               "MRI Need Methodology", None)],
        columns=["statute_id", "kind", "citation_label", "title", "effective_date"],
    )
    body = client.get("/statutes", params={"kind": "RULE"}).json()
    assert body["total"] == 1
    assert body["items"][0]["statuteId"] == "rule-111-2-2-.40"
    sql, params = executed_with(fake_conn, "FROM con.statute s")[0]
    assert "s.kind = ?" in sql and "RULE" not in sql and params == ("RULE",)

    assert client.get("/statutes", params={"kind": "USC"}).status_code == 400


def test_statute_detail_with_xrefs_and_citing_cases(client, fake_conn):
    fake_conn.script(
        "FROM con.statute s WHERE s.statute_id",
        rows=[("31-6-44.1", "OCGA", "O.C.G.A. § 31-6-44.1", "Judicial Review",
               "Full statutory text…", "2024-07-01", "HB 1339 (2024) rewrote judicial review.",
               json.dumps([{"id": "a", "text": "Any party…"}, {"id": "b", "text": "Remand…"}]))],
        columns=["statute_id", "kind", "citation_label", "title", "full_text",
                 "effective_date", "regime_note", "subsections_json"],
    )
    fake_conn.script(
        "con.statute_xref",
        rows=[("50-13-19", "O.C.G.A. § 50-13-19", "Judicial review of contested cases")],
        columns=["statute_id", "citation_label", "title"],
    )
    fake_conn.script(
        "c.cited_statute_id = ?",
        rows=[(101, None, "subsection (b)", "See § 31-6-44.1(b).",
               "Riverstone Imaging, LLC v. DCH", "CON-1234567", "CON", "372 Ga. App. 488")],
        columns=["citing_entry_id", "treatment", "pinpoint", "snippet", "case_title",
                 "docket_id", "docket_family", "case_cite"],
    )

    body = client.get("/statutes/31-6-44.1").json()
    assert body["statuteId"] == "31-6-44.1"
    assert body["citationLabel"] == "O.C.G.A. § 31-6-44.1"
    assert body["subsections"] == [{"id": "a", "text": "Any party…"}, {"id": "b", "text": "Remand…"}]
    assert body["xrefs"] == [
        {
            "statuteId": "50-13-19",
            "citationLabel": "O.C.G.A. § 50-13-19",
            "title": "Judicial review of contested cases",
        }
    ]
    assert body["citingCases"][0]["target"] == 101
    assert body["citingCases"][0]["cite"] == "372 Ga. App. 488"
    assert "level" not in body["citingCases"][0]  # no treatment recorded

    sql, params = executed_with(fake_conn, "c.cited_statute_id = ?")[0]
    assert "31-6-44.1" not in sql and params == ("31-6-44.1",)

    empty = FakeConnection()
    api_main.app.dependency_overrides[api_main.get_db] = lambda: empty
    assert client.get("/statutes/nope").status_code == 404


# ---------------------------------------------------------------------------
# /history/{docket_id}
# ---------------------------------------------------------------------------


def test_history_type_filter_parameterized(client, fake_conn):
    script_docket_resolution(fake_conn)
    fake_conn.script(
        "FROM con.docket_event e",
        rows=[(2, "2025-03-18", "Order", "Superior Court of Fulton County",
               "ORDER — Reversed and Remanded", "Welch, J.", None)],
        columns=["event_id", "event_date", "event_type", "court", "description", "actor",
                 "entry_id"],
    )
    response = client.get("/history/CON1234567", params={"type": "Order"})
    assert response.status_code == 200
    body = response.json()
    assert body["docketId"] == "CON-1234567"
    assert body["total"] == 1
    assert body["items"][0]["type"] == "Order"
    assert body["items"][0]["actor"] == "Welch, J."
    assert "entryId" not in body["items"][0]  # None dropped

    sql, params = executed_with(fake_conn, "FROM con.docket_event e")[0]
    assert "e.event_type = ?" in sql
    assert "'Order'" not in sql  # value bound, not quoted into the SQL
    assert params == ("CON-1234567", "Order")
    assert "e.event_date DESC" in sql


def test_history_rejects_unknown_event_type(client, fake_conn):
    response = client.get("/history/CON-1234567", params={"type": "Tweet"})
    assert response.status_code == 400
    assert "Tweet" in response.json()["detail"]
    assert fake_conn.executed == []  # rejected before any DB access


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------


def _script_stats(fake_conn: FakeConnection) -> None:
    fake_conn.script(
        "GROUP BY m.final_outcome",
        rows=[("Approved", 6), ("Denied", 3), ("Pending", 1)],
        columns=["final_outcome", "n"],
    )
    fake_conn.script(
        "m.highest_review_level",
        rows=[(10, 4, 1, 2)],
        columns=["total", "appealed", "reversed", "affirmed"],
    )
    fake_conn.script(
        "GROUP BY st.service_type",
        rows=[("MRI", 5, 3, 2), ("PET", 3, 2, 1)],
        columns=["service_type", "total", "approved", "denied"],
    )
    fake_conn.script(
        "GROUP BY m.year_filed",
        rows=[(2024, 4, 2, 1), (2025, 6, 4, 2)],
        columns=["year_filed", "total", "approved", "denied"],
    )
    fake_conn.script(
        "GROUP BY m.docket_family",
        rows=[("CON", 8, 5, 3), ("DET", 2, 1, 0)],
        columns=["docket_family", "total", "approved", "denied"],
    )


def test_stats_kpis_and_breakdowns(client, fake_conn):
    _script_stats(fake_conn)
    body = client.get("/stats").json()

    assert body["range"] == "all"
    assert "cutoffYear" not in body  # no cutoff for range=all
    assert body["kpis"] == {
        "totalDockets": 10,
        "grantRate": 66.7,     # 6 / (6 + 3)
        "denialRate": 33.3,
        "reversalRate": 25.0,  # 1 reversed / 4 appealed
    }
    assert body["appeal"] == {"appealedPct": 40.0, "reversalPct": 25.0, "affirmancePct": 50.0}
    assert body["byService"][0] == {"serviceType": "MRI", "total": 5, "approved": 3, "denied": 2}
    assert body["byYear"][0]["year"] == 2024
    assert body["byFamily"][0]["family"] == "CON"

    # Outcome codes are bound parameters, never inlined.
    sql, params = executed_with(fake_conn, "m.highest_review_level")[0]
    assert "Reversed (appeal)" not in sql
    assert "Reversed (appeal)" in params and "Affirmed (appeal)" in params


def test_stats_range_cutoff_computed_in_python(client, fake_conn):
    _script_stats(fake_conn)
    body = client.get("/stats", params={"range": "3yr"}).json()
    cutoff = date.today().year - 3
    assert body["cutoffYear"] == cutoff

    sql, params = executed_with(fake_conn, "GROUP BY m.final_outcome")[0]
    assert "m.year_filed >= ?" in sql
    assert "GETDATE" not in sql.upper().replace(" ", "")
    assert str(cutoff) not in sql and cutoff in params


def test_stats_rejects_unknown_range(client, fake_conn):
    assert client.get("/stats", params={"range": "5yr"}).status_code == 400
    assert fake_conn.executed == []


# ---------------------------------------------------------------------------
# /deadlines/calculate — pure, no DB
# ---------------------------------------------------------------------------


def test_deadlines_calculate_known_offset_no_db(client, fake_conn):
    response = client.post(
        "/deadlines/calculate",
        json={"family": "CON", "triggerEvent": "Letter of determination", "date": "2026-01-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["family"] == "CON"
    assert len(body["deadlines"]) == 1
    deadline = body["deadlines"][0]
    assert deadline["label"] == "Challenge Window"
    assert deadline["dueDate"] == "2026-01-31"  # 30 days after the trigger date
    assert deadline["basisStatute"] == "31-6-44"
    assert deadline["description"].startswith("Request for an administrative hearing")
    assert fake_conn.executed == []  # pure: no DB access


def test_deadlines_family_validated_against_vocab(client, fake_conn):
    response = client.post(
        "/deadlines/calculate",
        json={"family": "ZZZ", "triggerEvent": "Letter of determination", "date": "2026-01-01"},
    )
    assert response.status_code == 422
    assert fake_conn.executed == []


# ---------------------------------------------------------------------------
# /projects
# ---------------------------------------------------------------------------


def test_project_create_slug_id_and_parameterized(client, fake_conn):
    response = client.post(
        "/projects",
        json={"name": "MRI Need Research", "description": "Service-area cases", "tags": ["mri"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "MRI Need Research"
    assert body["status"] == "open"
    assert body["tags"] == ["mri"]
    # projectId = slug of the name + short random suffix (matches
    # web/src/lib/types.ts ResearchProject.projectId, not a bare "id").
    assert body["projectId"].startswith("mri-need-research-")
    assert len(body["projectId"]) == len("mri-need-research-") + 6

    sql, params = executed_with(fake_conn, "INSERT INTO con.research_project")[0]
    assert "MRI Need Research" not in sql
    assert "MRI Need Research" in params
    assert json.dumps(["mri"]) in params
    assert "open" in params
    assert fake_conn.committed == 1


def test_projects_list_uses_project_id_key_not_bare_id(client, fake_conn):
    # web/src/lib/api.ts's listProjects() does `return req('/projects')` with no
    # field-renaming adapter (unlike getWikiArticle, which explicitly maps
    # raw.id -> articleId): the wire shape must already match ResearchProject
    # (projectId), or web/src/views/Library.tsx's `p.projectId` links break.
    fake_conn.script(
        "SELECT p.* FROM con.research_project p",
        rows=[("p1", "owner@example.com", "MRI Need Research", None, None, "open", None)],
        columns=["project_id", "owner_upn", "name", "description", "tags_json", "status",
                 "created_at"],
    )
    body = client.get("/projects").json()
    assert body["items"][0]["projectId"] == "p1"
    assert "id" not in body["items"][0]


def test_project_item_requires_a_target(client, fake_conn):
    response = client.post("/projects/p1/items", json={"note": "no target"})
    assert response.status_code == 400
    assert fake_conn.executed == []  # rejected before any DB access


def test_project_add_item(client, fake_conn):
    fake_conn.script(
        "SELECT project_id FROM con.research_project", rows=[("p1",)], columns=["project_id"]
    )
    fake_conn.script("OUTPUT INSERTED.item_id", rows=[(7,)], columns=["item_id"])
    response = client.post(
        "/projects/p1/items", json={"entryId": 101, "flagged": True, "note": "key case"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["itemId"] == 7
    assert body["entryId"] == 101 and body["flagged"] is True

    sql, params = executed_with(fake_conn, "INSERT INTO con.project_item")[0]
    assert "key case" not in sql and "key case" in params
    assert 101 in params
    assert fake_conn.committed == 1


def test_project_add_item_unknown_project_404(client, fake_conn):
    assert client.post("/projects/nope/items", json={"entryId": 101}).status_code == 404


def test_project_complete_sets_status(client, fake_conn):
    response = client.post("/projects/p1/complete")
    assert response.status_code == 200
    assert response.json() == {"id": "p1", "status": "complete"}
    sql, params = executed_with(fake_conn, "UPDATE con.research_project SET status = ?")[0]
    assert params == ("complete", "p1")
    assert fake_conn.committed == 1


# ---------------------------------------------------------------------------
# /alerts
# ---------------------------------------------------------------------------


def test_alert_create_parameterized(client, fake_conn):
    response = client.post(
        "/alerts",
        json={"name": "MRI watch", "query": {"q": "MRI"}, "scope": "matters",
              "frequency": "weekly"},
    )
    assert response.status_code == 201
    body = response.json()
    # alertId (matches web/src/lib/types.ts SavedAlert.alertId, not a bare "id").
    assert body["alertId"].startswith("mri-watch-")
    assert body["active"] is True
    assert body["query"] == {"q": "MRI"}

    sql, params = executed_with(fake_conn, "INSERT INTO con.saved_alert")[0]
    assert "MRI watch" not in sql and "MRI watch" in params
    assert json.dumps({"q": "MRI"}) in params
    assert fake_conn.committed == 1


def test_alert_delete_is_soft(client, fake_conn):
    response = client.delete("/alerts/mri-watch-abc123")
    assert response.status_code == 200
    assert response.json() == {"id": "mri-watch-abc123", "active": False}

    update_calls = executed_with(fake_conn, "UPDATE con.saved_alert SET active = 0")
    assert len(update_calls) == 1
    assert update_calls[0][1] == ("mri-watch-abc123",)
    assert not any("DELETE" in sql.upper() for sql in fake_conn.executed_sql())
    assert fake_conn.committed == 1


def test_alerts_list_defaults_to_active_only(client, fake_conn):
    fake_conn.script(
        "SELECT a.* FROM con.saved_alert a",
        rows=[("mri-watch-abc123", "matt@example.com", "MRI watch",
               json.dumps({"q": "MRI"}), "matters", "weekly", 1)],
        columns=["alert_id", "owner_upn", "name", "query_json", "scope", "frequency", "active"],
    )
    body = client.get("/alerts", params={"owner": "matt@example.com"}).json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == {"q": "MRI"}  # JSON parsed at the boundary
    # alertId (matches web/src/lib/types.ts SavedAlert.alertId); listAlerts() has
    # no renaming adapter, so the wire key must already be alertId, not "id".
    assert body["items"][0]["alertId"] == "mri-watch-abc123"
    assert "id" not in body["items"][0]
    sql, params = executed_with(fake_conn, "FROM con.saved_alert a")[0]
    assert "a.active = ?" in sql and "a.owner_upn = ?" in sql
    assert "matt@example.com" not in sql and params == (1, "matt@example.com")


# ---------------------------------------------------------------------------
# /wiki
# ---------------------------------------------------------------------------


def test_wiki_grouped_by_group_name(client, fake_conn):
    fake_conn.script(
        "FROM con.wiki_article w ORDER BY",
        rows=[
            ("con-overview", "Foundations", "CON Program Overview", "published", None),
            ("need-method", "Foundations", "Need Methodologies", "published", None),
            ("hb-1339", "Reform", "HB 1339 Changes", "draft", None),
        ],
        columns=["article_id", "group_name", "title", "status", "updated_at"],
    )
    body = client.get("/wiki").json()
    assert body["total"] == 3
    groups = {g["group"]: g["articles"] for g in body["groups"]}
    assert [a["id"] for a in groups["Foundations"]] == ["con-overview", "need-method"]
    assert groups["Reform"][0]["id"] == "hb-1339"


def test_wiki_revision_create_is_pending(client, fake_conn):
    fake_conn.script(
        "SELECT article_id FROM con.wiki_article", rows=[("con-overview",)],
        columns=["article_id"],
    )
    fake_conn.script("OUTPUT INSERTED.revision_id", rows=[(9,)], columns=["revision_id"])
    response = client.post(
        "/wiki/con-overview/revisions",
        json={"author": "matt@example.com", "diff": {"ops": [{"insert": "…"}]}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["revisionId"] == 9
    assert body["status"] == "pending"

    sql, params = executed_with(fake_conn, "INSERT INTO con.wiki_revision")[0]
    assert "matt@example.com" not in sql and "matt@example.com" in params
    assert "pending" in params
    assert json.dumps({"ops": [{"insert": "…"}]}) in params
    assert fake_conn.committed == 1


def test_wiki_review_approve_touches_article(client, fake_conn):
    fake_conn.script("SELECT status FROM con.wiki_revision", rows=[("pending",)],
                     columns=["status"])
    response = client.post(
        "/wiki/con-overview/revisions/5/review", json={"action": "approve"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "revisionId": 5, "articleId": "con-overview", "status": "approved"
    }
    sql, params = executed_with(fake_conn, "UPDATE con.wiki_revision SET status = ?")[0]
    assert params == ("approved", 5, "con-overview")
    touch_calls = executed_with(fake_conn, "UPDATE con.wiki_article SET updated_at")
    assert len(touch_calls) == 1 and touch_calls[0][1] == ("con-overview",)
    assert fake_conn.committed == 1


def test_wiki_review_reject_does_not_touch_article(client, fake_conn):
    fake_conn.script("SELECT status FROM con.wiki_revision", rows=[("pending",)],
                     columns=["status"])
    response = client.post(
        "/wiki/con-overview/revisions/5/review", json={"action": "reject"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    sql, params = executed_with(fake_conn, "UPDATE con.wiki_revision SET status = ?")[0]
    assert params == ("rejected", 5, "con-overview")
    assert executed_with(fake_conn, "UPDATE con.wiki_article") == []


def test_wiki_review_rejects_unknown_action(client, fake_conn):
    response = client.post(
        "/wiki/con-overview/revisions/5/review", json={"action": "maybe"}
    )
    assert response.status_code == 400
    assert fake_conn.executed == []


def test_wiki_review_unknown_revision_404(client, fake_conn):
    assert (
        client.post("/wiki/con-overview/revisions/99/review", json={"action": "approve"})
        .status_code == 404
    )


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


def test_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401
    assert "x-ms-client-principal" in response.json()["detail"]


def test_me_with_forged_header_returns_profile_and_inserts_app_user(client, fake_conn):
    headers = principal_headers(
        {
            "identityProvider": "aad",
            "userId": "swa-user-1",
            "userDetails": "matt@custerfucks.com",
            "userRoles": ["authenticated"],
            "claims": [
                {
                    "typ": "http://schemas.microsoft.com/identity/claims/objectidentifier",
                    "val": "oid-111",
                }
            ],
        }
    )
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": "oid-111",
        "upn": "matt@custerfucks.com",
        "email": "matt@custerfucks.com",
        "name": "matt@custerfucks.com",
        "provider": "aad",
        "roles": ["authenticated"],
    }

    select_calls = executed_with(fake_conn, "SELECT user_id FROM con.app_user")
    assert select_calls and select_calls[0][1] == ("oid-111",)
    insert_calls = executed_with(fake_conn, "INSERT INTO con.app_user")
    assert insert_calls
    assert insert_calls[0][1] == (
        "oid-111",
        "matt@custerfucks.com",
        "matt@custerfucks.com",
        "matt@custerfucks.com",
        "aad",
    )
    assert not executed_with(fake_conn, "UPDATE con.app_user")
    assert fake_conn.committed == 1


def test_me_updates_existing_app_user_row(client, fake_conn):
    fake_conn.script(
        "SELECT user_id FROM con.app_user", rows=[("oid-222",)], columns=["user_id"]
    )
    headers = principal_headers({"userId": "oid-222", "userDetails": "someone@example.com"})
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    update_calls = executed_with(fake_conn, "UPDATE con.app_user SET upn")
    assert update_calls and update_calls[0][1][-1] == "oid-222"
    assert not executed_with(fake_conn, "INSERT INTO con.app_user")
    assert fake_conn.committed == 1


# ---------------------------------------------------------------------------
# Server-authoritative ownership (/projects, /alerts)
# ---------------------------------------------------------------------------


def test_project_create_owner_stamped_from_principal_overrides_body(client, fake_conn):
    headers = principal_headers({"userId": "oid-333", "userDetails": "alice@example.com"})
    response = client.post(
        "/projects",
        json={"name": "Owner Stamp Project", "owner": "client-supplied@example.com"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["owner"] == "alice@example.com"

    sql, params = executed_with(fake_conn, "INSERT INTO con.research_project")[0]
    assert "alice@example.com" in params
    assert "client-supplied@example.com" not in params


def test_project_create_without_headers_honors_body_owner(client, fake_conn):
    response = client.post(
        "/projects", json={"name": "Unauthenticated Project", "owner": "bob@example.com"}
    )
    assert response.status_code == 201
    assert response.json()["owner"] == "bob@example.com"

    sql, params = executed_with(fake_conn, "INSERT INTO con.research_project")[0]
    assert "bob@example.com" in params


def test_alert_create_owner_stamped_from_principal_overrides_body(client, fake_conn):
    headers = principal_headers({"userId": "oid-444", "userDetails": "carol@example.com"})
    response = client.post(
        "/alerts",
        json={
            "name": "Owner Stamp Alert",
            "query": {"q": "NICU"},
            "scope": "matters",
            "frequency": "weekly",
            "owner": "client-supplied@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["owner"] == "carol@example.com"

    sql, params = executed_with(fake_conn, "INSERT INTO con.saved_alert")[0]
    assert "carol@example.com" in params
    assert "client-supplied@example.com" not in params
