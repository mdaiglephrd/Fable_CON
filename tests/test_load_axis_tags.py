from ingest.load_axis_tags import (
    load_tag_rows,
    shape_tag_row,
    validate_rows,
)
from ingest.load_tags import RowRejected
from tests.fakes import FakeConnection


def _conn_with_documents(*entry_ids: int) -> FakeConnection:
    """FakeConnection scripted so the batch existence check finds entry_ids."""
    conn = FakeConnection()
    conn.script(
        "FROM con.document WHERE entry_id IN", rows=[(e,) for e in entry_ids]
    )
    return conn


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
    conn = _conn_with_documents(1043)
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
    conn = _conn_with_documents(1043)
    load_tag_rows(conn, [{"entry_id": 1043, "axis1": "CON"}])

    sqls = conn.executed_sql()
    assert any("MERGE con.document_axis1" in s for s in sqls)
    assert not any("MERGE con.document_axis2" in s for s in sqls)
    assert not any("INSERT INTO con.document_axis3" in s for s in sqls)
    assert not any("INSERT INTO con.document_axis4" in s for s in sqls)


def test_load_tag_rows_rerun_is_idempotent_shape():
    row = {"entry_id": 1043, "axis1": "CON", "axis3": "110;120"}

    conn = _conn_with_documents(1043)
    load_tag_rows(conn, [row])
    first = len(conn.executed)
    load_tag_rows(conn, [row])
    second = len(conn.executed) - first

    assert second == first  # same SQL shape emitted both times, no accumulation


def test_load_tag_rows_rejects_masterfile_violation_without_writing():
    conn = _conn_with_documents(1043)
    stats = load_tag_rows(conn, [{"entry_id": 1043, "axis2": "Masterfile", "axis4": "P110"}])

    assert stats.rows_upserted == 0
    assert len(stats.rejected) == 1
    assert conn.executed == []  # rejected in pure validation, before any DB check


def test_load_tag_rows_commits_every_batch_size():
    conn = _conn_with_documents(0, 1, 2)
    rows = [{"entry_id": i, "axis1": "CON"} for i in range(3)]
    stats = load_tag_rows(conn, rows, batch_size=1)

    assert stats.rows_upserted == 3
    assert stats.commits == 3


# --- DB-level conflicts become rejects, not crashes ---------------------------


def test_unknown_entry_id_is_rejected_not_crashed():
    conn = _conn_with_documents(1043)  # 9999 not in con.document
    stats = load_tag_rows(
        conn,
        [
            {"entry_id": 9999, "axis1": "CON"},
            {"entry_id": 1043, "axis1": "CON"},
        ],
    )

    assert stats.rows_upserted == 1
    assert len(stats.rejected) == 1
    assert stats.rejected[0].field == "entry_id"
    assert "not in con.document" in stats.rejected[0].message


def test_masterfile_transition_rejected_when_db_has_axis34_tags():
    conn = _conn_with_documents(1043)
    conn.script("FROM con.document_axis3 WHERE entry_id IN", rows=[(1043,)])

    stats = load_tag_rows(conn, [{"entry_id": 1043, "axis2": "Masterfile"}])

    assert stats.rows_upserted == 0
    assert len(stats.rejected) == 1
    assert "Axis 3/4 tags" in stats.rejected[0].message
    assert not any("MERGE con.document_axis2" in s for s in conn.executed_sql())


def test_adding_axis34_rejected_when_db_has_masterfile_tag():
    conn = _conn_with_documents(1043)
    conn.script("FROM con.document_axis2", rows=[(1043,)])  # tagged Masterfile in DB

    stats = load_tag_rows(conn, [{"entry_id": 1043, "axis3": "110"}])

    assert stats.rows_upserted == 0
    assert len(stats.rejected) == 1
    assert "Masterfile" in stats.rejected[0].message
    assert not any("INSERT INTO con.document_axis3" in s for s in conn.executed_sql())


def test_retagging_axis2_away_from_masterfile_permits_axis34_in_same_row():
    conn = _conn_with_documents(1043)
    conn.script("FROM con.document_axis2", rows=[(1043,)])  # tagged Masterfile in DB

    stats = load_tag_rows(
        conn, [{"entry_id": 1043, "axis2": "Statute", "axis3": "110"}]
    )

    # The row re-tags Axis 2 first (MERGE precedes the Axis 3 insert), so the
    # conflict clears within the row itself.
    assert stats.rows_upserted == 1
    assert stats.rejected == []
    sqls = conn.executed_sql()
    assert any("MERGE con.document_axis2" in s for s in sqls)
    assert any("INSERT INTO con.document_axis3" in s for s in sqls)


def test_in_batch_ordering_conflict_is_caught():
    # Row 1 adds an Axis 3 tag; row 2 (same batch) tags the same document
    # Masterfile -- the DB pre-check alone can't see row 1's uncommitted
    # write, so in-batch state tracking must catch it.
    conn = _conn_with_documents(1043)
    stats = load_tag_rows(
        conn,
        [
            {"entry_id": 1043, "axis3": "110"},
            {"entry_id": 1043, "axis2": "Masterfile"},
        ],
    )

    assert stats.rows_upserted == 1
    assert len(stats.rejected) == 1
    assert stats.rejected[0].row_number == 2


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
