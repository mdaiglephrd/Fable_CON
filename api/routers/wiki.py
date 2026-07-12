"""Wiki: article listing/detail plus the pending-revision review workflow.

Revisions are submitted as ``pending``; review sets ``approved`` or
``rejected``. Approval also touches the article's updated_at (the body merge
itself is editorial and happens outside this API — only status changes here).
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import drop_none, get_db, parse_json_field, query, scalar

router = APIRouter()

REVISION_STATUS_PENDING = "pending"
# Review action -> resulting con.wiki_revision.status (schema CHECK values).
_REVIEW_STATUS = {"approve": "approved", "reject": "rejected"}


@router.get("/wiki")
def list_wiki(conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(
        conn,
        "SELECT w.article_id, w.group_name, w.title, w.status, w.updated_at "
        "FROM con.wiki_article w ORDER BY w.group_name, w.title",
        [],
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("group_name") or "", []).append(
            drop_none(
                {
                    "id": row.get("article_id"),
                    "title": row.get("title"),
                    "status": row.get("status"),
                    "updatedAt": row.get("updated_at"),
                }
            )
        )
    return {
        "groups": [
            {"group": name, "articles": articles} for name, articles in grouped.items()
        ],
        "total": len(rows),
    }


@router.get("/wiki/{article_id}")
def get_article(article_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(conn, "SELECT w.* FROM con.wiki_article w WHERE w.article_id = ?", [article_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Wiki article {article_id!r} not found.")
    article = rows[0]
    parse_json_field(article, "toc_json")
    parse_json_field(article, "body_json")

    revisions = []
    for row in query(
        conn,
        "SELECT r.* FROM con.wiki_revision r WHERE r.article_id = ? "
        "ORDER BY r.submitted_at DESC, r.revision_id DESC",
        [article_id],
    ):
        parse_json_field(row, "diff_json")
        revisions.append(
            drop_none(
                {
                    "revisionId": row.get("revision_id"),
                    "author": row.get("author"),
                    "submittedAt": row.get("submitted_at"),
                    "status": row.get("status"),
                    "diff": row.get("diff_json"),
                }
            )
        )

    return drop_none(
        {
            "id": article.get("article_id"),
            "group": article.get("group_name"),
            "title": article.get("title"),
            "toc": article.get("toc_json"),
            "body": article.get("body_json"),
            "status": article.get("status"),
            "updatedAt": article.get("updated_at"),
            "revisions": revisions,
        }
    )


class RevisionCreate(BaseModel):
    author: str = Field(min_length=1)
    diff: dict[str, Any] | list[Any] | str


@router.post("/wiki/{article_id}/revisions", status_code=201)
def create_revision(
    article_id: str, revision: RevisionCreate, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    exists = scalar(
        conn, "SELECT article_id FROM con.wiki_article WHERE article_id = ?", [article_id]
    )
    if not exists:
        raise HTTPException(status_code=404, detail=f"Wiki article {article_id!r} not found.")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO con.wiki_revision (article_id, author, status, diff_json) "
        "OUTPUT INSERTED.revision_id VALUES (?, ?, ?, ?)",
        [article_id, revision.author, REVISION_STATUS_PENDING, json.dumps(revision.diff)],
    )
    row = cursor.fetchone()
    conn.commit()
    return {
        "revisionId": row[0] if row else None,
        "articleId": article_id,
        "author": revision.author,
        "status": REVISION_STATUS_PENDING,
        "diff": revision.diff,
    }


class RevisionReview(BaseModel):
    action: str


@router.post("/wiki/{article_id}/revisions/{revision_id}/review")
def review_revision(
    article_id: str, revision_id: int, review: RevisionReview, conn: Any = Depends(get_db)
) -> dict[str, Any]:
    if review.action not in _REVIEW_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action {review.action!r}; one of: {', '.join(_REVIEW_STATUS)}",
        )
    current = scalar(
        conn,
        "SELECT status FROM con.wiki_revision WHERE revision_id = ? AND article_id = ?",
        [revision_id, article_id],
    )
    if current is None:
        raise HTTPException(
            status_code=404,
            detail=f"Revision {revision_id} not found for wiki article {article_id!r}.",
        )
    new_status = _REVIEW_STATUS[review.action]
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE con.wiki_revision SET status = ? WHERE revision_id = ? AND article_id = ?",
        [new_status, revision_id, article_id],
    )
    if review.action == "approve":
        cursor.execute(
            "UPDATE con.wiki_article SET updated_at = SYSUTCDATETIME() WHERE article_id = ?",
            [article_id],
        )
    conn.commit()
    return {"revisionId": revision_id, "articleId": article_id, "status": new_status}
