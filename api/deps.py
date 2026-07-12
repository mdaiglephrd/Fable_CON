"""Shared DB plumbing for api.main and the research-layer routers.

Split out of api/main.py so api/routers/* can use the same ``get_db``
dependency and query helpers without importing api.main (which would be a
circular import). api.main imports these back under its original private
names; behavior is identical to the pre-refactor helpers.

All SQL is parameterized; column names come only from fixed whitelist maps,
never from user input.
"""

import json
import re
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import HTTPException

from common.docket import normalize_docket


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


def rows_to_dicts(cursor: Any) -> list[dict[str, Any]]:
    if not cursor.description:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def query(conn: Any, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    return rows_to_dicts(cursor)


def scalar(conn: Any, sql: str, params: list[Any]) -> Any:
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    row = cursor.fetchone()
    return row[0] if row else None


def parse_json_field(row: dict[str, Any], field: str) -> None:
    """Parse a JSON text column to a list/object in place (None on bad JSON)."""
    value = row.get(field)
    if isinstance(value, str):
        try:
            row[field] = json.loads(value)
        except ValueError:
            row[field] = None


def resolve_docket(conn: Any, raw: str) -> str:
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

    found = scalar(
        conn,
        f"SELECT docket_id FROM con.matter WHERE docket_id IN ({placeholders})",
        candidates,
    )
    if found:
        return found
    found = scalar(
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


def drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop None-valued keys so responses omit fields the JS contract omits."""
    return {key: value for key, value in payload.items() if value is not None}


def slug_id(name: str) -> str:
    """URL-safe id: slug of ``name`` plus a short random suffix (fits 60 chars)."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "item"
    return f"{slug}-{uuid.uuid4().hex[:6]}"
