"""Tests for ingest/weekly_report_parser.py.

The fixture-driven tests exercise the whole pipeline: reportlab-generated
synthetic PDF (tests/fixtures/sample_weekly_report.pdf, mimicking the REAL
DCH report layout of 2026-04-21) -> extract_text -> parse_report_text.
The TestRealReportFragments class parses small literal text fragments copied
from the real report (the PDF itself is not committed). DB loading is tested
against tests/fakes.py FakeConnection.
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
    bare_con_docket,
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
    "LETTER_OF_INTENT": 2,
    "PENDING_APPLICATION": 2,
    "APPEALED_DETERMINATION": 2,
    "APPEALED": 2,
    "LETTER_OF_DETERMINATION": 5,
    "EXTENDED_IMPLEMENTATION": 1,
}
# Sections present in the fixture as headings but containing only "none" (or
# informational prose) — they must emit no events.
EMPTY_SECTIONS = {
    "LOI_EXPIRED",
    "NEW_APPLICATION",
    "WITHDRAWN_APPLICATION",
    "APPROVED",
    "DENIED",
    "DISQUALIFIED",
    "DET_REVIEW",
    "LNR_CONVERSION",
    "OTHER",
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
# (a) Full pipeline against the fixture PDF (real-layout mimic)
# ---------------------------------------------------------------------------


class TestFixtureParse:
    def test_report_date_is_range_end(self, report_parse):
        # "April 15, 2026 – April 21, 2026" on the TOC page -> the END date.
        assert report_parse.report_date == date(2026, 4, 21)

    def test_entry_counts_per_section(self, report_parse):
        counts: dict[str, int] = {}
        for event in report_parse.events:
            counts[event.section] = counts.get(event.section, 0) + 1
        assert counts == EXPECTED_COUNTS

    def test_none_sections_emit_no_events(self, report_parse):
        assert not {e.section for e in report_parse.events} & EMPTY_SECTIONS

    def test_pending_application_entry(self, report_parse):
        event = by_docket(report_parse, "CON-2026002")  # bare "2026-002"
        assert event.section == "PENDING_APPLICATION"
        assert event.section_heading == "Pending Review Applications"
        assert event.docket_raw == "2026-002"
        assert event.applicant == "John D. Archbold Memorial Hospital, Inc."
        assert event.county == "Thomas"  # "Site: ... GA31792 (Thomas County)"
        assert event.cost == Decimal("6945132.00")
        assert event.opposition == "OPPOSITION FILED"
        assert "OPPOSITION" not in (event.project_description or "")
        assert event.project_description.startswith("Establishment ofAdult Open Heart")
        assert event.filing_date == date(2026, 2, 5)  # "Filed: ... Deemed Complete: ..."
        assert event.decision_deadline == date(2026, 6, 4)
        assert event.decision_date is None

    def test_second_pending_entry_glued_labels(self, report_parse):
        event = by_docket(report_parse, "CON-2026003")
        assert event.county == "Gwinnett"
        assert event.cost == Decimal("1015000.00")
        assert event.opposition == "OPPOSITION FILED"
        assert event.filing_date == date(2026, 2, 24)
        assert event.decision_deadline == date(2026, 6, 23)

    def test_appealed_determination_narrative(self, report_parse):
        event = by_docket(report_parse, "DET-EQT-2024-073")
        assert event.section == "APPEALED_DETERMINATION"
        assert event.docket_raw == "DET-EQT2024-073"
        assert event.applicant == "MDS Imaging, Inc."
        # "received on 7/2/2024, regarding acquisition of\nmobile MRI unit."
        assert event.filing_date == date(2024, 7, 2)
        assert event.project_description == "acquisition of mobile MRI unit"
        # "Agency Decision: Deniedon12/6/2024" (glued)
        assert event.decision_date == date(2024, 12, 6)
        # "Superior Court ofFulton County:" must not be read as a county.
        assert event.county is None
        assert "Superior Court ofFulton County" in event.raw_text

    def test_second_narrative_received_date_wraps_lines(self, report_parse):
        event = by_docket(report_parse, "DET-2025-036")
        assert event.applicant == "Crowning Moments Birth and Wellness Center, LLC"
        assert event.filing_date == date(2025, 4, 3)  # date on the wrapped line
        assert event.decision_date == date(2025, 5, 28)

    def test_appealed_con_project_spans_page_break(self, report_parse):
        event = by_docket(report_parse, "CON-2020020")
        assert event.section == "APPEALED"
        assert event.applicant == "University Hospital"
        assert event.county == "Columbia"  # "(Columbia)" after the applicant
        assert event.decision_date == date(2020, 7, 21)  # "Approved, 7/21/2020"
        # The entry continues past the page break (glued page number stripped).
        assert "withdraws CON 2020-023" in event.raw_text

    def test_midline_docket_does_not_split_entry(self, report_parse):
        # "... withdraws CON 2020-023, 12/4/2024." mid-narrative must not
        # start a new entry or emit a phantom event.
        assert not [e for e in report_parse.events if e.docket_id == "CON-2020-023"]
        assert sum(1 for e in report_parse.events if e.section == "APPEALED") == 2

    def test_det_eqt_request_entry(self, report_parse):
        event = by_docket(report_parse, "DET-EQT-2026002")
        assert event.section == "LETTER_OF_DETERMINATION"
        assert event.section_heading == "Requests for DET-EQT for Diagnostic or Therapeutic Equipment"
        assert event.applicant == "Women'sImaging Specialists - Gwinnett, LLC"
        assert event.project_description == "Acquisition ofMRI"
        assert event.filing_date == date(2026, 1, 6)  # "Request received:"
        # "Determination: Denied Determination Date: 4/20/2026" (two labels)
        assert event.decision_date == date(2026, 4, 20)

    def test_withdrawal_date_glued_label(self, report_parse):
        event = by_docket(report_parse, "DET-EQT-2026014")
        assert event.decision_date == date(2026, 3, 27)  # "DateofWithdrawal:"

    def test_det_asc_request_entry(self, report_parse):
        event = by_docket(report_parse, "DET-ASC-2026001")
        assert event.section == "LETTER_OF_DETERMINATION"
        assert event.cost == Decimal("982754.66")  # "Project costsassubmitted:"
        assert event.filing_date == date(2026, 1, 14)
        assert event.decision_date is None  # "Determination: Pending"
        assert "Single Specialty Ambulatory Surgery Center" in event.project_description

    def test_misc_determination_entry(self, report_parse):
        event = by_docket(report_parse, "DET-2024246")
        assert event.section_heading == "Requests for Miscellaneous Letters of Determination"
        assert event.applicant == "Middle Georgia Midwives"
        assert event.decision_date == date(2026, 4, 6)

    def test_extended_implementation_entry(self, report_parse):
        event = by_docket(report_parse, "CON-2023013")  # undashed "2023013"
        assert event.section == "EXTENDED_IMPLEMENTATION"
        assert event.docket_raw == "2023013"
        assert event.county == "Muscogee"  # "Columbus ( Muscogee)"
        assert event.cost == Decimal("45840002.00")  # "Approved Cost:"
        assert event.filing_date == date(2026, 3, 13)  # "Request Received:"
        # "Determination: Approved, 4/9/2026 Extended Mandatory Completion:
        # July 21, 2026" — the determination date, not the completion date.
        assert event.decision_date == date(2026, 4, 9)

    def test_loi_entries_and_glued_heading(self, report_parse):
        # Heading arrives as "IMPORTANT NOTICESLetters of Intent" (page glue).
        event = by_docket(report_parse, "LNR-2026-0012")
        assert event.section == "LETTER_OF_INTENT"
        assert event.section_heading == "Letters of Intent"
        assert event.county == "Fulton"
        assert event.filing_date == date(2026, 4, 16)

    def test_entry_without_docket(self, report_parse):
        no_docket = [e for e in report_parse.events if e.docket_id is None]
        assert len(no_docket) == 1
        event = no_docket[0]
        assert event.section == "LETTER_OF_INTENT"
        assert event.docket_raw is None
        assert event.applicant == "Georgia Cancer Care Partners, LLC"
        assert event.county == "Houston"
        assert any("no recognizable docket" in w for w in report_parse.warnings)

    def test_no_unexplained_warnings(self, report_parse):
        # The single expected warning is the deliberately docket-less entry.
        assert len(report_parse.warnings) == 1


# ---------------------------------------------------------------------------
# Regression tests: literal fragments from the real report of 2026-04-21
# (small parse_report_text cases; the real PDF itself is not committed).
# ---------------------------------------------------------------------------

REAL_PENDING_FRAGMENT = """Pending Review Applications
2026-006 Grady Memorial Hospital Corporation d/b/aGrady Health System
Construction ofaNew 200-Bed Short-Stay General Acute Care Hospital
Filed: 4/14/2026 Deemed Complete: 4/16/2026
30thDayDeadline: 5/13/2026
Decision Deadline: 8/11/2026
Site: 5500Campbellton Fairburn Road, UnionCity, GA30213 (Fulton County)
Contact: Shannon Sale, Chief Administrative Officer 404-616-7029
Estimated Cost: $924,793,000
"""

REAL_APPEALED_DETERMINATION_FRAGMENT = """Appealed Determinations
DET-EQT2022-035 Allegiance Imaging and Radiology, LLC Request forLetter ofDetermination received on 4/5/2022,
regarding additional locations for mobile MRI.
Agency Decision: Denied on7/27/2022
Appealed: Allegiance Imaging and Radiology, LLC (“Allegiance”) files Request for Administrative Appeal on8/19/2022.
HearingOfficer: MelvinM. Goldstein, Esq.
HearingDate: Pending
"""

REAL_APPEALED_CON_FRAGMENT = """Appealed CON Projects
2020-023 AU Medical Center, Inc. (Richmond)
Establish aFreestanding Emergency Care Facility as aDepartment ofAUMedical Center, Inc
Agency Decision: Approved, 7/28/2020
Appealed By: Doctors Hospital ofAugusta, LLC d/b/aDoctors Hospital ofAugusta (“Doctors”), 8/27/2020. University
Health Services, Inc. (“University”), 9/3/2020. AU Medical Center, Inc. withdraws CON 2020-023, 12/4/2024.
HearingOfficer: DavidC. Will, Esq.
HearingDate: Continued untilfurthernotice
"""

REAL_EXTENDED_FRAGMENT = """Requests for Extended Implementation/Effective Period
2023064 Piedmont Community Imaging, LLC d/b/aPiedmont Community Imaging at Marietta
Establishment of Freestanding Imaging Center
Request to Extend Completion Period
Site: 660 Cherokee Street, Marietta (Cobb)
Project Approved: 2/27/2024
Request Received: 3/30/2026
Contact: Michelle Fisher, President, Retail Svs. (404-831-2320)
Approved Cost: $5,183,196
Determination: Approved, 4/9/2026 Extended Mandatory Completion: October 24, 2026
"""


class TestRealReportFragments:
    def test_pending_application(self):
        parse = parse_report_text(REAL_PENDING_FRAGMENT)
        assert len(parse.events) == 1
        e = parse.events[0]
        assert e.section == "PENDING_APPLICATION"
        assert e.docket_id == "CON-2026006"
        assert e.docket_raw == "2026-006"
        assert e.applicant == "Grady Memorial Hospital Corporation d/b/aGrady Health System"
        assert e.county == "Fulton"
        assert e.cost == Decimal("924793000.00")
        assert e.opposition is None  # no OPPOSITION FILED marker
        assert e.filing_date == date(2026, 4, 14)
        assert e.decision_deadline == date(2026, 8, 11)

    def test_appealed_determination_narrative(self):
        parse = parse_report_text(REAL_APPEALED_DETERMINATION_FRAGMENT)
        assert len(parse.events) == 1
        e = parse.events[0]
        assert e.section == "APPEALED_DETERMINATION"
        assert e.docket_id == "DET-EQT-2022-035"
        assert e.applicant == "Allegiance Imaging and Radiology, LLC"
        assert e.filing_date == date(2022, 4, 5)  # "received on 4/5/2022"
        assert e.decision_date == date(2022, 7, 27)  # "Denied on7/27/2022"
        assert e.project_description == "additional locations for mobile MRI"

    def test_appealed_con_project_midline_docket(self):
        parse = parse_report_text(REAL_APPEALED_CON_FRAGMENT)
        assert len(parse.events) == 1  # "withdraws CON 2020-023" does not split
        e = parse.events[0]
        assert e.section == "APPEALED"
        assert e.docket_id == "CON-2020023"
        assert e.applicant == "AU Medical Center, Inc."
        assert e.county == "Richmond"
        assert e.decision_date == date(2020, 7, 28)

    def test_extended_implementation(self):
        parse = parse_report_text(REAL_EXTENDED_FRAGMENT)
        assert len(parse.events) == 1
        e = parse.events[0]
        assert e.section == "EXTENDED_IMPLEMENTATION"
        assert e.docket_id == "CON-2023064"
        assert e.county == "Cobb"  # "Marietta (Cobb)"
        assert e.cost == Decimal("5183196.00")
        assert e.filing_date == date(2026, 3, 30)
        assert e.decision_date == date(2026, 4, 9)  # not the completion date

    def test_report_date_range_and_glued_page_number(self):
        text = (
            "See the links below for easy navigation\n"
            "April 15, 2026 – April 21, 2026\n"
            "\f2Recently Denied Applications\n"
            "2026-099 Example Hospital, Inc.\n"
            "Some project description\n"
            "Filed: 1/2/2026\n"
        )
        parse = parse_report_text(text)
        assert parse.report_date == date(2026, 4, 21)
        assert len(parse.events) == 1
        assert parse.events[0].section == "DENIED"
        assert parse.events[0].docket_id == "CON-2026099"


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
        assert parse_cost("$982,754.66") == Decimal("982754.66")

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

    def test_glued_slash_date(self):
        assert parse_date("Deniedon12/6/2024") == date(2024, 12, 6)
        assert parse_date("Denied on7/27/2022") == date(2022, 7, 27)

    def test_glued_month_name(self):
        assert parse_date("onApril 15, 2026") == date(2026, 4, 15)

    def test_earliest_date_wins(self):
        raw = "Approved, 4/9/2026 Extended Mandatory Completion: July 21, 2026"
        assert parse_date(raw) == date(2026, 4, 9)

    def test_embedded_in_text(self):
        assert parse_date("approved on June 5, 2026 by the department") == date(2026, 6, 5)

    def test_absent(self):
        assert parse_date(None) is None
        assert parse_date("") is None
        assert parse_date("Pending") is None


# ---------------------------------------------------------------------------
# (c2) Bare year-seq CON docket rule (parser-level)
# ---------------------------------------------------------------------------


class TestBareConDocket:
    def test_dashed_form(self):
        dm = bare_con_docket("2026-002 John D. Archbold Memorial Hospital, Inc.")
        assert dm is not None
        assert dm.canonical == "CON-2026002"
        assert dm.raw == "2026-002"
        assert "2026-002" in dm.variants
        assert "CON2026002" in dm.variants

    def test_undashed_form(self):
        dm = bare_con_docket("2023013 The Medical Center, Inc.")
        assert dm is not None
        assert dm.canonical == "CON-2023013"
        assert dm.raw == "2023013"

    def test_glued_applicant(self):
        dm = bare_con_docket("2021-010South GeorgiaCenter forCancerCare (Bulloch)")
        assert dm is not None
        assert dm.canonical == "CON-2021010"

    def test_non_dockets(self):
        assert bare_con_docket("2030 Non-Special MRT Need Projection") is None
        assert bare_con_docket("2 Martin Luther King Jr. Drive SE") is None
        assert bare_con_docket("April 15, 2026") is None


# ---------------------------------------------------------------------------
# (d) dedupe_hash
# ---------------------------------------------------------------------------


class TestDedupeHash:
    def test_stable_hex(self):
        a = dedupe_hash(date(2026, 4, 21), "APPROVED", "CON-1234567", "raw text")
        b = dedupe_hash(date(2026, 4, 21), "APPROVED", "CON-1234567", "raw text")
        assert a == b
        assert len(a) == 64
        assert int(a, 16)  # valid hex

    def test_sensitive_to_inputs(self):
        base = dedupe_hash(date(2026, 4, 21), "APPROVED", "CON-1234567", "raw text")
        assert dedupe_hash(date(2026, 4, 21), "DENIED", "CON-1234567", "raw text") != base
        assert dedupe_hash(date(2026, 4, 28), "APPROVED", "CON-1234567", "raw text") != base
        assert dedupe_hash(date(2026, 4, 21), "APPROVED", None, "raw text") != base
        assert dedupe_hash(date(2026, 4, 21), "APPROVED", "CON-1234567", "other") != base

    def test_none_report_date_and_docket(self):
        a = dedupe_hash(None, "APPROVED", None, "raw text")
        assert a == dedupe_hash(None, "APPROVED", None, "raw text")
        assert len(a) == 64


# ---------------------------------------------------------------------------
# (e) load_events with FakeConnection
# ---------------------------------------------------------------------------


def make_event(**overrides) -> ReportEvent:
    base = dict(
        section="PENDING_APPLICATION",
        section_heading="Pending Review Applications",
        docket_raw="2026-002",
        docket_id="CON-2026002",
        applicant="Applicant A, Inc.",
        project_description="Establish a thing",
        county="Fulton",
        cost=Decimal("1000000.00"),
        opposition=None,
        filing_date=date(2026, 2, 5),
        decision_deadline=date(2026, 6, 4),
        decision_date=None,
        raw_text="2026-002 Applicant A, Inc.\nEstablish a thing",
    )
    base.update(overrides)
    return ReportEvent(**base)


def make_parse() -> ReportParse:
    return ReportParse(
        report_date=date(2026, 4, 21),
        events=[
            make_event(),
            make_event(
                section="LETTER_OF_INTENT",
                section_heading="Letters of Intent",
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
        stats = load_events(conn, make_parse(), "wr-2026-04-21.pdf")

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
        assert params == ("CON-2026002", '["stub_from_weekly_report"]', "CON-2026002")

        # Docket variants inserted if missing (bare printed form included).
        variant_inserts = [
            params
            for sql, params in conn.executed
            if sql.startswith("INSERT INTO con.matter_docket_variant")
        ]
        assert {p[1] for p in variant_inserts} == {"2026-002", "CON-2026002", "CON2026002"}
        assert all("WHERE NOT EXISTS" in sql for sql in sqls if sql.startswith("INSERT INTO con.matter"))

        event_inserts = [
            params
            for sql, params in conn.executed
            if sql.startswith("INSERT INTO con.weekly_report_event")
        ]
        assert len(event_inserts) == 2
        # (report_date, report_file, section, section_heading, docket_id, docket_raw, ...)
        assert event_inserts[0][0] == date(2026, 4, 21)
        assert event_inserts[0][1] == "wr-2026-04-21.pdf"
        assert event_inserts[0][2] == "PENDING_APPLICATION"
        assert event_inserts[0][3] == "Pending Review Applications"
        assert event_inserts[0][4] == "CON-2026002"
        assert event_inserts[0][5] == "2026-002"
        assert event_inserts[1][4] is None  # docket-less event still inserted
        assert event_inserts[1][5] is None
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
            report_date=date(2026, 4, 21),
            events=[
                make_event(raw_text="first entry"),
                make_event(section="APPEALED", raw_text="second entry, same docket"),
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
