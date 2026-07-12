"""Research projects: /projects list/create/detail, items, and complete.

Project ids are a slug of the name plus a short random suffix (api.deps
slug_id). Item creation requires at least one target (entryId or docketId);
docket ids are normalized to canonical form like the watchlist does.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.deps import drop_none, get_db, parse_json_field, query, scalar, slug_id
from common.docket import normalize_docket

router = APIRouter()

PROJECT_STATUS_OPEN = "open"
PROJECT_STATUS_COMPLETE = "complete"


def _project_json(row: dict[str, Any]) -> dict[str, Any]:
    parse_json_field(row, "tags_json")
    return drop_none(
        {
            "id": row.get("project_id"),
            "owner": row.get("owner_upn"),
            "name": row.get("name"),
            "description": row.get("description"),
            "tags": row.get("tags_json"),
            "status": row.get("status"),
            "createdAt": row.get("created_at"),
        }
    )


@router.get("/projects")
def list_projects(
    owner: str | None = None, status: str | None = None, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    where: list[str] = []
    params: list[Any] = []
    if owner is not None:
        where.append("p.owner_upn = ?")
        params.append(owner)
    if status is not None:
        where.append("p.status = ?")
        params.append(status)
    sql = "SELECT p.* FROM con.research_project p"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.created_at DESC, p.project_id"
    items = [_project_json(row) for row in query(conn, sql, params)]
    return {"items": items, "total": len(items)}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    tags: list[str] | None = None
    owner: str | None = None


@router.post("/projects", status_code=201)
def create_project(project: ProjectCreate, conn: Any = Depends(get_db)) -> dict[str, Any]:
    project_id = slug_id(project.name)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO con.research_project "
        "(project_id, owner_upn, name, description, tags_json, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            project_id,
            project.owner,
            project.name,
            project.description,
            json.dumps(project.tags) if project.tags is not None else None,
            PROJECT_STATUS_OPEN,
        ],
    )
    conn.commit()
    return drop_none(
        {
            "id": project_id,
            "owner": project.owner,
            "name": project.name,
            "description": project.description,
            "tags": project.tags,
            "status": PROJECT_STATUS_OPEN,
        }
    )


@router.get("/projects/{project_id}")
def get_project(project_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(
        conn, "SELECT p.* FROM con.research_project p WHERE p.project_id = ?", [project_id]
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")
    project = _project_json(rows[0])
    project["items"] = [
        drop_none(
            {
                "itemId": row.get("item_id"),
                "entryId": row.get("entry_id"),
                "docketId": row.get("docket_id"),
                "flagged": bool(row.get("flagged")),
                "note": row.get("note"),
                "documentTitle": row.get("document_title"),
                "applicant": row.get("applicant"),
                "facility": row.get("facility"),
            }
        )
        for row in query(
            conn,
            "SELECT i.item_id, i.entry_id, i.docket_id, i.flagged, i.note, "
            "d.title AS document_title, m.applicant, m.facility "
            "FROM con.project_item i "
            "LEFT JOIN con.document d ON d.entry_id = i.entry_id "
            "LEFT JOIN con.matter m ON m.docket_id = COALESCE(i.docket_id, d.docket_id) "
            "WHERE i.project_id = ? ORDER BY i.item_id",
            [project_id],
        )
    ]
    return project


class ProjectItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int | None = Field(default=None, alias="entryId")
    docket_id: str | None = Field(default=None, alias="docketId")
    flagged: bool = False
    note: str | None = None


@router.post("/projects/{project_id}/items", status_code=201)
def add_project_item(
    project_id: str, item: ProjectItemCreate, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    if item.entry_id is None and item.docket_id is None:
        raise HTTPException(
            status_code=400, detail="At least one of entryId, docketId is required."
        )
    docket_id = item.docket_id
    if docket_id:
        match = normalize_docket(docket_id)
        if match:
            docket_id = match.canonical
    exists = scalar(
        conn, "SELECT project_id FROM con.research_project WHERE project_id = ?", [project_id]
    )
    if not exists:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO con.project_item (project_id, entry_id, docket_id, flagged, note) "
        "OUTPUT INSERTED.item_id VALUES (?, ?, ?, ?, ?)",
        [project_id, item.entry_id, docket_id, 1 if item.flagged else 0, item.note],
    )
    row = cursor.fetchone()
    conn.commit()
    return drop_none(
        {
            "itemId": row[0] if row else None,
            "projectId": project_id,
            "entryId": item.entry_id,
            "docketId": docket_id,
            "flagged": item.flagged,
            "note": item.note,
        }
    )


@router.post("/projects/{project_id}/complete")
def complete_project(project_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE con.research_project SET status = ? WHERE project_id = ?",
        [PROJECT_STATUS_COMPLETE, project_id],
    )
    if cursor.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")
    conn.commit()
    return {"id": project_id, "status": PROJECT_STATUS_COMPLETE}
