"""The jobs package tasks."""

import structlog

from app.cli.purge import execute_purge
from app.core.database import run_with_session
from app.jobs.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task
def purge() -> None:
    """Delete the expired tokens and rate limit counters (beat sends it daily)."""
    deleted = run_with_session(execute_purge)
    logger.info("purge_finished", deleted=deleted)
