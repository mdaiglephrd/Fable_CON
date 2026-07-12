import json
from datetime import date
from pathlib import Path

import pytest

from common.proceeding import (
    REFERENCE_NOW,
    build_proceeding,
    duration_label,
    fmt,
    parse_date,
    seed_of,
    stages_to_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = REPO_ROOT / "tests" / "fixtures" / "handoff" / "golden_proceeding.json"

with open(GOLDEN, encoding="utf-8") as _f:
    _GOLDEN = json.load(_f)


def test_reference_now():
    assert REFERENCE_NOW == date(2026, 6, 25)


@pytest.mark.parametrize("label", sorted(_GOLDEN))
def test_golden_parity(label):
    """build_proceeding(rec) must deep-equal the golden proceeding for each rec."""
    case = _GOLDEN[label]
    assert build_proceeding(case["rec"]) == case["proceeding"]


def test_fmt_matches_en_us_short():
    assert fmt(date(2026, 5, 26)) == "May 26, 2026"
    assert fmt(date(2026, 1, 1)) == "Jan 1, 2026"
    assert fmt(date(2026, 4, 4)) == "Apr 4, 2026"
    assert fmt(None) == ""


def test_parse_date():
    assert parse_date("4/14/2026") == date(2026, 4, 14)
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date(date(2026, 1, 1)) == date(2026, 1, 1)


def test_duration_label():
    assert duration_label(date(2026, 2, 28), date(2026, 4, 4)) == "1 month"
    assert duration_label(date(2024, 6, 12), date(2024, 11, 1)) == "5 months"


def test_seed_of_deterministic_thresholds():
    # Replicated 32-bit hash: these values gate the CON precedent signal.
    assert seed_of("CON2026004") == pytest.approx(0.672)
    assert seed_of("CON24-0042") == pytest.approx(0.047)
    assert seed_of("CON2026099") == pytest.approx(0.956)


def test_con_shape_has_no_subtype_keys():
    proc = build_proceeding(_GOLDEN["con_pending"]["rec"])
    assert "subtypeLabel" not in proc
    assert "subtypeSub" not in proc
    assert proc["badge"] == {"label": "CON", "color": "#F43F5E"}


def test_det_shape_has_subtype_keys():
    proc = build_proceeding(_GOLDEN["det_pending"]["rec"])
    assert proc["subtypeLabel"] == "DET (Generic)"
    assert proc["subtypeSub"] == "Determination of Reviewability"


def test_now_override_moves_precedent_review_date():
    rec = _GOLDEN["con_approved"]["rec"]
    proc = build_proceeding(rec, now=date(2026, 1, 15))
    # precedent detail carries fmt(now - 30 days)
    assert "Dec 16, 2025" in proc["precedent"]["detail"]


def test_stages_to_rows_maps_columns():
    proc = build_proceeding(_GOLDEN["con_approved"]["rec"])
    rows = stages_to_rows("CON-2026004", proc)
    assert len(rows) == len(proc["stages"])
    first = rows[0]
    assert first["docket_id"] == "CON-2026004"
    assert first["stage_num"] == "0"
    assert first["title"] == "Letter of Intent"
    assert first["stage_label"] == "Letter of Intent"
    assert first["stage_date"] == date(2026, 2, 28)  # "Filed Feb 28, 2026"
    assert first["sort_order"] == 0
    assert first["has_opinion"] is False
    assert first["court"] is None
    # exactly one current stage for a closed CON? closed -> all complete -> none current
    assert not any(r["is_current"] for r in rows)


def test_stages_to_rows_flags_current_stage_for_pending():
    proc = build_proceeding(_GOLDEN["con_pending"]["rec"])
    rows = stages_to_rows("CON-2026006", proc)
    current = [r for r in rows if r["is_current"]]
    assert len(current) == 1
    assert current[0]["stage_num"] == "1"  # active stage
