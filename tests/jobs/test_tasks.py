"""The jobs package tasks tests."""

from collections.abc import Callable
from typing import Any

import structlog
from dirty_equals import IsDatetime, IsStr
from pytest_mock import MockerFixture

from app.cli.purge import execute_purge
from app.jobs.tasks import purge


def test_purge(
    mocker: MockerFixture, log_events: Callable[[str], list[dict[str, Any]]]
) -> None:
    """Test the purge runs on a session of its own and logs what it deleted."""
    run_with_session = mocker.patch(
        "app.jobs.tasks.run_with_session", return_value={"refresh tokens": 2}
    )
    result = purge.apply()
    assert result.successful()
    run_with_session.assert_called_once_with(execute_purge)
    assert log_events("purge_finished") == [
        {
            "event": "purge_finished",
            "deleted": {"refresh tokens": 2},
            "task_id": result.id,
            "task_name": "app.jobs.tasks.purge",
            "logger": "app.jobs.tasks",
            "level": "info",
            "timestamp": IsDatetime(iso_string=True),
        }
    ]
    assert result.id == IsStr(min_length=1)
    # The context of the task does not leak into what runs next.
    assert structlog.contextvars.get_contextvars() == {}
