from datetime import date, timedelta

from common import vocab
from common.deadline_rules import (
    DEADLINE_RULES,
    ComputedDeadline,
    DeadlineRule,
    compute_deadlines,
)


def test_every_rule_has_valid_family():
    assert DEADLINE_RULES
    for rule in DEADLINE_RULES:
        assert isinstance(rule, DeadlineRule)
        assert rule.docket_family in vocab.DOCKET_FAMILIES
        assert rule.offset_days >= 0
        assert rule.rule_id
        assert rule.trigger_event
        assert rule.basis_statute


def test_rule_ids_unique():
    ids = [r.rule_id for r in DEADLINE_RULES]
    assert len(ids) == len(set(ids))


def test_con_challenge_window_30_days():
    out = compute_deadlines("CON", "Letter of determination", date(2026, 1, 1))
    assert len(out) == 1
    dl = out[0]
    assert isinstance(dl, ComputedDeadline)
    assert dl.due_date == date(2026, 1, 31)
    assert dl.basis_statute == "31-6-44"


def test_con_hearing_window_open_and_close():
    base = date(2026, 3, 1)
    out = compute_deadlines("CON", "Hearing officer appointed", base)
    due = sorted(d.due_date for d in out)
    assert due == [base + timedelta(days=60), base + timedelta(days=120)]


def test_con_judicial_petition_and_finality():
    base = date(2026, 5, 1)
    petition = compute_deadlines("CON", "Final agency decision", base)
    assert [d.due_date for d in petition] == [date(2026, 5, 31)]
    assert petition[0].basis_statute == "31-6-44.1"
    finality = compute_deadlines("CON", "Superior court docketing", base)
    assert [d.due_date for d in finality] == [date(2026, 8, 29)]  # +120
    assert finality[0].basis_statute == "50-13-19"


def test_det_request_filed_sufficiency_and_letter():
    base = date(2026, 3, 14)
    out = compute_deadlines("DET", "Request filed", base)
    due = sorted(d.due_date for d in out)
    assert due == [date(2026, 3, 25), date(2026, 5, 13)]  # +11 sufficiency, +60 letter


def test_det_subtypes_fold_onto_det_rules():
    base = date(2026, 4, 1)
    det = compute_deadlines("DET", "Final agency decision", base)
    for family in ("DET-EQT", "DET-ASC", "LNR-ASC", "LNR-EQT"):
        assert compute_deadlines(family, "Final agency decision", base) == det
    assert det and det[0].due_date == date(2026, 5, 1)


def test_unknown_family_or_trigger_returns_empty():
    assert compute_deadlines("BOGUS", "Letter of determination", date(2026, 1, 1)) == []
    assert compute_deadlines("CON", "No such trigger", date(2026, 1, 1)) == []


def test_computed_deadline_label_is_humanized():
    out = compute_deadlines("CON", "Challenge filed", date(2026, 1, 1))
    assert out[0].label == "HO Appointment"
