import json
from datetime import date, datetime

import pytest

from ingest.load_tags import (
    DOCUMENT_MERGE_SQL,
    MATTER_MERGE_SQL,
    LoadStats,
    RowRejected,
    load_rows,
    shape_row,
)
from tests.fakes import FakeConnection


def full_row(**overrides) -> dict:
    """A CSV-style row (all values strings) exercising every field."""
    row = {
        "entry_id": "12345",
        "docket_id": "Docket No. CON-1234567",
        "docket_variants": "GA-1234567; CON1234567",
        "applicant": "Acme Health System",
        "facility": "Acme Hospital",
        "matter_type": "CON Application",
        "action_type": "New service/facility",
        "county": "fulton",
        "service_area": "Region 3",
        "bed_count": "24",
        "year_filed": "2021",
        "final_outcome": "Approved",
        "final_decision_date": "2022-03-01",
        "highest_review_level": "2",
        "completeness_flags": "stub_from_weekly_report",
        "service_type": "PET; MRI",
        "phases_present": "Initial Application; Administrative Appeal",
        "docview_url": "",
        "file_name": "Final Order CON-1234567.pdf",
        "doc_type": "Final Agency Decision",
        "decision_level": "1",
        "phase": "Initial Application",
        "page_count": "12",
        "repo_date_created": "2021-06-01T08:30:00",
        "repo_date_modified": "6/2/2021 09:15",
        "doc_date": "7/4/2021",
        "decision_maker": "Hearing Officer Smith",
        "outcome": "approved",
        "parties": "Acme Health System; Rival Health",
        "source_path": "\\\\repo\\CON\\1234567",
        "template_name": "CON Document",
        "ocr_status": "complete",
        "ocr_confidence": "97.5",
        "validation_status": "Validated",
        "validated_by": "matt",
        "validated_date": "2024-01-02T03:04:05",
        "duplicate_of": "",
    }
    row.update(overrides)
    return row


class TestShapeRowHappyPath:
    def test_keys_and_docket(self):
        shaped = shape_row(full_row())
        assert shaped.entry_id == 12345
        assert shaped.docket_id == "CON-1234567"
        assert shaped.document["docket_id"] == "CON-1234567"

    def test_matter_fields(self):
        shaped = shape_row(full_row())
        m = shaped.matter
        assert m["applicant"] == "Acme Health System"
        assert m["county"] == "Fulton"  # canonicalized
        assert m["bed_count"] == 24
        assert m["year_filed"] == 2021
        assert m["final_outcome"] == "Approved"
        assert m["final_decision_date"] == date(2022, 3, 1)
        assert m["highest_review_level"] == 2
        assert json.loads(m["completeness_flags"]) == ["stub_from_weekly_report"]

    def test_document_fields(self):
        shaped = shape_row(full_row())
        d = shaped.document
        assert d["doc_type"] == "Final Agency Decision"
        assert d["decision_level"] == 1
        assert d["page_count"] == 12
        assert d["outcome"] == "Approved"  # vocab match is case-tolerant
        assert d["ocr_confidence"] == pytest.approx(97.5)
        assert d["validation_status"] == "Validated"
        assert d["validated_date"] == datetime(2024, 1, 2, 3, 4, 5)
        assert d["duplicate_of"] is None  # blank -> None
        assert json.loads(d["parties"]) == ["Acme Health System", "Rival Health"]

    def test_missing_optional_fields_are_none(self):
        shaped = shape_row({"entry_id": "7", "docket_id": "CON-1234567"})
        assert shaped.matter["applicant"] is None
        assert shaped.matter["completeness_flags"] is None
        assert shaped.document["doc_type"] is None
        assert shaped.document["parties"] is None
        assert shaped.document["validation_status"] is None  # loader applies default
        assert shaped.service_types == ()
        assert shaped.phases == ()


class TestDocketNormalization:
    def test_variant_input_normalizes_to_canonical(self):
        shaped = shape_row({"entry_id": "1", "docket_id": "con 1234567"})
        assert shaped.docket_id == "CON-1234567"

    def test_ga_legacy_maps_to_con(self):
        shaped = shape_row({"entry_id": "1", "docket_id": "GA-1234567"})
        assert shaped.docket_id == "CON-1234567"
        assert "GA-1234567" in shaped.docket_variants

    def test_variants_union_column_and_match(self):
        shaped = shape_row(full_row())
        for v in ("CON-1234567", "CON1234567", "GA-1234567"):
            assert v in shaped.docket_variants

    def test_json_style_variant_list(self):
        shaped = shape_row(
            {"entry_id": 1, "docket_id": "CON-1234567", "docket_variants": ["04-21-003"]}
        )
        assert "04-21-003" in shaped.docket_variants

    def test_unnormalizable_docket_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row({"entry_id": "1", "docket_id": "hello world"}, row_number=3)
        assert exc.value.error.field == "docket_id"
        assert exc.value.error.row_number == 3
        assert exc.value.error.raw_value == "hello world"

    def test_missing_docket_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row({"entry_id": "1"})
        assert exc.value.error.field == "docket_id"


class TestEntryId:
    def test_missing_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row({"docket_id": "CON-1234567"})
        assert exc.value.error.field == "entry_id"

    def test_non_integer_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row({"entry_id": "abc", "docket_id": "CON-1234567"})
        assert exc.value.error.field == "entry_id"
        assert exc.value.error.raw_value == "abc"

    def test_json_int_accepted(self):
        assert shape_row({"entry_id": 42, "docket_id": "CON-1234567"}).entry_id == 42


class TestVocabRejection:
    @pytest.mark.parametrize(
        "field_name",
        [
            "matter_type",
            "action_type",
            "doc_type",
            "phase",
            "outcome",
            "final_outcome",
        ],
    )
    def test_invalid_vocab_names_field(self, field_name):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(**{field_name: "Totally Bogus Value"}), row_number=9)
        assert exc.value.error.field == field_name
        assert exc.value.error.row_number == 9
        assert exc.value.error.raw_value == "Totally Bogus Value"

    def test_unknown_validation_status_falls_back_to_default_with_warning(self, caplog):
        # validation_status is loader-owned workflow state, not source metadata:
        # real exports contain values like "Provisional", which mean "not yet
        # validated here" — the row loads with the default status, not a reject.
        with caplog.at_level("WARNING", logger="ingest.load_tags"):
            shaped = shape_row(full_row(validation_status="Provisional"), row_number=9)
        assert shaped.document["validation_status"] is None  # loader applies --default-status
        assert any("Provisional" in r.message for r in caplog.records)

    def test_export_form_decision_level_and_slash_spacing(self):
        # Real export forms: "1 Desk Decision" and "Decision / Determination".
        shaped = shape_row(
            full_row(
                decision_level="1 Desk Decision",
                highest_review_level="4 Appellate Court Decision",
                doc_type="Decision / Determination",
            )
        )
        assert shaped.document["decision_level"] == 1
        assert shaped.matter["highest_review_level"] == 4
        assert shaped.document["doc_type"] == "Decision/Determination"

    def test_decision_level_label_mismatch_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(decision_level="1 Hearing Officer Decision"))
        assert exc.value.error.field == "decision_level"

    def test_invalid_service_type_in_list_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(service_type="PET; Bogus Modality"))
        assert exc.value.error.field == "service_type"

    def test_invalid_phases_present_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(phases_present="Initial Application; Phase 9"))
        assert exc.value.error.field == "phases_present"

    def test_invalid_county_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(county="Springfield"))
        assert exc.value.error.field == "county"

    def test_invalid_decision_level_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(decision_level="9"))
        assert exc.value.error.field == "decision_level"


class TestParsing:
    def test_us_date(self):
        shaped = shape_row(full_row(doc_date="7/4/2021"))
        assert shaped.document["doc_date"] == date(2021, 7, 4)

    def test_iso_date(self):
        shaped = shape_row(full_row(doc_date="2021-07-04"))
        assert shaped.document["doc_date"] == date(2021, 7, 4)

    def test_iso_datetime(self):
        shaped = shape_row(full_row(repo_date_created="2021-06-01T08:30:00"))
        assert shaped.document["repo_date_created"] == datetime(2021, 6, 1, 8, 30)

    def test_us_datetime(self):
        shaped = shape_row(full_row(repo_date_modified="6/2/2021 09:15"))
        assert shaped.document["repo_date_modified"] == datetime(2021, 6, 2, 9, 15)

    def test_bad_date_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(doc_date="sometime in July"))
        assert exc.value.error.field == "doc_date"

    def test_bad_int_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(page_count="twelve"))
        assert exc.value.error.field == "page_count"

    def test_bad_float_rejects(self):
        with pytest.raises(RowRejected) as exc:
            shape_row(full_row(ocr_confidence="high"))
        assert exc.value.error.field == "ocr_confidence"


class TestMultiValue:
    def test_csv_semicolon_split(self):
        shaped = shape_row(full_row())
        assert shaped.service_types == ("PET", "MRI")
        assert shaped.phases == ("Initial Application", "Administrative Appeal")

    def test_json_list_input(self):
        shaped = shape_row(
            {
                "entry_id": 1,
                "docket_id": "CON-1234567",
                "service_type": ["PET", "MRI"],
                "parties": ["A", "B"],
            }
        )
        assert shaped.service_types == ("PET", "MRI")
        assert json.loads(shaped.document["parties"]) == ["A", "B"]

    def test_blank_segments_dropped(self):
        shaped = shape_row(full_row(service_type="PET; ; MRI;"))
        assert shaped.service_types == ("PET", "MRI")


class TestDocviewUrl:
    def test_synthesized_when_missing(self):
        shaped = shape_row(full_row(docview_url=""))
        assert shaped.document["docview_url"] == (
            "https://weblink.dch.georgia.gov/WebLink/DocView.aspx"
            "?id=12345&dbid=1&repo=HealthPlanning"
        )

    def test_provided_value_kept(self):
        shaped = shape_row(full_row(docview_url="https://example.com/doc/1"))
        assert shaped.document["docview_url"] == "https://example.com/doc/1"


class TestLoader:
    def test_matter_merged_before_document(self):
        conn = FakeConnection()
        load_rows(conn, [full_row()])
        sqls = conn.executed_sql()
        i_matter = next(i for i, s in enumerate(sqls) if "MERGE con.matter" in s)
        i_doc = next(i for i, s in enumerate(sqls) if "MERGE con.document" in s)
        assert i_matter < i_doc

    def test_child_table_inserts_present_and_never_delete(self):
        conn = FakeConnection()
        load_rows(conn, [full_row()])
        sqls = conn.executed_sql()
        assert any("con.matter_docket_variant" in s and "INSERT" in s for s in sqls)
        assert any("con.matter_service_type" in s and "INSERT" in s for s in sqls)
        assert any("con.matter_phase" in s and "INSERT" in s for s in sqls)
        assert not any("DELETE" in s.upper() for s in sqls)

    def test_merge_sql_uses_coalesce(self):
        assert "applicant = COALESCE(s.applicant, t.applicant)" in MATTER_MERGE_SQL
        assert "doc_type = COALESCE(s.doc_type, t.doc_type)" in DOCUMENT_MERGE_SQL
        # validation trio is always taken from the row, never coalesced
        assert "validation_status = s.validation_status" in DOCUMENT_MERGE_SQL
        assert "validated_by = s.validated_by" in DOCUMENT_MERGE_SQL
        assert "COALESCE(s.validation_status" not in DOCUMENT_MERGE_SQL

    def test_default_status_applied_when_row_has_none(self):
        conn = FakeConnection()
        load_rows(conn, [full_row(validation_status="")], default_status="Corrected")
        doc_calls = [(s, p) for s, p in conn.executed if "MERGE con.document" in s]
        assert len(doc_calls) == 1
        assert "Corrected" in doc_calls[0][1]

    def test_row_status_wins_over_default(self):
        conn = FakeConnection()
        load_rows(conn, [full_row(validation_status="Validated")], default_status="Corrected")
        _, params = next((s, p) for s, p in conn.executed if "MERGE con.document" in s)
        assert "Validated" in params
        assert "Corrected" not in params

    def test_commit_count_respects_batch_size(self):
        rows = [full_row(entry_id=str(i)) for i in range(1, 6)]  # 5 rows
        conn = FakeConnection()
        stats = load_rows(conn, rows, batch_size=2)
        assert conn.committed == 3  # after rows 2, 4, and the final partial batch
        assert stats.commits == 3
        assert stats.documents_upserted == 5
        assert stats.matters_upserted == 1  # all rows share one docket

    def test_rejected_rows_emit_no_sql(self):
        conn = FakeConnection()
        stats = load_rows(conn, [full_row(doc_type="Bogus")])
        assert conn.executed == []
        assert conn.committed == 0
        assert len(stats.rejected) == 1
        assert stats.rejected[0].field == "doc_type"
        assert stats.rejected[0].row_number == 1

    def test_mixed_good_and_bad_rows(self):
        rows = [full_row(), full_row(entry_id="not-an-int"), full_row(entry_id="99")]
        conn = FakeConnection()
        stats = load_rows(conn, rows)
        assert stats.rows_read == 3
        assert stats.documents_upserted == 2
        assert [e.row_number for e in stats.rejected] == [2]

    def test_rerun_yields_identical_sql_and_params(self):
        # Idempotency at the SQL level is not assertable with fakes; instead
        # the same input must produce the identical statement stream, which
        # combined with MERGE/insert-if-missing semantics converges on rerun.
        rows = [full_row(), full_row(entry_id="99", docket_id="DET-2020-014")]
        conn1, conn2 = FakeConnection(), FakeConnection()
        load_rows(conn1, list(rows))
        load_rows(conn2, list(rows))
        assert conn1.executed == conn2.executed

    def test_stats_type(self):
        conn = FakeConnection()
        assert isinstance(load_rows(conn, []), LoadStats)

    def test_bad_default_status_raises(self):
        with pytest.raises(ValueError):
            load_rows(FakeConnection(), [], default_status="Fancy")


class TestRealSampleExport:
    """Regression against the real DCH tag export sample (committed fixture)."""

    def test_all_rows_shape(self):
        import csv
        from pathlib import Path

        path = Path(__file__).parent / "fixtures" / "sample_tag_export.csv"
        shaped = []
        with path.open(newline="", encoding="utf-8-sig") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                shaped.append(shape_row(row, row_number=i))

        assert [s.docket_id for s in shaped] == [
            "CON-2099001",
            "CON-2099001",
            "CON-2099002",
            "DET-2099010",
            "CON-2098050",
            "CON-2099003",
        ]
        # Real export forms handled: "5 Initial Application", "Application / Request",
        # en-dash phases, and the out-of-vocabulary "Provisional" status.
        assert shaped[0].document["decision_level"] == 5
        assert shaped[0].document["doc_type"] == "Application/Request"
        assert shaped[4].document["phase"] == "Judicial Review – Court of Appeals"
        assert shaped[4].document["validation_status"] is None  # "Provisional" -> default
        assert shaped[4].document["outcome"] == "Affirmed (appeal)"
        assert shaped[2].matter["county"] == "DeKalb"
        assert shaped[3].document["decision_level"] == 1
