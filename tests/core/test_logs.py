"""The core logs tests."""

import json
import logging
import re
import sys

import structlog
from dirty_equals import IsDatetime, IsStr

from app.core.config import Settings
from app.core.logs import build_formatter, logging_config


def test_build_formatter_json() -> None:
    """Test a standard library log line becomes a JSON object with the context."""
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            "uvicorn.error", logging.ERROR, __file__, 1, "Worker %s", ("1",), None
        )
        record.exc_info = sys.exc_info()
    with structlog.contextvars.bound_contextvars(request_id="abc"):
        line = build_formatter("json").format(record)
    assert json.loads(line) == {
        "event": "Worker 1",
        "exception": IsStr(regex=r"Traceback .*RuntimeError: boom", regex_flags=re.S),
        "level": "error",
        "logger": "uvicorn.error",
        "request_id": "abc",
        "timestamp": IsDatetime(iso_string=True),
    }


def test_build_formatter_console() -> None:
    """Test a log line is a readable key-value line in the console format."""
    record = logging.LogRecord(
        "uvicorn.error", logging.INFO, __file__, 1, "Worker %s", ("1",), None
    )
    with structlog.contextvars.bound_contextvars(request_id="abc"):
        line = build_formatter("console").format(record)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", line)
    assert plain == IsStr(regex=r"\S+ \[info\s*\] Worker 1 +\[uvicorn\.error\] .*")
    assert "request_id=abc" in plain


def test_logging_config() -> None:
    """Test the format and the level come from the settings."""
    config = logging_config(Settings(LOG_FORMAT="json", LOG_LEVEL="WARNING"))
    assert config["formatters"]["structlog"]["log_format"] == "json"
    assert config["handlers"]["default"]["level"] == "WARNING"
    assert config["root"]["level"] == "WARNING"
