"""Azure Functions entry points (Python v2 programming model).

Thin decorated wrappers around processing.py, which holds all logic and is
unit-testable without the Functions runtime. Deployment stages common/ and
ingest/ next to this file (see deploy.sh) so `from ingest...` imports resolve
in Azure; processing.py sits in the same folder, so `import processing` works
both in Azure and locally under `func start`.
"""

import logging
from typing import Any

import azure.functions as func

import processing

app = func.FunctionApp()


def _container_client(container: str) -> Any:
    return processing.blob_service_client().get_container_client(container)


@app.blob_trigger(
    arg_name="blob", path="%SNAPSHOT_CONTAINER%/{name}", connection="AzureWebJobsStorage"
)
def snapshot_blob_trigger(blob: func.InputStream) -> None:
    """New Laserfiche index snapshot (.jsonl.gz): diff against the previous one.

    First-ever snapshot is registered as the baseline (no diff). Failures are
    recorded in con.processed_blob and re-raised so the Functions retry /
    poison-blob handling engages.
    """
    container, name = processing.split_blob_path(blob.name or "")
    conn = processing.connect()
    try:
        detail = processing.process_snapshot_blob(conn, _container_client(container), name)
        logging.info("snapshot_blob_trigger %s/%s: %s", container, name, detail)
    finally:
        conn.close()


@app.blob_trigger(
    arg_name="blob", path="%REPORT_CONTAINER%/{name}", connection="AzureWebJobsStorage"
)
def report_blob_trigger(blob: func.InputStream) -> None:
    """New DCH weekly report PDF: extract text, parse, load events."""
    container, name = processing.split_blob_path(blob.name or "")
    conn = processing.connect()
    try:
        detail = processing.process_report_blob(conn, _container_client(container), name)
        logging.info("report_blob_trigger %s/%s: %s", container, name, detail)
    finally:
        conn.close()


@app.timer_trigger(arg_name="timer", schedule="%SWEEP_CRON%")
def daily_sweep(timer: func.TimerRequest) -> None:
    """Catch-up sweep: process any blob in either container that con.processed_blob
    does not record as succeeded (heals missed trigger events and failures)."""
    if timer.past_due:
        logging.info("daily_sweep: timer is past due")
    conn = processing.connect()
    try:
        counts = processing.sweep_containers(conn, processing.blob_service_client())
        logging.info("daily_sweep: %s", counts)
    finally:
        conn.close()
