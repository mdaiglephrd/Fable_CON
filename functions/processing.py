"""Shared blob-processing logic for the Azure Functions app.

Plain module: no azure.functions import, and DB / ingest imports are lazy so
this file can be imported and unit-tested without pyodbc's ODBC runtime or the
ingest modules present (tests monkeypatch the ``_index_diff`` / ``_report_parser``
hooks). function_app.py is a thin decorated wrapper around these functions;
the daily sweep and the blob triggers share the same code paths.

Every processed blob is recorded in ``con.processed_blob`` keyed by
"container/name" with status 'succeeded' or 'failed'. A 'failed' row does not
block reprocessing, so Functions retries and the daily sweep can heal failures;
only 'succeeded' blobs are skipped.
"""

import logging
import os
import re
import tempfile
from datetime import date
from typing import Any, Callable

log = logging.getLogger(__name__)

SNAPSHOT_SUFFIX = ".jsonl.gz"
REPORT_SUFFIX = ".pdf"


# --- config / clients (all lazy: nothing here touches env at import time) ---


def snapshot_container() -> str:
    return os.environ.get("SNAPSHOT_CONTAINER", "index-snapshots")


def report_container() -> str:
    return os.environ.get("REPORT_CONTAINER", "weekly-reports")


def connect() -> Any:
    """Open the Azure SQL connection (lazy import: needs the ODBC runtime)."""
    from common.db import get_connection

    return get_connection()


def blob_service_client() -> Any:
    """BlobServiceClient from STORAGE_CONNECTION / AzureWebJobsStorage, or
    DefaultAzureCredential against STORAGE_ACCOUNT_URL (managed identity)."""
    from azure.storage.blob import BlobServiceClient

    conn_str = os.environ.get("STORAGE_CONNECTION") or os.environ.get("AzureWebJobsStorage")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)
    account_url = os.environ.get("STORAGE_ACCOUNT_URL")
    if not account_url:
        raise RuntimeError(
            "storage not configured: set STORAGE_CONNECTION, AzureWebJobsStorage, "
            "or STORAGE_ACCOUNT_URL (with a managed identity / az login)"
        )
    from azure.identity import DefaultAzureCredential

    return BlobServiceClient(account_url, credential=DefaultAzureCredential())


def _index_diff() -> Any:
    """Lazy import hook for ingest.index_diff (tests monkeypatch this)."""
    from ingest import index_diff

    return index_diff


def _report_parser() -> Any:
    """Lazy import hook for ingest.weekly_report_parser (tests monkeypatch this)."""
    from ingest import weekly_report_parser

    return weekly_report_parser


# --- small helpers ---


def blob_key(container: str, blob_name: str) -> str:
    """con.processed_blob key format per DESIGN.md: 'container/name'."""
    return f"{container}/{blob_name}"


def split_blob_path(path: str) -> tuple[str, str]:
    """Split a trigger blob path 'container/dir/name.ext' into (container, name)."""
    container, sep, name = path.partition("/")
    if not sep or not container or not name:
        raise ValueError(f"expected 'container/name', got {path!r}")
    return container, name


def already_succeeded(conn: Any, container: str, blob_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT status FROM con.processed_blob WHERE blob_name = ?",
        blob_key(container, blob_name),
    )
    row = cur.fetchone()
    return row is not None and row[0] == "succeeded"


def record_processed(conn: Any, container: str, blob_name: str, status: str, detail: str) -> None:
    """Upsert the processed_blob row (retries update in place). Caller commits."""
    conn.cursor().execute(
        """
        MERGE con.processed_blob AS t
        USING (SELECT ? AS blob_name) AS s
           ON t.blob_name = s.blob_name
        WHEN MATCHED THEN UPDATE SET status = ?, detail = ?, processed_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (blob_name, status, detail) VALUES (s.blob_name, ?, ?);
        """,
        blob_key(container, blob_name),
        status,
        detail,
        status,
        detail,
    )


_DATE_IN_NAME_RE = re.compile(r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})")


def snapshot_date_from_name(blob_name: str) -> date | None:
    """Best-effort snapshot date from a blob name like 'index-2026-07-04.jsonl.gz'."""
    m = _DATE_IN_NAME_RE.search(blob_name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def latest_snapshot(conn: Any) -> tuple[int, str] | None:
    """(snapshot_id, blob_name) of the most recent registered snapshot, if any."""
    cur = conn.cursor()
    cur.execute(
        "SELECT TOP 1 snapshot_id, blob_name FROM con.index_snapshot ORDER BY snapshot_id DESC"
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else None


def _download_to_temp(container_client: Any, blob_name: str, suffix: str) -> str:
    """Download a blob to a named temp file; caller removes it."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            container_client.download_blob(blob_name).readinto(fh)
    except Exception:
        os.unlink(path)
        raise
    return path


def _remove_quietly(*paths: str) -> None:
    for path in paths:
        try:
            os.unlink(path)
        except OSError:
            pass


# --- snapshot processing ---


def process_snapshot_blob(conn: Any, container_client: Any, blob_name: str) -> str:
    """Process one index snapshot blob; returns a one-line detail summary.

    Skips blobs already recorded as 'succeeded'. On failure records a 'failed'
    processed_blob row and re-raises so the Functions retry / poison-blob
    handling engages.
    """
    container = container_client.container_name
    if not blob_name.lower().endswith(SNAPSHOT_SUFFIX):
        return f"ignored (not *{SNAPSHOT_SUFFIX})"
    if already_succeeded(conn, container, blob_name):
        return "skipped (already processed)"
    try:
        detail = _ingest_snapshot(conn, container_client, blob_name)
    except Exception as exc:
        conn.rollback()
        record_processed(conn, container, blob_name, "failed", f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
    record_processed(conn, container, blob_name, "succeeded", detail)
    conn.commit()
    return detail


def _ingest_snapshot(conn: Any, container_client: Any, blob_name: str) -> str:
    mod = _index_diff()
    prior = latest_snapshot(conn)
    if prior is None:
        return _register_baseline(conn, mod, container_client, blob_name)
    prior_id, prior_blob = prior
    if prior_blob == blob_name:
        return "already registered in con.index_snapshot; no diff run"
    old_path = _download_to_temp(container_client, prior_blob, SNAPSHOT_SUFFIX)
    try:
        new_path = _download_to_temp(container_client, blob_name, SNAPSHOT_SUFFIX)
    except Exception:
        _remove_quietly(old_path)
        raise
    try:
        diff = mod.diff_snapshots(mod.read_snapshot(old_path), mod.read_snapshot(new_path))
        mod.apply_diff(conn, diff, prior_blob, blob_name)
    finally:
        _remove_quietly(old_path, new_path)
    return (
        f"diff vs {prior_blob} (snapshot_id={prior_id}): added={len(diff.added)}"
        f" modified={len(diff.modified)} deleted={len(diff.deleted)}"
    )


def _register_baseline(conn: Any, mod: Any, container_client: Any, blob_name: str) -> str:
    """First-ever snapshot: register it in con.index_snapshot, no diff."""
    path = _download_to_temp(container_client, blob_name, SNAPSHOT_SUFFIX)
    try:
        entry_count = 0
        max_entry_id: int | None = None
        for record in mod.read_snapshot(path):
            entry_count += 1
            entry_id = record.get("id")
            if entry_id is not None and (max_entry_id is None or entry_id > max_entry_id):
                max_entry_id = entry_id
    finally:
        _remove_quietly(path)
    conn.cursor().execute(
        "INSERT INTO con.index_snapshot (blob_name, snapshot_date, entry_count, max_entry_id)"
        " VALUES (?, ?, ?, ?)",
        blob_name,
        snapshot_date_from_name(blob_name),
        entry_count,
        max_entry_id,
    )
    return f"baseline snapshot registered: entries={entry_count} max_entry_id={max_entry_id}"


# --- weekly report processing ---


def process_report_blob(conn: Any, container_client: Any, blob_name: str) -> str:
    """Process one weekly report PDF; returns a one-line detail summary."""
    container = container_client.container_name
    if not blob_name.lower().endswith(REPORT_SUFFIX):
        return f"ignored (not *{REPORT_SUFFIX})"
    if already_succeeded(conn, container, blob_name):
        return "skipped (already processed)"
    try:
        detail = _ingest_report(conn, container_client, blob_name)
    except Exception as exc:
        conn.rollback()
        record_processed(conn, container, blob_name, "failed", f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
    record_processed(conn, container, blob_name, "succeeded", detail)
    conn.commit()
    return detail


def _ingest_report(conn: Any, container_client: Any, blob_name: str) -> str:
    mod = _report_parser()
    pdf_path = _download_to_temp(container_client, blob_name, REPORT_SUFFIX)
    try:
        text = mod.extract_text(pdf_path)
    finally:
        _remove_quietly(pdf_path)
    parse = mod.parse_report_text(text, report_file=blob_name)
    stats = mod.load_events(conn, parse, blob_name)
    return (
        f"report_date={parse.report_date} events={len(parse.events)}"
        f" warnings={len(parse.warnings)}; {stats}"
    )


# --- catch-up sweep ---


def succeeded_keys(conn: Any) -> set[str]:
    """All 'container/name' keys already processed successfully."""
    cur = conn.cursor()
    cur.execute("SELECT blob_name FROM con.processed_blob WHERE status = 'succeeded'")
    return {row[0] for row in cur.fetchall()}


def sweep_containers(conn: Any, service_client: Any) -> dict[str, int]:
    """Process every blob in both containers not yet recorded as succeeded.

    Failures are recorded by the per-blob handlers and logged; the sweep keeps
    going so one bad blob cannot starve the rest of the catch-up.
    """
    done = succeeded_keys(conn)
    counts = {"processed": 0, "failed": 0, "skipped": 0}
    handlers: list[tuple[str, Callable[[Any, Any, str], str]]] = [
        (snapshot_container(), process_snapshot_blob),
        (report_container(), process_report_blob),
    ]
    for container, handler in handlers:
        container_client = service_client.get_container_client(container)
        for blob in container_client.list_blobs():
            name = getattr(blob, "name", blob)
            if blob_key(container, name) in done:
                counts["skipped"] += 1
                continue
            try:
                detail = handler(conn, container_client, name)
            except Exception:
                log.exception("sweep: processing %s failed", blob_key(container, name))
                counts["failed"] += 1
            else:
                log.info("sweep: %s: %s", blob_key(container, name), detail)
                counts["processed"] += 1
    return counts
