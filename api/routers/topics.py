"""GET /topics (full key-number tree) and GET /topics/{topic_id} (documents)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import drop_none, get_db, query, scalar

router = APIRouter()


@router.get("/topics")
def topic_tree(conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(
        conn,
        "SELECT t.topic_id, t.parent_topic_id, t.key_number, t.title, t.description "
        "FROM con.topic t ORDER BY t.topic_id",
        [],
    )
    nodes: dict[str, dict[str, Any]] = {
        row["topic_id"]: drop_none(
            {
                "topicId": row["topic_id"],
                "keyNumber": row.get("key_number"),
                "title": row.get("title"),
                "description": row.get("description"),
                "children": [],
            }
        )
        for row in rows
    }
    roots: list[dict[str, Any]] = []
    for row in rows:
        node = nodes[row["topic_id"]]
        parent = row.get("parent_topic_id")
        if parent and parent in nodes:
            nodes[parent]["children"].append(node)
        else:
            roots.append(node)
    return {"topics": roots, "total": len(rows)}


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(conn, "SELECT t.* FROM con.topic t WHERE t.topic_id = ?", [topic_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id!r} not found.")
    topic = rows[0]

    documents = [
        drop_none(
            {
                "entryId": row.get("entry_id"),
                "docketId": row.get("docket_id"),
                "title": row.get("title"),
                "docType": row.get("doc_type"),
                "date": row.get("doc_date"),
                "badge": row.get("docket_family"),
                "applicant": row.get("applicant"),
                "facility": row.get("facility"),
            }
        )
        for row in query(
            conn,
            "SELECT d.entry_id, d.docket_id, d.title, d.doc_type, d.doc_date, "
            "m.docket_family, m.applicant, m.facility "
            "FROM con.document_topic dt "
            "JOIN con.document d ON d.entry_id = dt.entry_id "
            "LEFT JOIN con.matter m ON m.docket_id = d.docket_id "
            "WHERE dt.topic_id = ? ORDER BY d.doc_date DESC, d.entry_id",
            [topic_id],
        )
    ]

    headnote_count = (
        scalar(conn, "SELECT COUNT(*) FROM con.headnote WHERE topic_id = ?", [topic_id]) or 0
    )
    children = [
        drop_none(
            {
                "topicId": row.get("topic_id"),
                "keyNumber": row.get("key_number"),
                "title": row.get("title"),
            }
        )
        for row in query(
            conn,
            "SELECT t.topic_id, t.key_number, t.title FROM con.topic t "
            "WHERE t.parent_topic_id = ? ORDER BY t.topic_id",
            [topic_id],
        )
    ]

    return drop_none(
        {
            "topicId": topic.get("topic_id"),
            "parentTopicId": topic.get("parent_topic_id"),
            "keyNumber": topic.get("key_number"),
            "title": topic.get("title"),
            "description": topic.get("description"),
            "headnoteCount": headnote_count,
            "children": children,
            "documents": documents,
        }
    )
