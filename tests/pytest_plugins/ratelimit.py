"""
The ratelimit fixtures.

Rate limits count requests in fixed windows (e.g. one minute): a test that
crossed the end of a window would see its counters start again. Tests of rate
limits stop the clock at the start of a window instead.
"""

from datetime import UTC, datetime

import pytest
from time_machine import TimeMachineFixture


@pytest.fixture
def start_of_minute(time_machine: TimeMachineFixture) -> datetime:
    """Stop the clock at the start of a minute (and of an hour)."""
    now = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
    time_machine.move_to(now, tick=False)
    return now
