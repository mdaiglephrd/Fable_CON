"""FastAPI app for the GA DCH CON research database.

Read-mostly HTTP layer over the `con` schema (see DESIGN.md). All SQL is
parameterized; column names come only from fixed whitelist maps, never from
user input. Auth is platform-level (App Service Easy Auth / Entra) — none here.
"""

import json
import os
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from api import semantic
from api.search_client import ConfigurationError
from common import vocab
from common.docket import normalize_docket

app = FastAPI(
    title="GA DCH CON research API",
    description="Georgia Certificate of Need matters, documents, and weekly-report events.",
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


# ---------------------------------------------------------------------------
# DB plumbing
# ---------------------------------------------------------------------------


def get_db() -> Iterator[Any]:
    """Yield a live DB connection. Tests override this with a FakeConnection.

    common.db (and pyodbc) is imported lazily so the app imports cleanly in
    environments without ODBC libraries or SQL_* configuration.
    """
    from common import db

    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _rows_to_dicts(cursor: Any) -> list[dict[str, Any]]:
    if not cursor.description:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _query(conn: Any, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    return _rows_to_dicts(cursor)


def _scalar(conn: Any, sql: str, params: list[Any]) -> Any:
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    row = cursor.fetchone()
    return row[0] if row else None


def _parse_json_field(row: dict[str, Any], field: str) -> None:
    """Parse a JSON text column to a list/object in place (None on bad JSON)."""
    value = row.get(field)
    if isinstance(value, str):
        try:
            row[field] = json.loads(value)
        except ValueError:
            row[field] = None


# ---------------------------------------------------------------------------
# Filter / sort whitelists (column names NEVER come from user input)
# ---------------------------------------------------------------------------

# param -> (column expression, operator kind)
MATTER_FILTERS: dict[str, tuple[str, str]] = {
    "docket_id": ("m.docket_id", "eq"),
    "applicant": ("m.applicant", "like"),
    "facility": ("m.facility", "like"),
    "matter_type": ("m.matter_type", "eq"),
    "action_type": ("m.action_type", "eq"),
    "county": ("m.county", "eq"),
    "service_area": ("m.service_area", "like"),
    "bed_count_min": ("m.bed_count", "gte"),
    "bed_count_max": ("m.bed_count", "lte"),
    "year_filed": ("m.year_filed", "eq"),
    "final_outcome": ("m.final_outcome", "eq"),
    "final_decision_date_from": ("m.final_decision_date", "gte"),
    "final_decision_date_to": ("m.final_decision_date", "lte"),
    "highest_review_level": ("m.highest_review_level", "eq"),
}

# Matter filters that resolve through child tables.
MATTER_EXISTS_FILTERS: dict[str, str] = {
    "service_type": (
        "EXISTS (SELECT 1 FROM con.matter_service_type st "
        "WHERE st.docket_id = m.docket_id AND st.service_type = ?)"
    ),
    "phase": (
        "EXISTS (SELECT 1 FROM con.matter_phase mp "
        "WHERE mp.docket_id = m.docket_id AND mp.phase = ?)"
    ),
    "docket_variant": (
        "EXISTS (SELECT 1 FROM con.matter_docket_variant dv "
        "WHERE dv.docket_id = m.docket_id AND dv.variant = ?)"
    ),
    "completeness_flag": (
        "EXISTS (SELECT 1 FROM OPENJSON(m.completeness_flags) f WHERE f.value = ?)"
    ),
}

MATTER_LIKE_COLUMNS = ("m.applicant", "m.facility", "m.service_area")
MATTER_FT_COLUMNS = "(applicant, facility, service_area)"

MATTER_SORT: dict[str, str] = {
    "docket_id": "m.docket_id",
    "applicant": "m.applicant",
    "facility": "m.facility",
    "matter_type": "m.matter_type",
    "action_type": "m.action_type",
    "county": "m.county",
    "bed_count": "m.bed_count",
    "year_filed": "m.year_filed",
    "final_outcome": "m.final_outcome",
    "final_decision_date": "m.final_decision_date",
    "highest_review_level": "m.highest_review_level",
    "created_at": "m.created_at",
    "updated_at": "m.updated_at",
}

DOCUMENT_FILTERS: dict[str, tuple[str, str]] = {
    "entry_id": ("d.entry_id", "eq"),
    "docket_id": ("d.docket_id", "eq"),
    "file_name": ("d.file_name", "like"),
    "source_path": ("d.source_path", "like"),
    "doc_type": ("d.doc_type", "eq"),
    "decision_level": ("d.decision_level", "eq"),
    "phase": ("d.phase", "eq"),
    "outcome": ("d.outcome", "eq"),
    "validation_status": ("d.validation_status", "eq"),
    "decision_maker": ("d.decision_maker", "like"),
    "doc_date_from": ("d.doc_date", "gte"),
    "doc_date_to": ("d.doc_date", "lte"),
    "page_count_min": ("d.page_count", "gte"),
    "page_count_max": ("d.page_count", "lte"),
    "repo_created_from": ("d.repo_date_created", "gte"),
    "repo_created_to": ("d.repo_date_created", "lte"),
    "repo_modified_from": ("d.repo_date_modified", "gte"),
    "repo_modified_to": ("d.repo_date_modified", "lte"),
    "ocr_confidence_min": ("d.ocr_confidence", "gte"),
    "ocr_confidence_max": ("d.ocr_confidence", "lte"),
    "validated_by": ("d.validated_by", "eq"),
    "validated_from": ("d.validated_date", "gte"),
    "validated_to": ("d.validated_date", "lte"),
    "party": ("d.parties", "like"),  # parties is a JSON array; substring match on its text
    "template_name": ("d.template_name", "eq"),
    "ocr_status": ("d.ocr_status", "eq"),
    "duplicate_of": ("d.duplicate_of", "eq"),
}

DOCUMENT_LIKE_COLUMNS = ("d.file_name", "d.decision_maker", "d.source_path")
DOCUMENT_FT_COLUMNS = "(file_name, decision_maker, source_path)"

DOCUMENT_SORT: dict[str, str] = {
    "entry_id": "d.entry_id",
    "docket_id": "d.docket_id",
    "doc_type": "d.doc_type",
    "decision_level": "d.decision_level",
    "phase": "d.phase",
    "doc_date": "d.doc_date",
    "outcome": "d.outcome",
    "validation_status": "d.validation_status",
    "page_count": "d.page_count",
    "file_name": "d.file_name",
    "created_at": "d.created_at",
    "updated_at": "d.updated_at",
}

EVENT_LIKE_COLUMNS = ("e.applicant", "e.project_description")
EVENT_FT_COLUMNS = "(applicant, project_description)"

_OPS = {"eq": "=", "like": "LIKE", "gte": ">=", "lte": "<="}


def fulltext_enabled() -> bool:
    return os.environ.get("FULLTEXT_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def _fts_query(q: str) -> str:
    """Shape a user query for CONTAINSTABLE: quoted prefix terms ANDed together."""
    terms = [t.replace('"', "") for t in q.split()]
    terms = [t for t in terms if t]
    return " AND ".join(f'"{t}*"' for t in terms) or '""'


def _clamp_paging(limit: int, offset: int) -> tuple[int, int]:
    return max(1, min(limit, MAX_LIMIT)), max(0, offset)


def _order_by(sort: str | None, whitelist: dict[str, str], default: str) -> str:
    if not sort:
        return default
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    column = whitelist.get(key)
    if column is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sort field {key!r}; valid fields: {', '.join(sorted(whitelist))}",
        )
    return f"{column} DESC" if descending else f"{column} ASC"


def _build_where(
    values: dict[str, Any],
    filters: dict[str, tuple[str, str]],
    exists_filters: dict[str, str] | None = None,
) -> tuple[list[str], list[Any]]:
    """Build WHERE clauses from whitelisted filters. Values are parameterized."""
    clauses: list[str] = []
    params: list[Any] = []
    for name, (column, kind) in filters.items():
        value = values.get(name)
        if value is None:
            continue
        clauses.append(f"{column} {_OPS[kind]} ?")
        params.append(f"%{value}%" if kind == "like" else value)
    for name, clause in (exists_filters or {}).items():
        value = values.get(name)
        if value is None:
            continue
        clauses.append(clause)
        params.append(value)
    return clauses, params


def _like_clause(columns: tuple[str, ...], q: str) -> tuple[str, list[Any]]:
    clause = "(" + " OR ".join(f"{c} LIKE ?" for c in columns) + ")"
    return clause, [f"%{q}%"] * len(columns)


def _paged(
    conn: Any,
    *,
    select_sql: str,
    count_sql: str,
    where: list[str],
    params: list[Any],
    order_by: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    total = _scalar(conn, count_sql + where_sql, params)
    items_sql = (
        f"{select_sql}{where_sql} ORDER BY {order_by} "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    )
    items = _query(conn, items_sql, [*params, offset, limit])
    return {"items": items, "total": total or 0, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# Health + vocab
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_VOCAB_LISTS: dict[str, tuple] = {
    "service_type": vocab.SERVICE_TYPES,
    "matter_type": vocab.MATTER_TYPES,
    "action_type": vocab.ACTION_TYPES,
    "doc_type": vocab.DOC_TYPES,
    "phase": vocab.PHASES,
    "outcome": vocab.OUTCOMES,
    "county": vocab.COUNTIES,
    "validation_status": vocab.VALIDATION_STATUSES,
}


@app.get("/vocab/{name}")
def get_vocab(name: str) -> dict[str, Any]:
    if name == "decision_level":
        items: list[Any] = [
            {"level": level, "label": label} for level, label in vocab.DECISION_LEVELS.items()
        ]
    elif name in _VOCAB_LISTS:
        items = list(_VOCAB_LISTS[name])
    else:
        valid = ", ".join(sorted([*_VOCAB_LISTS, "decision_level"]))
        raise HTTPException(status_code=404, detail=f"Unknown vocabulary {name!r}; one of: {valid}")
    return {"name": name, "items": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Matters
# ---------------------------------------------------------------------------


@app.get("/matters")
def list_matters(
    docket_id: str | None = None,
    applicant: str | None = None,
    facility: str | None = None,
    matter_type: str | None = None,
    action_type: str | None = None,
    county: str | None = None,
    service_area: str | None = None,
    bed_count_min: int | None = None,
    bed_count_max: int | None = None,
    year_filed: int | None = None,
    final_outcome: str | None = None,
    final_decision_date_from: date | None = None,
    final_decision_date_to: date | None = None,
    highest_review_level: int | None = None,
    service_type: str | None = None,
    phase: str | None = None,
    docket_variant: str | None = None,
    completeness_flag: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    sort: str | None = None,
    conn: Any = Depends(get_db),
) -> dict[str, Any]:
    limit, offset = _clamp_paging(limit, offset)
    values = {
        "docket_id": docket_id,
        "applicant": applicant,
        "facility": facility,
        "matter_type": matter_type,
        "action_type": action_type,
        "county": county,
        "service_area": service_area,
        "bed_count_min": bed_count_min,
        "bed_count_max": bed_count_max,
        "year_filed": year_filed,
        "final_outcome": final_outcome,
        "final_decision_date_from": final_decision_date_from,
        "final_decision_date_to": final_decision_date_to,
        "highest_review_level": highest_review_level,
        "service_type": service_type,
        "phase": phase,
        "docket_variant": docket_variant,
        "completeness_flag": completeness_flag,
    }
    where, params = _build_where(values, MATTER_FILTERS, MATTER_EXISTS_FILTERS)

    select_sql = "SELECT m.* FROM con.matter m"
    count_sql = "SELECT COUNT(*) FROM con.matter m"
    head_params: list[Any] = []
    default_order = "m.docket_id ASC"
    if q:
        if fulltext_enabled():
            join = (
                f" JOIN CONTAINSTABLE(con.matter, {MATTER_FT_COLUMNS}, ?) ft"
                " ON ft.[KEY] = m.docket_id"
            )
            select_sql += join
            count_sql += join
            head_params = [_fts_query(q)]
            default_order = "ft.RANK DESC"
        else:
            clause, like_params = _like_clause(MATTER_LIKE_COLUMNS, q)
            where.append(clause)
            params.extend(like_params)

    result = _paged(
        conn,
        select_sql=select_sql,
        count_sql=count_sql,
        where=where,
        params=[*head_params, *params],
        order_by=_order_by(sort, MATTER_SORT, default_order),
        limit=limit,
        offset=offset,
    )
    for row in result["items"]:
        _parse_json_field(row, "completeness_flags")
    return result


def _resolve_docket(conn: Any, raw: str) -> str:
    """Resolve a path docket param (any variant form) to the owning matter id.

    Tries the canonical form (via normalize_docket) and the raw string against
    con.matter, then against con.matter_docket_variant. Raises 404 otherwise.
    """
    match = normalize_docket(raw)
    candidates: list[str] = []
    for candidate in ([match.canonical, *match.variants] if match else []) + [raw.strip()]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    placeholders = ", ".join("?" for _ in candidates)

    found = _scalar(
        conn,
        f"SELECT docket_id FROM con.matter WHERE docket_id IN ({placeholders})",
        candidates,
    )
    if found:
        return found
    found = _scalar(
        conn,
        "SELECT DISTINCT docket_id FROM con.matter_docket_variant "
        f"WHERE variant IN ({placeholders})",
        candidates,
    )
    if found:
        return found
    canonical_note = f" (canonical form {match.canonical!r})" if match else ""
    raise HTTPException(
        status_code=404,
        detail=(
            f"No matter found for docket {raw!r}{canonical_note}; "
            "checked con.matter and con.matter_docket_variant."
        ),
    )


@app.get("/matters/{docket_id}")
def get_matter(docket_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    resolved = _resolve_docket(conn, docket_id)
    rows = _query(conn, "SELECT * FROM con.matter WHERE docket_id = ?", [resolved])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Matter {resolved!r} not found.")
    matter = rows[0]
    _parse_json_field(matter, "completeness_flags")

    variants = _query(
        conn,
        "SELECT variant FROM con.matter_docket_variant WHERE docket_id = ? ORDER BY variant",
        [resolved],
    )
    service_types = _query(
        conn,
        "SELECT service_type FROM con.matter_service_type "
        "WHERE docket_id = ? ORDER BY service_type",
        [resolved],
    )
    phases = _query(
        conn, "SELECT phase FROM con.matter_phase WHERE docket_id = ? ORDER BY phase", [resolved]
    )
    documents = _query(
        conn,
        "SELECT * FROM con.document WHERE docket_id = ? ORDER BY doc_date, entry_id",
        [resolved],
    )
    for doc in documents:
        _parse_json_field(doc, "parties")
    events = _query(
        conn,
        "SELECT * FROM con.weekly_report_event WHERE docket_id = ? "
        "ORDER BY report_date, event_id",
        [resolved],
    )

    matter["docket_variants"] = [r["variant"] for r in variants]
    matter["service_types"] = [r["service_type"] for r in service_types]
    matter["phases_present"] = [r["phase"] for r in phases]
    matter["documents"] = documents
    matter["weekly_report_events"] = events
    return matter


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@app.get("/documents")
def list_documents(
    entry_id: int | None = None,
    docket_id: str | None = None,
    file_name: str | None = None,
    source_path: str | None = None,
    doc_type: str | None = None,
    decision_level: int | None = None,
    phase: str | None = None,
    outcome: str | None = None,
    validation_status: str | None = None,
    decision_maker: str | None = None,
    doc_date_from: date | None = None,
    doc_date_to: date | None = None,
    page_count_min: int | None = None,
    page_count_max: int | None = None,
    repo_created_from: datetime | None = None,
    repo_created_to: datetime | None = None,
    repo_modified_from: datetime | None = None,
    repo_modified_to: datetime | None = None,
    ocr_confidence_min: float | None = None,
    ocr_confidence_max: float | None = None,
    validated_by: str | None = None,
    validated_from: datetime | None = None,
    validated_to: datetime | None = None,
    party: str | None = None,
    template_name: str | None = None,
    ocr_status: str | None = None,
    duplicate_of: int | None = None,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    sort: str | None = None,
    conn: Any = Depends(get_db),
) -> dict[str, Any]:
    limit, offset = _clamp_paging(limit, offset)
    values = {
        "entry_id": entry_id,
        "docket_id": docket_id,
        "file_name": file_name,
        "source_path": source_path,
        "doc_type": doc_type,
        "decision_level": decision_level,
        "phase": phase,
        "outcome": outcome,
        "validation_status": validation_status,
        "decision_maker": decision_maker,
        "doc_date_from": doc_date_from,
        "doc_date_to": doc_date_to,
        "page_count_min": page_count_min,
        "page_count_max": page_count_max,
        "repo_created_from": repo_created_from,
        "repo_created_to": repo_created_to,
        "repo_modified_from": repo_modified_from,
        "repo_modified_to": repo_modified_to,
        "ocr_confidence_min": ocr_confidence_min,
        "ocr_confidence_max": ocr_confidence_max,
        "validated_by": validated_by,
        "validated_from": validated_from,
        "validated_to": validated_to,
        "party": party,
        "template_name": template_name,
        "ocr_status": ocr_status,
        "duplicate_of": duplicate_of,
    }
    where, params = _build_where(values, DOCUMENT_FILTERS)

    select_sql = "SELECT d.* FROM con.document d"
    count_sql = "SELECT COUNT(*) FROM con.document d"
    head_params: list[Any] = []
    default_order = "d.entry_id ASC"
    if q:
        if fulltext_enabled():
            join = (
                f" JOIN CONTAINSTABLE(con.document, {DOCUMENT_FT_COLUMNS}, ?) ft"
                " ON ft.[KEY] = d.entry_id"
            )
            select_sql += join
            count_sql += join
            head_params = [_fts_query(q)]
            default_order = "ft.RANK DESC"
        else:
            clause, like_params = _like_clause(DOCUMENT_LIKE_COLUMNS, q)
            where.append(clause)
            params.extend(like_params)

    result = _paged(
        conn,
        select_sql=select_sql,
        count_sql=count_sql,
        where=where,
        params=[*head_params, *params],
        order_by=_order_by(sort, DOCUMENT_SORT, default_order),
        limit=limit,
        offset=offset,
    )
    for row in result["items"]:
        _parse_json_field(row, "parties")
    return result


@app.get("/documents/{entry_id}")
def get_document(entry_id: int, conn: Any = Depends(get_db)) -> dict[str, Any]:
    rows = _query(conn, "SELECT * FROM con.document WHERE entry_id = ?", [entry_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Document with entry_id {entry_id} not found.")
    doc = rows[0]
    _parse_json_field(doc, "parties")
    return doc


@app.get("/dockets/{docket_id}/documents")
def docket_documents(docket_id: str, conn: Any = Depends(get_db)) -> dict[str, Any]:
    resolved = _resolve_docket(conn, docket_id)
    documents = _query(
        conn,
        "SELECT * FROM con.document WHERE docket_id = ? ORDER BY doc_date, entry_id",
        [resolved],
    )
    for doc in documents:
        _parse_json_field(doc, "parties")
    return {"docket_id": resolved, "items": documents, "total": len(documents)}


# ---------------------------------------------------------------------------
# Search (SQL full-text / LIKE fallback)
# ---------------------------------------------------------------------------

_SEARCH_SCOPES = ("matters", "documents", "events")


def _search_matters(conn: Any, q: str, limit: int) -> list[dict[str, Any]]:
    if fulltext_enabled():
        sql = (
            "SELECT m.*, ft.RANK AS rank FROM con.matter m "
            f"JOIN CONTAINSTABLE(con.matter, {MATTER_FT_COLUMNS}, ?) ft "
            "ON ft.[KEY] = m.docket_id "
            "ORDER BY ft.RANK DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        )
        rows = _query(conn, sql, [_fts_query(q), limit])
    else:
        clause, params = _like_clause(MATTER_LIKE_COLUMNS, q)
        sql = (
            f"SELECT m.* FROM con.matter m WHERE {clause} "
            "ORDER BY m.docket_id OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        )
        rows = _query(conn, sql, [*params, limit])
    for row in rows:
        _parse_json_field(row, "completeness_flags")
    return rows


def _search_documents(conn: Any, q: str, limit: int) -> list[dict[str, Any]]:
    if fulltext_enabled():
        sql = (
            "SELECT d.*, ft.RANK AS rank FROM con.document d "
            f"JOIN CONTAINSTABLE(con.document, {DOCUMENT_FT_COLUMNS}, ?) ft "
            "ON ft.[KEY] = d.entry_id "
            "ORDER BY ft.RANK DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        )
        rows = _query(conn, sql, [_fts_query(q), limit])
    else:
        clause, params = _like_clause(DOCUMENT_LIKE_COLUMNS, q)
        sql = (
            f"SELECT d.* FROM con.document d WHERE {clause} "
            "ORDER BY d.entry_id OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        )
        rows = _query(conn, sql, [*params, limit])
    for row in rows:
        _parse_json_field(row, "parties")
    return rows


def _search_events(conn: Any, q: str, limit: int) -> list[dict[str, Any]]:
    if fulltext_enabled():
        sql = (
            "SELECT e.*, ft.RANK AS rank FROM con.weekly_report_event e "
            f"JOIN CONTAINSTABLE(con.weekly_report_event, {EVENT_FT_COLUMNS}, ?) ft "
            "ON ft.[KEY] = e.event_id "
            "ORDER BY ft.RANK DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        )
        return _query(conn, sql, [_fts_query(q), limit])
    clause, params = _like_clause(EVENT_LIKE_COLUMNS, q)
    sql = (
        f"SELECT e.* FROM con.weekly_report_event e WHERE {clause} "
        "ORDER BY e.event_id OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    )
    return _query(conn, sql, [*params, limit])


@app.get("/search")
def search(
    q: str,
    scope: str = "all",
    limit: int = DEFAULT_LIMIT,
    conn: Any = Depends(get_db),
) -> dict[str, Any]:
    if scope != "all" and scope not in _SEARCH_SCOPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scope {scope!r}; one of: {', '.join((*_SEARCH_SCOPES, 'all'))}",
        )
    limit, _ = _clamp_paging(limit, 0)
    scopes = _SEARCH_SCOPES if scope == "all" else (scope,)
    searchers = {
        "matters": ("matter", _search_matters),
        "documents": ("document", _search_documents),
        "events": ("event", _search_events),
    }
    hits: list[dict[str, Any]] = []
    for name in scopes:
        hit_type, searcher = searchers[name]
        for row in searcher(conn, q, limit):
            rank = row.pop("rank", None)
            hits.append({"type": hit_type, "rank": rank, "record": row})
    hits.sort(key=lambda h: h["rank"] or 0, reverse=True)
    return {
        "query": q,
        "scope": scope,
        "fulltext": fulltext_enabled(),
        "hits": hits[:limit],
    }


# ---------------------------------------------------------------------------
# Changes
# ---------------------------------------------------------------------------


@app.get("/changes")
def list_changes(
    since: datetime | None = None,
    change_type: str | None = None,
    in_scope: bool | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    conn: Any = Depends(get_db),
) -> dict[str, Any]:
    limit, offset = _clamp_paging(limit, offset)
    where: list[str] = []
    params: list[Any] = []
    if since is not None:
        where.append("c.detected_at >= ?")
        params.append(since)
    if change_type is not None:
        where.append("c.change_type = ?")
        params.append(change_type)
    if in_scope is not None:
        where.append("c.in_scope = ?")
        params.append(1 if in_scope else 0)
    result = _paged(
        conn,
        select_sql="SELECT c.* FROM con.change_log c",
        count_sql="SELECT COUNT(*) FROM con.change_log c",
        where=where,
        params=params,
        order_by="c.detected_at DESC",
        limit=limit,
        offset=offset,
    )
    for row in result["items"]:
        _parse_json_field(row, "details")
    return result


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


class WatchlistCreate(BaseModel):
    docket_id: str | None = None
    entry_id: int | None = None
    path_prefix: str | None = None
    reason: str | None = None
    created_by: str | None = None

    @model_validator(mode="after")
    def _require_a_target(self) -> "WatchlistCreate":
        if self.docket_id is None and self.entry_id is None and self.path_prefix is None:
            raise ValueError("At least one of docket_id, entry_id, path_prefix is required.")
        return self


@app.get("/watchlist")
def list_watchlist(all: bool = False, conn: Any = Depends(get_db)) -> dict[str, Any]:
    sql = "SELECT w.* FROM con.watchlist w"
    params: list[Any] = []
    if not all:
        sql += " WHERE w.active = ?"
        params.append(1)
    sql += " ORDER BY w.watch_id DESC"
    items = _query(conn, sql, params)
    return {"items": items, "total": len(items)}


@app.post("/watchlist", status_code=201)
def create_watchlist(entry: WatchlistCreate, conn: Any = Depends(get_db)) -> dict[str, Any]:
    docket_id = entry.docket_id
    if docket_id:
        match = normalize_docket(docket_id)
        if match:
            docket_id = match.canonical
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO con.watchlist (docket_id, entry_id, path_prefix, reason, created_by) "
        "OUTPUT INSERTED.watch_id VALUES (?, ?, ?, ?, ?)",
        [docket_id, entry.entry_id, entry.path_prefix, entry.reason, entry.created_by],
    )
    row = cursor.fetchone()
    conn.commit()
    return {
        "watch_id": row[0] if row else None,
        "docket_id": docket_id,
        "entry_id": entry.entry_id,
        "path_prefix": entry.path_prefix,
        "reason": entry.reason,
        "created_by": entry.created_by,
        "active": True,
    }


@app.delete("/watchlist/{watch_id}")
def deactivate_watchlist(watch_id: int, conn: Any = Depends(get_db)) -> dict[str, Any]:
    # Soft-deactivate only; watchlist rows are never hard-deleted.
    cursor = conn.cursor()
    cursor.execute("UPDATE con.watchlist SET active = 0 WHERE watch_id = ?", [watch_id])
    if cursor.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail=f"Watchlist entry {watch_id} not found.")
    conn.commit()
    return {"watch_id": watch_id, "active": False}


# ---------------------------------------------------------------------------
# Weekly report events
# ---------------------------------------------------------------------------


@app.get("/reports/events")
def report_events(
    docket_id: str | None = None,
    section: str | None = None,
    since: date | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    conn: Any = Depends(get_db),
) -> dict[str, Any]:
    limit, offset = _clamp_paging(limit, offset)
    where: list[str] = []
    params: list[Any] = []
    if docket_id is not None:
        match = normalize_docket(docket_id)
        where.append("e.docket_id = ?")
        params.append(match.canonical if match else docket_id)
    if section is not None:
        where.append("e.section = ?")
        params.append(section)
    if since is not None:
        where.append("e.report_date >= ?")
        params.append(since)
    return _paged(
        conn,
        select_sql="SELECT e.* FROM con.weekly_report_event e",
        count_sql="SELECT COUNT(*) FROM con.weekly_report_event e",
        where=where,
        params=params,
        order_by="e.report_date DESC, e.event_id DESC",
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Azure AI Search + Azure OpenAI routes (api/semantic.py) and 503 mapping
# ---------------------------------------------------------------------------

app.include_router(semantic.router)


@app.exception_handler(ConfigurationError)
async def _configuration_error_handler(request: Any, exc: ConfigurationError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})
