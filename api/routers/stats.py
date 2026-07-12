"""GET /stats — outcome aggregates over con.matter (+ matter_service_type).

``range`` is all|3yr|1yr; the year cutoff is computed in Python (no GETDATE())
and applied as a parameterized ``year_filed >= ?`` filter. Rates are
percentages (0-100, one decimal); a zero denominator yields 0.0.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import drop_none, get_db, query
from common import vocab

router = APIRouter()

_RANGE_YEARS: dict[str, int | None] = {"all": None, "3yr": 3, "1yr": 1}

# Outcome groupings over vocab.OUTCOMES (asserted below so drift in the vocab
# is caught at import time, same pattern as common/deadline_rules.py).
APPROVED_OUTCOMES: tuple[str, ...] = (
    "Approved",
    "Approved with conditions",
    "Partially approved",
)
DENIED_OUTCOMES: tuple[str, ...] = ("Denied",)
REVERSED_OUTCOMES: tuple[str, ...] = ("Reversed (appeal)", "Vacated (appeal)")
AFFIRMED_OUTCOMES: tuple[str, ...] = ("Affirmed (appeal)",)
assert set(
    APPROVED_OUTCOMES + DENIED_OUTCOMES + REVERSED_OUTCOMES + AFFIRMED_OUTCOMES
) <= set(vocab.OUTCOMES)

# A matter reached appellate review when it went past the desk decision
# (vocab.DECISION_LEVELS: 2 = Hearing Officer Decision and above).
_APPEALED_LEVEL = 2


def _placeholders(values: tuple[str, ...]) -> str:
    return ", ".join("?" for _ in values)


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


@router.get("/stats")
def get_stats(range: str = "all", conn: Any = Depends(get_db)) -> dict[str, Any]:
    if range not in _RANGE_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown range {range!r}; one of: {', '.join(_RANGE_YEARS)}",
        )
    years = _RANGE_YEARS[range]
    where_sql = ""
    where_params: list[Any] = []
    cutoff_year: int | None = None
    if years is not None:
        cutoff_year = date.today().year - years
        where_sql = " WHERE m.year_filed >= ?"
        where_params = [cutoff_year]

    outcome_rows = query(
        conn,
        "SELECT m.final_outcome, COUNT(*) AS n FROM con.matter m"
        + where_sql + " GROUP BY m.final_outcome",
        where_params,
    )
    by_outcome = {row.get("final_outcome"): row.get("n") or 0 for row in outcome_rows}
    total = sum(by_outcome.values())
    approved = sum(by_outcome.get(outcome, 0) for outcome in APPROVED_OUTCOMES)
    denied = sum(by_outcome.get(outcome, 0) for outcome in DENIED_OUTCOMES)
    decided = approved + denied

    appeal_rows = query(
        conn,
        "SELECT COUNT(*) AS total, "
        f"SUM(CASE WHEN m.highest_review_level >= {_APPEALED_LEVEL} THEN 1 ELSE 0 END) "
        "AS appealed, "
        f"SUM(CASE WHEN m.final_outcome IN ({_placeholders(REVERSED_OUTCOMES)}) "
        "THEN 1 ELSE 0 END) AS reversed, "
        f"SUM(CASE WHEN m.final_outcome IN ({_placeholders(AFFIRMED_OUTCOMES)}) "
        "THEN 1 ELSE 0 END) AS affirmed "
        "FROM con.matter m" + where_sql,
        [*REVERSED_OUTCOMES, *AFFIRMED_OUTCOMES, *where_params],
    )
    appeal_row = appeal_rows[0] if appeal_rows else {}
    appealed = appeal_row.get("appealed") or 0
    reversed_count = appeal_row.get("reversed") or 0
    affirmed = appeal_row.get("affirmed") or 0

    outcome_sums = (
        f"SUM(CASE WHEN m.final_outcome IN ({_placeholders(APPROVED_OUTCOMES)}) "
        "THEN 1 ELSE 0 END) AS approved, "
        f"SUM(CASE WHEN m.final_outcome IN ({_placeholders(DENIED_OUTCOMES)}) "
        "THEN 1 ELSE 0 END) AS denied"
    )
    outcome_sum_params = [*APPROVED_OUTCOMES, *DENIED_OUTCOMES]

    by_service = [
        {
            "serviceType": row.get("service_type"),
            "total": row.get("total") or 0,
            "approved": row.get("approved") or 0,
            "denied": row.get("denied") or 0,
        }
        for row in query(
            conn,
            f"SELECT st.service_type, COUNT(*) AS total, {outcome_sums} "
            "FROM con.matter_service_type st "
            "JOIN con.matter m ON m.docket_id = st.docket_id"
            + where_sql + " GROUP BY st.service_type ORDER BY COUNT(*) DESC, st.service_type",
            [*outcome_sum_params, *where_params],
        )
    ]

    by_year = [
        {
            "year": row.get("year_filed"),
            "total": row.get("total") or 0,
            "approved": row.get("approved") or 0,
            "denied": row.get("denied") or 0,
        }
        for row in query(
            conn,
            f"SELECT m.year_filed, COUNT(*) AS total, {outcome_sums} FROM con.matter m"
            + where_sql + " GROUP BY m.year_filed ORDER BY m.year_filed",
            [*outcome_sum_params, *where_params],
        )
    ]

    by_family = [
        {
            "family": row.get("docket_family"),
            "total": row.get("total") or 0,
            "approved": row.get("approved") or 0,
            "denied": row.get("denied") or 0,
        }
        for row in query(
            conn,
            f"SELECT m.docket_family, COUNT(*) AS total, {outcome_sums} FROM con.matter m"
            + where_sql + " GROUP BY m.docket_family ORDER BY COUNT(*) DESC, m.docket_family",
            [*outcome_sum_params, *where_params],
        )
    ]

    return drop_none(
        {
            "range": range,
            "cutoffYear": cutoff_year,
            "kpis": {
                "totalDockets": total,
                "grantRate": _pct(approved, decided),
                "denialRate": _pct(denied, decided),
                "reversalRate": _pct(reversed_count, appealed),
            },
            "byService": by_service,
            "byYear": by_year,
            "byFamily": by_family,
            "appeal": {
                "appealedPct": _pct(appealed, appeal_row.get("total") or 0),
                "reversalPct": _pct(reversed_count, appealed),
                "affirmancePct": _pct(affirmed, appealed),
            },
        }
    )
