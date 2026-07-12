import csv
import json

import pytest

from ingest.load_document_text import (
    DOCUMENT_TEXT_MERGE_SQL,
    LoadStats,
    Paragraph,
    RowRejected,
    build_arg_parser,
    iter_records,
    load_texts,
    main,
    shape_record,
    validate_records,
)
from tests.fakes import FakeConnection

FULL_TEXT = "In February 2023, Riverstone Imaging filed an application."


def full_record(**overrides) -> dict:
    """A JSONL-style record (docs/05 §B) exercising every field."""
    rec = {
        "entry_id": 9000030,
        "full_text": FULL_TEXT,
        "text_source": "ocr",
        "di_model": "prebuilt-layout",
        "di_confidence": 0.98,
        "paragraphs": [
            {"num": "1", "text": "In February 2023, Riverstone Imaging filed..."},
            {"num": "2", "text": "The Department, in its initial decision..."},
        ],
    }
    rec.update(overrides)
    return rec


def scripted_conn(document_ids: list[int]) -> FakeConnection:
    """FakeConnection whose con.document existence check returns document_ids."""
    conn = FakeConnection()
    conn.script(
        "SELECT entry_id FROM con.document",
        rows=[(i,) for i in document_ids],
        columns=["entry_id"],
    )
    return conn


class TestShapeRecordHappyPath:
    def test_fields_and_char_count(self):
        shaped = shape_record(full_record())
        assert shaped.entry_id == 9000030
        assert shaped.full_text == FULL_TEXT
        assert shaped.char_count == len(FULL_TEXT)
        assert shaped.text_source == "ocr"
        assert shaped.di_model == "prebuilt-layout"
        assert shaped.di_confidence == pytest.approx(0.98)
        assert shaped.paragraphs == (
            Paragraph(num="1", text="In February 2023, Riverstone Imaging filed..."),
            Paragraph(num="2", text="The Department, in its initial decision..."),
        )

    def test_text_source_case_tolerant(self):
        assert shape_record(full_record(text_source="OCR")).text_source == "ocr"
        assert shape_record(full_record(text_source="Native")).text_source == "native"

    def test_string_entry_id_accepted(self):
        assert shape_record(full_record(entry_id="9000030")).entry_id == 9000030

    def test_optional_fields_absent(self):
        rec = {"entry_id": 1, "full_text": "x", "text_source": "tag"}
        shaped = shape_record(rec)
        assert shaped.di_model is None
        assert shaped.di_confidence is None
        assert shaped.paragraphs is None  # no key -> existing rows untouched

    def test_empty_paragraph_list_kept_as_empty(self):
        shaped = shape_record(full_record(paragraphs=[]))
        assert shaped.paragraphs == ()  # explicit empty set -> clears existing rows

    def test_paragraph_num_coerced_and_optional(self):
        shaped = shape_record(
            full_record(paragraphs=[{"num": 1, "text": "a"}, {"text": "b"}])
        )
        assert shaped.paragraphs[0].num == "1"
        assert shaped.paragraphs[1].num is None

    def test_di_confidence_string_number(self):
        assert shape_record(full_record(di_confidence="0.5")).di_confidence == pytest.approx(0.5)


class TestShapeRecordRejects:
    @pytest.mark.parametrize("bad_id", [None, "abc", "", True, 1.5])
    def test_bad_entry_id(self, bad_id):
        with pytest.raises(RowRejected) as exc:
            shape_record(full_record(entry_id=bad_id), line_number=7)
        assert exc.value.error.field == "entry_id"
        assert exc.value.error.row_number == 7

    @pytest.mark.parametrize("bad_text", [None, "", "   ", 42, ["a"]])
    def test_bad_full_text(self, bad_text):
        with pytest.raises(RowRejected) as exc:
            shape_record(full_record(full_text=bad_text))
        assert exc.value.error.field == "full_text"

    @pytest.mark.parametrize("bad_source", [None, "", "scanned", "pdf", 3])
    def test_bad_text_source(self, bad_source):
        with pytest.raises(RowRejected) as exc:
            shape_record(full_record(text_source=bad_source))
        assert exc.value.error.field == "text_source"

    @pytest.mark.parametrize(
        "bad_paragraphs",
        [
            "not-a-list",
            {"num": "1", "text": "a"},
            ["just a string"],
            [{"num": "1"}],  # no text
            [{"num": "1", "text": ""}],
            [{"num": "1", "text": 42}],
        ],
    )
    def test_malformed_paragraphs(self, bad_paragraphs):
        with pytest.raises(RowRejected) as exc:
            shape_record(full_record(paragraphs=bad_paragraphs))
        assert exc.value.error.field == "paragraphs"

    def test_bad_di_confidence(self):
        with pytest.raises(RowRejected) as exc:
            shape_record(full_record(di_confidence="high"))
        assert exc.value.error.field == "di_confidence"

    def test_non_object_record(self):
        # iter_records yields unparseable JSONL lines as raw strings.
        with pytest.raises(RowRejected) as exc:
            shape_record('{"entry_id": oops', line_number=3)
        assert exc.value.error.field == "record"
        assert exc.value.error.row_number == 3


class TestMergeSql:
    def test_full_text_and_char_count_always_win(self):
        assert "full_text = s.full_text" in DOCUMENT_TEXT_MERGE_SQL
        assert "char_count = s.char_count" in DOCUMENT_TEXT_MERGE_SQL
        assert "COALESCE(s.full_text" not in DOCUMENT_TEXT_MERGE_SQL
        assert "COALESCE(s.char_count" not in DOCUMENT_TEXT_MERGE_SQL

    def test_other_columns_coalesce(self):
        for col in ("text_source", "di_model", "di_confidence"):
            assert f"{col} = COALESCE(s.{col}, t.{col})" in DOCUMENT_TEXT_MERGE_SQL


class TestLoader:
    def test_merge_executed_for_known_id(self):
        conn = scripted_conn([9000030])
        stats = load_texts(conn, [full_record()])
        merges = [(s, p) for s, p in conn.executed if "MERGE con.document_text" in s]
        assert len(merges) == 1
        assert merges[0][1] == (
            9000030, FULL_TEXT, len(FULL_TEXT), "ocr", "prebuilt-layout", 0.98
        )
        assert stats.texts_upserted == 1
        assert stats.rejected == []

    def test_unknown_entry_id_rejected_not_crashed(self):
        conn = scripted_conn([])
        stats = load_texts(conn, [full_record()])
        assert stats.texts_upserted == 0
        assert len(stats.rejected) == 1
        assert stats.rejected[0].field == "entry_id"
        assert "con.document" in stats.rejected[0].message
        assert stats.rejected[0].raw_value == "9000030"
        assert not any("MERGE" in s for s in conn.executed_sql())

    def test_mixed_known_and_unknown_ids(self):
        conn = scripted_conn([9000030])
        stats = load_texts(conn, [full_record(), full_record(entry_id=555)])
        assert stats.texts_upserted == 1
        assert [e.raw_value for e in stats.rejected] == ["555"]

    def test_existence_check_is_chunked(self, monkeypatch):
        import ingest.load_document_text as mod

        monkeypatch.setattr(mod, "_EXISTS_CHUNK", 2)
        ids = list(range(1, 6))  # 5 ids -> 3 chunks
        conn = scripted_conn(ids)
        load_texts(conn, [full_record(entry_id=i) for i in ids])
        exists_sqls = [
            s for s in conn.executed_sql() if "SELECT entry_id FROM con.document" in s
        ]
        assert len(exists_sqls) == 3
        assert all("IN (" in s for s in exists_sqls)

    def test_paragraphs_deleted_then_inserted_in_order(self):
        conn = scripted_conn([9000030])
        load_texts(conn, [full_record()])
        sqls = conn.executed_sql()
        i_delete = next(i for i, s in enumerate(sqls) if "DELETE FROM con.opinion_paragraph" in s)
        insert_idx = [i for i, s in enumerate(sqls) if "INSERT INTO con.opinion_paragraph" in s]
        assert insert_idx and all(i_delete < i for i in insert_idx)
        inserts = [p for s, p in conn.executed if "INSERT INTO con.opinion_paragraph" in s]
        assert inserts[0] == (
            9000030,
            "1",
            json.dumps(["In February 2023, Riverstone Imaging filed..."]),
            "In February 2023, Riverstone Imaging filed...",
            0,
        )
        assert inserts[1][1] == "2"
        assert inserts[1][4] == 1  # sort_order follows list index

    def test_record_without_paragraphs_leaves_rows_untouched(self):
        conn = scripted_conn([9000030])
        rec = full_record()
        del rec["paragraphs"]
        stats = load_texts(conn, [rec])
        assert stats.paragraphs_written == 0
        assert not any("con.opinion_paragraph" in s for s in conn.executed_sql())

    def test_empty_paragraph_list_clears_wholesale(self):
        conn = scripted_conn([9000030])
        load_texts(conn, [full_record(paragraphs=[])])
        sqls = conn.executed_sql()
        assert any("DELETE FROM con.opinion_paragraph" in s for s in sqls)
        assert not any("INSERT INTO con.opinion_paragraph" in s for s in sqls)

    def test_commit_count_respects_batch_size(self):
        ids = list(range(1, 6))  # 5 records
        conn = scripted_conn(ids)
        stats = load_texts(conn, [full_record(entry_id=i) for i in ids], batch_size=2)
        assert conn.committed == 3  # after records 2, 4, and the final partial batch
        assert stats.commits == 3
        assert stats.texts_upserted == 5
        assert stats.paragraphs_written == 10

    def test_shape_rejects_collected_and_emit_no_sql(self):
        conn = scripted_conn([9000030])
        records = [full_record(), full_record(entry_id="bad"), '{"entry_id": oops']
        stats = load_texts(conn, records)
        assert stats.records_read == 3
        assert stats.texts_upserted == 1
        assert [e.field for e in stats.rejected] == ["entry_id", "record"]
        assert len([s for s in conn.executed_sql() if "MERGE" in s]) == 1

    def test_rerun_yields_identical_sql_and_params(self):
        records = [full_record(), full_record(entry_id=9000031)]
        conn1 = scripted_conn([9000030, 9000031])
        conn2 = scripted_conn([9000030, 9000031])
        load_texts(conn1, [dict(r) for r in records])
        load_texts(conn2, [dict(r) for r in records])
        assert conn1.executed == conn2.executed

    def test_stats_type(self):
        assert isinstance(load_texts(scripted_conn([]), []), LoadStats)

    def test_bad_batch_size_raises(self):
        with pytest.raises(ValueError):
            load_texts(scripted_conn([]), [], batch_size=0)


class TestValidateRecords:
    def test_counts_without_db(self):
        stats = validate_records([full_record(), full_record(entry_id="bad")])
        assert stats.records_read == 2
        assert stats.texts_upserted == 1
        assert stats.paragraphs_written == 2
        assert [e.field for e in stats.rejected] == ["entry_id"]
        assert stats.commits == 0


class TestCli:
    def test_parser_defaults(self):
        args = build_arg_parser().parse_args(["texts.jsonl"])
        assert args.apply is False  # --apply gates all DB writes
        assert args.batch_size == 200
        assert args.rejects is None

    def test_parser_flags(self):
        args = build_arg_parser().parse_args(
            ["texts", "--apply", "--batch-size", "50", "--rejects", "out.csv"]
        )
        assert args.apply is True
        assert args.batch_size == 50
        assert str(args.rejects) == "out.csv"

    def test_main_dry_run_touches_no_db(self, tmp_path, capsys):
        path = tmp_path / "texts.jsonl"
        lines = [
            json.dumps(full_record()),
            json.dumps(full_record(entry_id="bad")),
            "{not json",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # No DB is available in tests: succeeding proves --apply gates the
        # connection (get_connection is only imported/called under --apply).
        assert main([str(path)]) == 0
        out = capsys.readouterr().out
        assert "records read:       3" in out
        assert "valid records:      1" in out
        assert "rejected records:   2" in out
        assert "dry run" in out

    def test_main_writes_rejects_csv(self, tmp_path):
        path = tmp_path / "texts.jsonl"
        path.write_text(json.dumps(full_record(text_source="scanned")) + "\n", encoding="utf-8")
        rejects = tmp_path / "rejects.csv"
        assert main([str(path), "--rejects", str(rejects)]) == 0
        with rejects.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["field"] == "text_source"

    def test_iter_records_directory_sorted(self, tmp_path):
        (tmp_path / "b.jsonl").write_text(
            json.dumps({"entry_id": 2}) + "\n", encoding="utf-8"
        )
        (tmp_path / "a.jsonl").write_text(
            json.dumps({"entry_id": 1}) + "\n", encoding="utf-8"
        )
        records = list(iter_records(tmp_path))
        assert [r["entry_id"] for r in records] == [1, 2]

    def test_iter_records_empty_directory_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            list(iter_records(tmp_path))

    def test_iter_records_bad_line_yields_raw_string(self, tmp_path):
        path = tmp_path / "texts.jsonl"
        path.write_text("{not json\n\n" + json.dumps({"entry_id": 1}) + "\n", encoding="utf-8")
        records = list(iter_records(path))
        assert records[0] == "{not json"  # blank line skipped
        assert records[1] == {"entry_id": 1}
