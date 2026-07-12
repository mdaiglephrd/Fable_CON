"""GET /cases/{entry_id} — the case-reader payload for the research console.

Assembles con.opinion + ordered paragraphs + headnotes + reporter citations +
counsel + briefs (via the document's docket) + document/matter meta + citator
flag counts into the camelCase shape the SPA reads (field names follow
tests/fixtures/handoff/con-corpus.js). 404 when no opinion row exists.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import drop_none, get_db, parse_json_field, query
from api.routers.citator import flag_counts

router = APIRouter()


@router.get("/cases/{entry_id}")
def get_case(entry_id: int, conn: Any = Depends(get_db)) -> dict[str, Any]:
    opinions = query(conn, "SELECT o.* FROM con.opinion o WHERE o.entry_id = ?", [entry_id])
    if not opinions:
        raise HTTPException(status_code=404, detail=f"No opinion found for entry_id {entry_id}.")
    opinion = opinions[0]
    for field in ("caption_json", "disposition_json", "treatment_note_json"):
        parse_json_field(opinion, field)

    docs = query(conn, "SELECT d.* FROM con.document d WHERE d.entry_id = ?", [entry_id])
    doc = docs[0] if docs else {}
    docket_id = doc.get("docket_id")

    matter: dict[str, Any] = {}
    service_types: list[str] = []
    brief_rows: list[dict[str, Any]] = []
    if docket_id:
        matters = query(conn, "SELECT m.* FROM con.matter m WHERE m.docket_id = ?", [docket_id])
        matter = matters[0] if matters else {}
        service_types = [
            row["service_type"]
            for row in query(
                conn,
                "SELECT st.service_type FROM con.matter_service_type st "
                "WHERE st.docket_id = ? ORDER BY st.service_type",
                [docket_id],
            )
        ]
        brief_rows = query(
            conn,
            "SELECT b.title, b.party_side, b.attorney_name, b.firm, b.filed_date, b.page_count "
            "FROM con.brief b WHERE b.docket_id = ? ORDER BY b.filed_date, b.brief_id",
            [docket_id],
        )

    paragraphs: list[dict[str, Any]] = []
    for row in query(
        conn,
        "SELECT p.para_num, p.segs_json FROM con.opinion_paragraph p "
        "WHERE p.entry_id = ? ORDER BY p.sort_order, p.paragraph_id",
        [entry_id],
    ):
        parse_json_field(row, "segs_json")
        paragraphs.append({"num": row.get("para_num"), "segs": row.get("segs_json") or []})

    headnotes = [
        drop_none(
            {
                "num": row.get("num"),
                "key": row.get("key_number"),
                "keyId": row.get("topic_id"),
                "topic": row.get("topic_label"),
                "text": row.get("text"),
            }
        )
        for row in query(
            conn,
            "SELECT h.num, h.topic_id, h.topic_label, h.text, t.key_number "
            "FROM con.headnote h LEFT JOIN con.topic t ON t.topic_id = h.topic_id "
            "WHERE h.entry_id = ? ORDER BY h.headnote_id",
            [entry_id],
        )
    ]

    citations = [
        row["citation"]
        for row in query(
            conn,
            "SELECT rc.citation FROM con.reporter_citation rc "
            "WHERE rc.entry_id = ? ORDER BY rc.is_parallel, rc.cite_id",
            [entry_id],
        )
    ]

    counsel = [
        drop_none(
            {"role": row.get("role"), "name": row.get("attorney_name"), "firm": row.get("firm")}
        )
        for row in query(
            conn,
            "SELECT c.role, c.attorney_name, c.firm FROM con.counsel c "
            "WHERE c.entry_id = ? ORDER BY c.counsel_id",
            [entry_id],
        )
    ]

    note = opinion.get("treatment_note_json")
    note = note if isinstance(note, dict) else {}
    treatment = drop_none(
        {
            "level": opinion.get("treatment_level"),
            "word": note.get("word"),
            "text": note.get("text"),
        }
    )

    meta = drop_none(
        {
            "Service": "; ".join(service_types) or None,
            "Applicant": matter.get("applicant"),
            "Facility": matter.get("facility"),
            "County": matter.get("county"),
            "CON No.": docket_id,
            "Argued": opinion.get("argued_date"),
            "Decided": opinion.get("decided_date"),
        }
    )

    is_published = opinion.get("is_published")
    return drop_none(
        {
            "entryId": entry_id,
            "docketId": docket_id,
            "badge": matter.get("docket_family"),
            "title": doc.get("title"),
            "captionParts": opinion.get("caption_json"),
            "tribunalLine": opinion.get("tribunal_line"),
            "citations": citations,
            "docketNo": opinion.get("court_docket_no"),
            "decided": opinion.get("decided_date"),
            "subsequent": opinion.get("subsequent_history"),
            "treatment": treatment or None,
            "editorial": opinion.get("editorial_synopsis"),
            "headnotes": headnotes,
            "byline": opinion.get("byline"),
            "intro": opinion.get("intro_text"),
            "paragraphs": paragraphs,
            "disposition": opinion.get("disposition_json"),
            "meta": meta,
            "counsel": counsel,
            "briefs": [
                drop_none(
                    {
                        "title": row.get("title"),
                        "side": row.get("party_side"),
                        "attorney": row.get("attorney_name"),
                        "firm": row.get("firm"),
                        "filedDate": row.get("filed_date"),
                        "pageCount": row.get("page_count"),
                    }
                )
                for row in brief_rows
            ],
            "standardOfReview": opinion.get("standard_of_review"),
            "isPublished": None if is_published is None else bool(is_published),
            "citator": {"flags": flag_counts(conn, entry_id)},
        }
    )
