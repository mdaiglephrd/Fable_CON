"""GET /citator/{entry_id} — how-cited flags, citing cases, table of authorities.

How-cited = con.citation WHERE cited_entry_id; table-of-authorities = WHERE
citing_entry_id. Response keys are camelCase and mirror the citator block in
tests/fixtures/handoff/con-corpus.js.
"""

from typing import Any

from fastapi import APIRouter, Depends

from api.deps import drop_none, get_db, query
from common import vocab

router = APIRouter()

# Citator treatment verb (con.vocab_treatment) -> good-law banner level
# (con.vocab_treatment_level). Anything unmapped or NULL is neutral.
TREATMENT_LEVEL: dict[str, str] = {
    "Followed": "positive",
    "Distinguished": "caution",
    "Criticized": "caution",
    "Reversed": "negative",
    "Overruled": "negative",
    "Cited": "neutral",
    "Neutral": "neutral",
}
assert set(TREATMENT_LEVEL) <= set(vocab.TREATMENTS)
assert set(TREATMENT_LEVEL.values()) <= set(vocab.TREATMENT_LEVELS)

# con.statute.kind -> display cite used by the table of authorities.
_STATUTE_CITE = {"OCGA": "Ga. Code Ann.", "RULE": "Ga. Comp. R. & Regs."}


def treatment_level(treatment: str | None) -> str:
    return TREATMENT_LEVEL.get(treatment or "", "neutral")


def flag_counts(conn: Any, entry_id: int) -> list[dict[str, Any]]:
    """Citator flag counts for one cited document (single GROUP BY query)."""
    rows = query(
        conn,
        "SELECT treatment, COUNT(*) AS n FROM con.citation "
        "WHERE cited_entry_id = ? GROUP BY treatment",
        [entry_id],
    )
    by_level = {"positive": 0, "caution": 0, "negative": 0, "neutral": 0}
    citing = 0
    for row in rows:
        count = row.get("n") or 0
        citing += count
        by_level[treatment_level(row.get("treatment"))] += count
    return [
        {"label": "Citing", "count": citing},
        {"label": "Positive", "count": by_level["positive"]},
        {"label": "Cautionary", "count": by_level["caution"]},
        {"label": "Negative", "count": by_level["negative"]},
    ]


def _citing_cases(conn: Any, entry_id: int) -> list[dict[str, Any]]:
    rows = query(
        conn,
        "SELECT c.citing_entry_id, c.treatment, c.depth, c.snippet, c.pinpoint, "
        "c.topic_id, t.key_number, d.docket_id, d.title AS case_title, "
        "m.docket_family, o.court_docket_no, "
        "(SELECT TOP 1 rc.citation FROM con.reporter_citation rc "
        "WHERE rc.entry_id = c.citing_entry_id ORDER BY rc.cite_id) AS case_cite "
        "FROM con.citation c "
        "JOIN con.document d ON d.entry_id = c.citing_entry_id "
        "LEFT JOIN con.matter m ON m.docket_id = d.docket_id "
        "LEFT JOIN con.opinion o ON o.entry_id = c.citing_entry_id "
        "LEFT JOIN con.topic t ON t.topic_id = c.topic_id "
        "WHERE c.cited_entry_id = ? ORDER BY c.citation_id",
        [entry_id],
    )
    return [
        drop_none(
            {
                "badge": row.get("docket_family"),
                "dktNum": row.get("court_docket_no") or row.get("docket_id"),
                "treat": row.get("treatment"),
                "level": treatment_level(row.get("treatment")),
                "title": row.get("case_title"),
                "cite": row.get("case_cite"),
                "depth": row.get("depth"),
                "snippet": row.get("snippet"),
                "pinpoint": row.get("pinpoint"),
                "keys": (
                    [[row.get("key_number"), row["topic_id"]]] if row.get("topic_id") else []
                ),
                "target": row.get("citing_entry_id"),
            }
        )
        for row in rows
    ]


def _table_of_authorities(conn: Any, entry_id: int) -> list[dict[str, Any]]:
    rows = query(
        conn,
        "SELECT c.citation_id, c.cited_entry_id, c.cited_statute_id, c.cited_external, "
        "c.pinpoint, d.title AS case_title, "
        "(SELECT TOP 1 rc.citation FROM con.reporter_citation rc "
        "WHERE rc.entry_id = c.cited_entry_id ORDER BY rc.cite_id) AS case_cite, "
        "s.kind AS statute_kind, s.citation_label, s.title AS statute_title "
        "FROM con.citation c "
        "LEFT JOIN con.document d ON d.entry_id = c.cited_entry_id "
        "LEFT JOIN con.statute s ON s.statute_id = c.cited_statute_id "
        "WHERE c.citing_entry_id = ? ORDER BY c.citation_id",
        [entry_id],
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        if row.get("cited_entry_id") is not None:
            kind, target = "case", row["cited_entry_id"]
            title, cite = row.get("case_title"), row.get("case_cite")
        elif row.get("cited_statute_id"):
            kind, target = "stat", row["cited_statute_id"]
            label, statute_title = row.get("citation_label"), row.get("statute_title")
            title = f"{label} — {statute_title}" if label and statute_title else (
                label or statute_title
            )
            cite = _STATUTE_CITE.get(row.get("statute_kind"))
        else:
            kind, target = "external", None
            title, cite = row.get("cited_external"), None
        items.append(
            drop_none(
                {
                    "title": title,
                    "cite": cite,
                    "pinpoint": row.get("pinpoint"),
                    "target": target,
                    "kind": kind,
                }
            )
        )
    return items


@router.get("/citator/{entry_id}")
def get_citator(entry_id: int, conn: Any = Depends(get_db)) -> dict[str, Any]:
    return {
        "entryId": entry_id,
        "flags": flag_counts(conn, entry_id),
        "citingCases": _citing_cases(conn, entry_id),
        "tableOfAuthorities": _table_of_authorities(conn, entry_id),
    }
