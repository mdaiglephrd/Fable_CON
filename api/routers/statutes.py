"""GET /statutes and GET /statutes/{statute_id} (full row + xrefs + citing cases)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import drop_none, get_db, parse_json_field, query
from api.routers.citator import treatment_level

router = APIRouter()

# Mirrors the CHECK constraint on con.statute.kind (DESIGN.md schema).
STATUTE_KINDS: tuple[str, ...] = ("OCGA", "RULE")


@router.get("/statutes")
def list_statutes(kind: str | None = None, conn: Any = Depends(get_db)) -> dict[str, Any]:
    if kind is not None and kind not in STATUTE_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown statute kind {kind!r}; one of: {', '.join(STATUTE_KINDS)}",
        )
    sql = (
        "SELECT s.statute_id, s.kind, s.citation_label, s.title, s.effective_date "
        "FROM con.statute s"
    )
    params: list[Any] = []
    if kind is not None:
        sql += " WHERE s.kind = ?"
        params.append(kind)
    sql += " ORDER BY s.statute_id"
    items = [
        drop_none(
            {
                "statuteId": row.get("statute_id"),
                "kind": row.get("kind"),
                "citationLabel": row.get("citation_label"),
                "title": row.get("title"),
                "effectiveDate": row.get("effective_date"),
            }
        )
        for row in query(conn, sql, params)
    ]
    return {"items": items, "total": len(items)}


@router.get("/statutes/{statute_id}")
def statute_detail(statute_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = query(conn, "SELECT s.* FROM con.statute s WHERE s.statute_id = ?", [statute_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Statute {statute_id!r} not found.")
    statute = rows[0]
    parse_json_field(statute, "subsections_json")

    xrefs = [
        drop_none(
            {
                "statuteId": row.get("statute_id"),
                "citationLabel": row.get("citation_label"),
                "title": row.get("title"),
            }
        )
        for row in query(
            conn,
            "SELECT s.statute_id, s.citation_label, s.title "
            "FROM con.statute_xref x JOIN con.statute s ON s.statute_id = x.to_statute_id "
            "WHERE x.from_statute_id = ? "
            "UNION "
            "SELECT s.statute_id, s.citation_label, s.title "
            "FROM con.statute_xref x JOIN con.statute s ON s.statute_id = x.from_statute_id "
            "WHERE x.to_statute_id = ?",
            [statute_id, statute_id],
        )
    ]

    citing_cases = [
        drop_none(
            {
                "target": row.get("citing_entry_id"),
                "badge": row.get("docket_family"),
                "title": row.get("case_title"),
                "cite": row.get("case_cite"),
                "treat": row.get("treatment"),
                "level": treatment_level(row["treatment"]) if row.get("treatment") else None,
                "pinpoint": row.get("pinpoint"),
                "snippet": row.get("snippet"),
            }
        )
        for row in query(
            conn,
            "SELECT c.citing_entry_id, c.treatment, c.pinpoint, c.snippet, "
            "d.title AS case_title, d.docket_id, m.docket_family, "
            "(SELECT TOP 1 rc.citation FROM con.reporter_citation rc "
            "WHERE rc.entry_id = c.citing_entry_id ORDER BY rc.cite_id) AS case_cite "
            "FROM con.citation c "
            "JOIN con.document d ON d.entry_id = c.citing_entry_id "
            "LEFT JOIN con.matter m ON m.docket_id = d.docket_id "
            "WHERE c.cited_statute_id = ? ORDER BY c.citation_id",
            [statute_id],
        )
    ]

    return drop_none(
        {
            "statuteId": statute.get("statute_id"),
            "kind": statute.get("kind"),
            "citationLabel": statute.get("citation_label"),
            "title": statute.get("title"),
            "fullText": statute.get("full_text"),
            "effectiveDate": statute.get("effective_date"),
            "regimeNote": statute.get("regime_note"),
            "subsections": statute.get("subsections_json"),
            "xrefs": xrefs,
            "citingCases": citing_cases,
        }
    )
