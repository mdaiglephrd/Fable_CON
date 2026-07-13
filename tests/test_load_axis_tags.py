from ingest.load_axis_tags import (
    load_tag_rows,
    shape_tag_row,
    validate_rows,
)
from ingest.load_tags import RowRejected
from tests.fakes import FakeConnection


def test_shape_valid_row():
    shaped = shape_tag_row(
        {"entry_id": 1043, "axis1": "CON", "axis2": "Application (non-authority)", "axis3": "110;120", "axis4": "P110"}
    )
    assert shaped.entry_id == 1043
    assert shaped.axis1 == "CON"
    assert shaped.axis3_codes == ("110", "120")
    assert shaped.axis4_codes == ("P110",)


def test_shape_row_missing_entry_id_is_rejected():
    try:
        shape_tag_row({"axis1": "CON"})
        assert False, "expected RowRejected"
    except RowRejected as exc:
        assert exc.error.field == "entry_id"


def test_shape_row_unknown_axis_value_is_rejected():
    try:
        shape_tag_row({"entry_id": 1043, "axis1": "NOT-REAL"})
        assert False, "expected RowRejected"
    except RowRejected as exc:
        assert exc.error.field == "axis_tags"
        assert "axis1" in exc.error.message


def test_shape_row_masterfile_with_axis3_is_rejected():
    try:
        shape_tag_row({"entry_id": 1043, "axis2": "Masterfile", "axis3": "110"})
        assert False, "expected RowRejected"
    except RowRejected as exc:
        assert "masterfile" in exc.error.message.lower()


def test_shape_row_allows_partial_incremental_tagging():
    # Only axis1 provided this pass; axis2/3/4 blank is not itself an error.
    shaped = shape_tag_row({"entry_id": 1043, "axis1": "DET"})
    assert shaped.axis2 is None
    assert shaped.axis3_codes == ()
    assert shaped.axis4_codes == ()


def test_json_array_values_for_axis3_axis4():
    shaped = shape_tag_row({"entry_id": 1043, "axis3": ["110", "120"], "axis4": ["P110", "P120"]})
    assert shaped.axis3_codes == ("110", "120")
    assert shaped.axis4_codes == ("P110", "P120")


# --- load_tag_rows (DB layer) ----------------------------------------------


def test_load_tag_rows_writes_expected_sql():
    conn = FakeConnection()
    stats = load_tag_rows(
        conn,
        [{"entry_id": 1043, "axis1": "CON", "axis2": "Application (non-authority)", "axis3": "110", "axis4": "P110"}],
    )
    assert stats.rows_upserted == 1
    assert stats.rejected == []
    sqls = conn.executed_sql()
    assert any("MERGE con.document_axis1" in s for s in sqls)
    assert any("MERGE con.document_axis2" in s for s in sqls)
    assert any("INSERT INTO con.document_axis3" in s for s in sqls)
    assert any("INSERT INTO con.document_axis4" in s for s in sqls)


def test_load_tag_rows_skips_untouched_axes():
    conn = FakeConnection()
    load_tag_rows(conn, [{"entry_id": 1043, "axis1": "CON"}])

    sqls = conn.executed_sql()
    assert any("MERGE con.document_axis1" in s for s in sqls)
    assert not any("MERGE con.document_axis2" in s for s in sqls)
    assert not any("INSERT INTO con.document_axis3" in s for s in sqls)
    assert not any("INSERT INTO con.document_axis4" in s for s in sqls)


def test_load_tag_rows_rerun_is_idempotent_shape():
    conn = FakeConnection()
    row = {"entry_id": 1043, "axis1": "CON", "axis3": "110;120"}

    load_tag_rows(conn, [row])
    first = len(conn.executed)
    load_tag_rows(conn, [row])
    second = len(conn.executed) - first

    assert second == first  # same SQL shape emitted both times, no accumulation


def test_load_tag_rows_rejects_masterfile_violation_without_writing():
    conn = FakeConnection()
    stats = load_tag_rows(conn, [{"entry_id": 1043, "axis2": "Masterfile", "axis4": "P110"}])

    assert stats.rows_upserted == 0
    assert len(stats.rejected) == 1
    assert conn.executed == []


def test_load_tag_rows_commits_every_batch_size():
    conn = FakeConnection()
    rows = [{"entry_id": i, "axis1": "CON"} for i in range(3)]
    stats = load_tag_rows(conn, rows, batch_size=1)

    assert stats.rows_upserted == 3
    assert stats.commits == 3


# --- validate_rows (dry run) -------------------------------------------------


def test_validate_rows_counts_without_touching_db():
    stats = validate_rows(
        [
            {"entry_id": 1043, "axis1": "CON"},
            {"entry_id": 1044, "axis1": "NOT-REAL"},
        ]
    )
    assert stats.rows_read == 2
    assert stats.rows_upserted == 1
    assert len(stats.rejected) == 1
