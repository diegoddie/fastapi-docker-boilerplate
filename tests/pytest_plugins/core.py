"""
The core fixtures.

``log_events`` reads what the application logged: structlog hands each event to
the standard library as a dict, which pytest's ``caplog`` captures.
"""

import logging
from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def log_events(
    caplog: pytest.LogCaptureFixture,
) -> Callable[[str], list[dict[str, Any]]]:
    """Return a function listing the structlog events logged with a name."""
    caplog.set_level(logging.DEBUG)

    def events(name: str) -> list[dict[str, Any]]:
        """Return the events logged with the name, oldest first."""
        return [
            record.msg
            for record in caplog.records
            if isinstance(record.msg, dict) and record.msg.get("event") == name
        ]

    return events
