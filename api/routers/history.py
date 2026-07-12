"""GET /history/{docket_id} — the docket_event timeline (newest first).

Resolves docket variants the same way /matters/{id} does; the optional
``type`` filter is whitelist-validated against vocab.EVENT_TYPES.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import drop_none, get_db, query, resolve_docket
from common import vocab

router = APIRouter()


def event_json(row: dict[str, Any]) -> dict[str, Any]:
    """Map a con.docket_event row to the camelCase timeline shape."""
    return drop_none(
        {
            "eventId": row.get("event_id"),
            "date": row.get("event_date"),
            "type": row.get("event_type"),
            "court": row.get("court"),
            "description": row.get("description"),
            "actor": row.get("actor"),
            "entryId": row.get("entry_id"),
        }
    )


@router.get("/history/{docket_id}")
def docket_history(
    docket_id: str, type: str | None = None, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    if type is not None and type not in vocab.EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event type {type!r}; one of: {', '.join(vocab.EVENT_TYPES)}",
        )
    resolved = resolve_docket(conn, docket_id)
    where = ["e.docket_id = ?"]
    params: list[Any] = [resolved]
    if type is not None:
        where.append("e.event_type = ?")
        params.append(type)
    rows = query(
        conn,
        "SELECT e.* FROM con.docket_event e WHERE " + " AND ".join(where)
        + " ORDER BY e.event_date DESC, e.event_id DESC",
        params,
    )
    items = [event_json(row) for row in rows]
    return {"docketId": resolved, "items": items, "total": len(items)}
