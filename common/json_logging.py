"""Structured (JSON) logging for the tag ETL pipeline.

The rest of this repo logs with plain stdlib `logging` text records (see
ingest/load_tags.py, ingest/load_document_text.py). This pipeline's own
quality bar calls for structured JSON logs on anything that touches the
filesystem or the database, so `ingest/tag_*` modules use this helper
instead -- a deliberate, scoped divergence, not a repo-wide change.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_RESERVED = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Formats each LogRecord as one JSON object per line.

    Any extra=... keyword fields passed to a log call are included verbatim
    (e.g. log.info("processed file", extra={"file_path": p, "entry_id": e})).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_json_logging(name: str, *, level: int = logging.INFO) -> logging.Logger:
    """Return a logger under `name` that emits one JSON object per line to stderr.

    Idempotent: calling this more than once for the same name does not stack
    duplicate handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger
