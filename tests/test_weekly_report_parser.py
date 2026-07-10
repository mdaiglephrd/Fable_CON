"""Tests for ingest/weekly_report_parser.py.

The fixture-driven tests exercise the whole pipeline: reportlab-generated
synthetic PDF (tests/fixtures/sample_weekly_report.pdf) -> extract_text ->
parse_report_text. DB loading is tested against tests/fakes.py FakeConnection.
"""

import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ingest.weekly_report_parser import (
    ReportEvent,
    ReportParse,
    dedupe_hash,
    extract_text,
    load_events,
    parse_cost,
    parse_date,
    parse_report_text,
)
from tests.fakes import FakeConnection

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PDF = REPO_ROOT / "tests" / "fixtures" / "sample_weekly_report.pdf"
GENERATOR = REPO_ROOT / "tests" / "fixtures" / "make_weekly_report_fixture.py"

EXPECTED_COUNTS = {
    "LETTER_OF_INTENT": 3,
    "NEW_APPLICATION": 3,
    "WITHDRAWN_APPLICATION": 2,
    "PENDING_APPLICATION": 3,
    "APPROVED": 2,
    "DENIED": 2,
    "APPEALED": 2,
    "LETTER_OF_DETERMINATION": 2,
}


@pytest.fixture(scope="module")
def report_parse() -> ReportParse:
    if not FIXTURE_PDF.exists():
        subprocess.run([sys.executable, str(GENERATOR)], check=True, cwd=REPO_ROOT)
    text = extract_text(str(FIXTURE_PDF))
    return parse_report_text(text, report_file=FIXTURE_PDF.name)


def by_docket(parse: ReportParse, docket_id: str) -> ReportEvent:
    matches = [e for e in parse.events if e.docket_id == docket_id]
    assert len(matches) == 1, f"expected exactly one event for {docket_id}, got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# (a) Full pipeline against the fixture PDF
# ---------------------------------------------------------------------------


class TestFixtureParse:
    def test_report_date_found(self, report_parse):
        assert report_parse.report_date == date(2026, 6, 22)

    def test_all_eight_sections_present(self, report_parse):
        assert {e.section for e in report_parse.events} == set(EXPECTED_COUNTS)

    def test_entry_counts_per_section(self, report_parse):
        counts: dict[str, int] = {}
        for event in report_parse.events:
            counts[event.section] = counts.get(event.section, 0) + 1
        assert counts == EXPECTED_COUNTS

    def test_approved_entry_details(self, report_parse):
        event = by_docket(report_parse, "CON-2026-0187")
        assert event.section == "APPROVED"
        assert event.docket_raw == "CON2026-0187"  # as printed, compact form
        assert event.applicant == "Wellstar Health System, Inc."
        assert event.county == "Spalding"  # printed "SPALDING" -> Title Case
        assert event.cost == Decimal("4500000.00")  # printed "$4.5 million"
        assert event.filing_date == date(2026, 1, 12)
        assert event.decision_date == date(2026, 6, 18)  # "Approved: 06/18/2026"
        assert "Wellstar" in event.raw_text
        assert "Approved: 06/18/2026" in event.raw_text

    def test_lnr_docket_canonicalizes(self, report_parse):
        event = by_docket(report_parse, "LNR-2026-0012")
        assert event.section == "LETTER_OF_INTENT"
        assert event.docket_raw == "LNR 2026-0012"  # printed with a space

    def test_det_docket_canonicalizes(self, report_parse):
        event = by_docket(report_parse, "DET-2026-021")
        assert event.section == "LETTER_OF_DETERMINATION"
        assert event.docket_raw == "DET2026-021"  # printed compact
        assert event.decision_date == date(2026, 6, 19)

    def test_entry_without_docket(self, report_parse):
        no_docket = [e for e in report_parse.events if e.docket_id is None]
        assert len(no_docket) == 1
        event = no_docket[0]
        assert event.section == "LETTER_OF_INTENT"
        assert event.docket_raw is None
        assert event.applicant == "Georgia Cancer Care Partners, LLC"
        assert event.cost == Decimal("6200000.00")  # "$6.2 million"
        assert any("no recognizable docket" in w for w in report_parse.warnings)

    def test_county_from_labeled_field(self, report_parse):
        assert by_docket(report_parse, "CON-2026-0203").county == "Hall"

    def test_county_from_site_line(self, report_parse):
        # "Site: Macon, Bibb County" and "Site: Savannah, Chatham County"
        assert by_docket(report_parse, "CON-2026-0201").county == "Bibb"
        assert by_docket(report_parse, "CON-2026-0149").county == "Chatham"

    def test_date_forms_in_fixture(self, report_parse):
        event = by_docket(report_parse, "CON-2026-0201")
        assert event.filing_date == date(2026, 6, 16)  # "6/16/26"
        assert event.decision_deadline == date(2026, 10, 14)  # ISO "2026-10-14"

    def test_plain_comma_cost_form(self, report_parse):
        assert by_docket(report_parse, "CON-2026-0201").cost == Decimal("1234567.00")

    def test_opposition_kept_as_printed(self, report_parse):
        event = by_docket(report_parse, "CON-2026-0195")
        assert event.opposition == "Opposed by Piedmont Healthcare"

    def test_unlabeled_remainder_becomes_description(self, report_parse):
        event = by_docket(report_parse, "LNR-2026-0015")
        assert event.project_description is not None
        assert event.project_description.startswith(
            "Letter of intent to add 12 skilled nursing beds"
        )

    def test_missing_cost_is_none(self, report_parse):
        assert by_docket(report_parse, "LNR-2026-0015").cost is None


# ---------------------------------------------------------------------------
# (b) Cost parsing
# ---------------------------------------------------------------------------


class TestParseCost:
    def test_comma_separated(self):
        assert parse_cost("$1,234,567") == Decimal("1234567.00")

    def test_million_word_form(self):
        assert parse_cost("$4.5 million") == Decimal("4500000.00")

    def test_cents(self):
        assert parse_cost("$950,000.00") == Decimal("950000.00")

    def test_m_suffix(self):
        assert parse_cost("$1.2M") == Decimal("1200000.00")

    def test_bare_number(self):
        assert parse_cost("1,234,567") == Decimal("1234567.00")

    def test_absent(self):
        assert parse_cost(None) is None
        assert parse_cost("") is None
        assert parse_cost("TBD") is None


# ---------------------------------------------------------------------------
# (c) Date parsing
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_long_form(self):
        assert parse_date("June 22, 2026") == date(2026, 6, 22)

    def test_abbreviated_month(self):
        assert parse_date("Jun. 22, 2026") == date(2026, 6, 22)

    def test_slash_four_digit_year(self):
        assert parse_date("06/22/2026") == date(2026, 6, 22)

    def test_slash_two_digit_year(self):
        assert parse_date("6/22/26") == date(2026, 6, 22)

    def test_iso(self):
        assert parse_date("2026-06-22") == date(2026, 6, 22)

    def test_embedded_in_text(self):
        assert parse_date("approved on June 5, 2026 by the department") == date(2026, 6, 5)

    def test_absent(self):
        assert parse_date(None) is None
        assert parse_date("") is None
        assert parse_date("pending") is None


# ---------------------------------------------------------------------------
# (d) dedupe_hash
# ---------------------------------------------------------------------------


class TestDedupeHash:
    def test_stable_hex(self):
        a = dedupe_hash(date(2026, 6, 22), "APPROVED", "CON-1234567", "raw text")
        b = dedupe_hash(date(2026, 6, 22), "APPROVED", "CON-1234567", "raw text")
        assert a == b
        assert len(a) == 64
        assert int(a, 16)  # valid hex

    def test_sensitive_to_inputs(self):
        base = dedupe_hash(date(2026, 6, 22), "APPROVED", "CON-1234567", "raw text")
        assert dedupe_hash(date(2026, 6, 22), "DENIED", "CON-1234567", "raw text") != base
        assert dedupe_hash(date(2026, 6, 29), "APPROVED", "CON-1234567", "raw text") != base
        assert dedupe_hash(date(2026, 6, 22), "APPROVED", None, "raw text") != base
        assert dedupe_hash(date(2026, 6, 22), "APPROVED", "CON-1234567", "other") != base

    def test_none_report_date_and_docket(self):
        a = dedupe_hash(None, "APPROVED", None, "raw text")
        assert a == dedupe_hash(None, "APPROVED", None, "raw text")
        assert len(a) == 64


# ---------------------------------------------------------------------------
# (e) load_events with FakeConnection
# ---------------------------------------------------------------------------


def make_event(**overrides) -> ReportEvent:
    base = dict(
        section="NEW_APPLICATION",
        docket_raw="CON1234567",
        docket_id="CON-1234567",
        applicant="Applicant A, Inc.",
        project_description="Establish a thing",
        county="Fulton",
        cost=Decimal("1000000.00"),
        opposition=None,
        filing_date=date(2026, 6, 15),
        decision_deadline=date(2026, 10, 13),
        decision_date=None,
        raw_text="CON1234567\nApplicant: Applicant A, Inc.",
    )
    base.update(overrides)
    return ReportEvent(**base)


def make_parse() -> ReportParse:
    return ReportParse(
        report_date=date(2026, 6, 22),
        events=[
            make_event(),
            make_event(
                section="LETTER_OF_INTENT",
                docket_raw=None,
                docket_id=None,
                applicant="No Docket, LLC",
                raw_text="Project No.: Pending assignment",
            ),
        ],
        warnings=[],
    )


class TestLoadEvents:
    def test_inserts_events_and_stub_matter(self):
        conn = FakeConnection()
        stats = load_events(conn, make_parse(), "wr-2026-06-22.pdf")

        assert stats.inserted == 2
        assert stats.skipped_duplicates == 0
        assert stats.stub_matters_created == 1

        sqls = conn.executed_sql()
        matter_inserts = [
            (sql, params)
            for sql, params in conn.executed
            if sql.startswith("INSERT INTO con.matter (")
        ]
        assert len(matter_inserts) == 1
        sql, params = matter_inserts[0]
        assert "WHERE NOT EXISTS" in sql  # insert-if-missing guard, never UPDATE
        assert params == ("CON-1234567", '["stub_from_weekly_report"]', "CON-1234567")

        # Docket variants inserted if missing (CON1234567 + CON-1234567).
        variant_inserts = [
            params
            for sql, params in conn.executed
            if sql.startswith("INSERT INTO con.matter_docket_variant")
        ]
        assert {p[1] for p in variant_inserts} == {"CON-1234567", "CON1234567"}
        assert all("WHERE NOT EXISTS" in sql for sql in sqls if sql.startswith("INSERT INTO con.matter"))

        event_inserts = [
            params
            for sql, params in conn.executed
            if sql.startswith("INSERT INTO con.weekly_report_event")
        ]
        assert len(event_inserts) == 2
        # (report_date, report_file, section, docket_id, docket_raw, ...)
        assert event_inserts[0][0] == date(2026, 6, 22)
        assert event_inserts[0][1] == "wr-2026-06-22.pdf"
        assert event_inserts[0][3] == "CON-1234567"
        assert event_inserts[1][3] is None  # docket-less event still inserted
        assert event_inserts[1][4] is None
        assert len(event_inserts[0][-1]) == 64  # dedupe_hash param

        assert not any(sql.strip().upper().startswith("UPDATE") for sql in sqls)
        assert conn.committed == 1

    def test_dedupe_select_guard_skips_existing_events(self):
        conn = FakeConnection()
        # Every dedupe guard SELECT finds a row -> both events are duplicates.
        conn.script("SELECT 1 FROM con.weekly_report_event WHERE dedupe_hash", rows=[(1,)])
        stats = load_events(conn, make_parse(), "wr.pdf")

        assert stats.inserted == 0
        assert stats.skipped_duplicates == 2
        assert stats.stub_matters_created == 0
        assert not any(
            sql.startswith("INSERT INTO con.weekly_report_event") for sql in conn.executed_sql()
        )
        assert conn.committed == 1

    def test_existing_matter_not_recreated(self):
        conn = FakeConnection()
        conn.script("SELECT 1 FROM con.matter WHERE docket_id", rows=[(1,)])
        conn.script("SELECT 1 FROM con.matter_docket_variant WHERE", rows=[(1,)])
        stats = load_events(conn, make_parse(), "wr.pdf")

        assert stats.inserted == 2
        assert stats.stub_matters_created == 0
        sqls = conn.executed_sql()
        assert not any(sql.startswith("INSERT INTO con.matter (") for sql in sqls)
        assert not any(sql.startswith("INSERT INTO con.matter_docket_variant") for sql in sqls)

    def test_duplicate_docket_events_create_one_stub(self):
        parse = ReportParse(
            report_date=date(2026, 6, 22),
            events=[
                make_event(raw_text="first entry"),
                make_event(section="APPROVED", raw_text="second entry, same docket"),
            ],
            warnings=[],
        )
        conn = FakeConnection()
        stats = load_events(conn, parse, "wr.pdf")
        assert stats.inserted == 2
        assert stats.stub_matters_created == 1

    def test_missing_report_date_raises(self):
        conn = FakeConnection()
        parse = ReportParse(report_date=None, events=[make_event()], warnings=["no date"])
        with pytest.raises(ValueError):
            load_events(conn, parse, "wr.pdf")
        assert conn.committed == 0
