import io
import json
import logging

from common.json_logging import configure_json_logging


def _capture(logger_name: str) -> io.StringIO:
    logger = configure_json_logging(logger_name)
    stream = io.StringIO()
    for handler in logger.handlers:
        handler.stream = stream
    return stream


def test_log_record_is_one_json_object_per_line():
    stream = _capture("tag_test.basic")
    logging.getLogger("tag_test.basic").info("processed file")

    record = json.loads(stream.getvalue().strip())
    assert record["message"] == "processed file"
    assert record["level"] == "INFO"
    assert record["logger"] == "tag_test.basic"
    assert "timestamp" in record


def test_extra_fields_are_included_verbatim():
    stream = _capture("tag_test.extra")
    logging.getLogger("tag_test.extra").info(
        "processed file", extra={"file_path": "/ssd/a.pdf", "entry_id": 1234}
    )

    record = json.loads(stream.getvalue().strip())
    assert record["file_path"] == "/ssd/a.pdf"
    assert record["entry_id"] == 1234


def test_configuring_twice_does_not_duplicate_handlers():
    logger_a = configure_json_logging("tag_test.dup")
    logger_b = configure_json_logging("tag_test.dup")

    assert logger_a is logger_b
    assert len(logger_a.handlers) == 1
