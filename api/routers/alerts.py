"""Saved alerts: GET/POST /alerts and soft DELETE /alerts/{id} (active=0).

Alert rows are never hard-deleted — DELETE flips ``active`` to 0, matching
the watchlist convention in api.main.

Ownership is server-authoritative: when the platform identity (api.auth) is
present on create, it overrides any client-supplied owner; the client value
is only honored when unauthenticated (local dev).
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import CurrentUser, get_current_user
from api.deps import drop_none, get_db, parse_json_field, query, slug_id

router = APIRouter()


def _alert_json(row: dict[str, Any]) -> dict[str, Any]:
    parse_json_field(row, "query_json")
    active = row.get("active")
    return drop_none(
        {
            "alertId": row.get("alert_id"),
            "owner": row.get("owner_upn"),
            "name": row.get("name"),
            "query": row.get("query_json"),
            "scope": row.get("scope"),
            "frequency": row.get("frequency"),
            "active": None if active is None else bool(active),
            "createdAt": row.get("created_at"),
        }
    )


@router.get("/alerts")
def list_alerts(
    owner: str | None = None, all: bool = False, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    where: list[str] = []
    params: list[Any] = []
    if not all:
        where.append("a.active = ?")
        params.append(1)
    if owner is not None:
        where.append("a.owner_upn = ?")
        params.append(owner)
    sql = "SELECT a.* FROM con.saved_alert a"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.created_at DESC, a.alert_id"
    items = [_alert_json(row) for row in query(conn, sql, params)]
    return {"items": items, "total": len(items)}


class AlertCreate(BaseModel):
    name: str = Field(min_length=1)
    query: dict[str, Any] | list[Any] | str
    scope: str
    frequency: str
    owner: str | None = None


@router.post("/alerts", status_code=201)
def create_alert(
    alert: AlertCreate,
    conn: Any = Depends(get_db),
    user: CurrentUser | None = Depends(get_current_user),
) -> dict[str, Any]:
    owner = (user.upn or user.email or user.id) if user is not None else alert.owner
    alert_id = slug_id(alert.name)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO con.saved_alert "
        "(alert_id, owner_upn, name, query_json, scope, frequency, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [alert_id, owner, alert.name, json.dumps(alert.query), alert.scope,
         alert.frequency, 1],
    )
    conn.commit()
    return drop_none(
        {
            "alertId": alert_id,
            "owner": owner,
            "name": alert.name,
            "query": alert.query,
            "scope": alert.scope,
            "frequency": alert.frequency,
            "active": True,
        }
    )


@router.delete("/alerts/{alert_id}")
def deactivate_alert(alert_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    # Soft-deactivate only; saved alerts are never hard-deleted.
    cursor = conn.cursor()
    cursor.execute("UPDATE con.saved_alert SET active = 0 WHERE alert_id = ?", [alert_id])
    if cursor.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail=f"Alert {alert_id!r} not found.")
    conn.commit()
    return {"id": alert_id, "active": False}
