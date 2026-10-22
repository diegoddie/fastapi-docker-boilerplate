"""The jobs package worker: the Celery app that the worker and beat run."""

import tempfile
from pathlib import Path
from typing import Any

import structlog
from celery import Celery, Task, signals
from celery.schedules import crontab

import app.core.models  # noqa: F401  # side-effect: register every model
from app.core.config import settings
from app.core.logs import configure_logging
from app.core.sentry import init_sentry  # copier:sentry

init_sentry(settings)  # copier:sentry

celery_app = Celery(
    "app", broker=str(settings.CELERY_BROKER_URL), include=["app.jobs.tasks"]
)
celery_app.conf.update(
    beat_schedule={
        "purge": {
            "task": "app.jobs.tasks.purge",
            "schedule": crontab(hour=3, minute=0),
        },
    },
    # Why: beat keeps the time of the last runs in this file and rebuilds it when
    # it is missing, so it stays out of the source tree.
    beat_schedule_filename=str(Path(tempfile.gettempdir()) / "celerybeat-schedule"),
    broker_connection_retry_on_startup=True,
    # Why: a task is acknowledged once it is done, so one interrupted by a worker
    # that dies runs again on another: tasks must be safe to run twice.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Why: nothing waits for the return value of a task, so there is no result
    # backend to run.
    task_ignore_result=True,
    timezone="UTC",
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    # Why: with late acknowledgement, a worker reserves only the task it runs.
    worker_prefetch_multiplier=1,
)


@signals.setup_logging.connect
def setup_logging(**kwargs: Any) -> None:
    """Send Celery's log lines through structlog, like every other line."""
    configure_logging(settings)


@signals.task_prerun.connect
def bind_task_context(task_id: str, task: Task[Any, Any], **kwargs: Any) -> None:
    """Write the task's id and name on every line it logs."""
    structlog.contextvars.bind_contextvars(task_id=task_id, task_name=task.name)


@signals.task_postrun.connect
def clear_task_context(**kwargs: Any) -> None:
    """Forget the task's context once it is done."""
    structlog.contextvars.clear_contextvars()
