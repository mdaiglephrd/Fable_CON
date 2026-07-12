"""GET /dockets/{docket_id}/proceeding — the docket-engine proceeding view.

If curated con.proceeding_stage rows exist for the resolved docket they are
returned mapped into the engine shape; otherwise the proceeding is
synthesized from the matter row via common.proceeding.build_proceeding (the
Python port of docket-engine.js). Either way the response carries the
docket_event timeline under ``events``.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends

from api.deps import drop_none, get_db, query, resolve_docket
from api.routers.history import event_json
from common import vocab
from common.docket_family import classify_family
from common.proceeding import _badge_meta, build_proceeding

router = APIRouter()

# con.matter.final_outcome -> docket-engine `finding`. The engine branches
# only on 'Pending' (open docket), 'Denied', and 'Withdrawn'; every other
# closed outcome renders as an effective/approved terminal state, so the
# remaining closed vocab codes fold onto 'Approved'. Dismissed ends without a
# merits decision, so it folds onto 'Withdrawn'.
FINDING_BY_OUTCOME: dict[str, str] = {
    "Approved": "Approved",
    "Approved with conditions": "Approved",
    "Partially approved": "Approved",
    "Denied": "Denied",
    "Withdrawn": "Withdrawn",
    "Dismissed": "Withdrawn",
    "Remanded": "Approved",
    "Settled": "Approved",
    "Affirmed (appeal)": "Approved",
    "Reversed (appeal)": "Approved",
    "Vacated (appeal)": "Approved",
    "Pending": "Pending",
    "Unknown": "Pending",
}
assert set(FINDING_BY_OUTCOME) <= set(vocab.OUTCOMES)


def _finding(final_outcome: str | None) -> str:
    """Map final_outcome to the engine finding; unknown closed values ~ Approved."""
    if not final_outcome:
        return "Pending"
    return FINDING_BY_OUTCOME.get(final_outcome, "Approved")


def _stage_json(row: dict[str, Any]) -> dict[str, Any]:
    """Map a stored con.proceeding_stage row into the engine stage shape."""
    return drop_none(
        {
            "n": row.get("stage_num"),
            "status": "active" if row.get("is_current") else "complete",
            "title": row.get("title") or row.get("stage_label"),
            "dateLine": row.get("summary"),
            "stageLabel": row.get("stage_label"),
            "court": row.get("court"),
            "cite": row.get("cite"),
            "date": row.get("stage_date"),
            "outcome": row.get("outcome"),
            "filingsCount": row.get("filings_count"),
            "decisionMaker": row.get("decision_maker"),
            "durationDays": row.get("duration_days"),
            "hasOpinion": bool(row.get("has_opinion")),
            "opinionEntryId": row.get("opinion_entry_id"),
        }
    )


@router.get("/dockets/{docket_id}/proceeding")
def docket_proceeding(docket_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    resolved = resolve_docket(conn, docket_id)
    matters = query(conn, "SELECT m.* FROM con.matter m WHERE m.docket_id = ?", [resolved])
    matter = matters[0] if matters else {}
    family = matter.get("docket_family") or classify_family(resolved)
    finding = _finding(matter.get("final_outcome"))

    events = [
        event_json(row)
        for row in query(
            conn,
            "SELECT e.* FROM con.docket_event e WHERE e.docket_id = ? "
            "ORDER BY e.event_date DESC, e.event_id DESC",
            [resolved],
        )
    ]

    stage_rows = query(
        conn,
        "SELECT s.* FROM con.proceeding_stage s WHERE s.docket_id = ? "
        "ORDER BY s.sort_order, s.stage_id",
        [resolved],
    )
    if stage_rows:
        return {
            "docketId": resolved,
            "source": "stored",
            "badge": _badge_meta(family),
            "isClosed": finding != "Pending",
            "isActive": finding == "Pending",
            "stages": [_stage_json(row) for row in stage_rows],
            "events": events,
        }

    received = matter.get("letter_of_intent_date")
    if received is None and matter.get("year_filed"):
        # year_filed alone carries no day-level date; anchor the engine's
        # review clock at Jan 1 of the filing year.
        received = date(int(matter["year_filed"]), 1, 1)
    rec = {
        "type": family,
        "num": resolved,
        "facility": matter.get("facility"),
        "title": matter.get("project_description"),
        "received": received,
        "date": matter.get("final_decision_date"),
        "finding": finding,
        "county": matter.get("county"),
    }
    proceeding = build_proceeding(rec)
    return {"docketId": resolved, "source": "synthesized", **proceeding, "events": events}
