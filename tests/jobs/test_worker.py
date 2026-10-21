"""The jobs package worker tests."""

from celery import signals
from celery.schedules import crontab
from pytest_mock import MockerFixture

from app.core.config import settings
from app.jobs.tasks import purge
from app.jobs.worker import celery_app


def test_beat_schedule() -> None:
    """Test beat sends the purge every day at 03:00 UTC."""
    assert str(celery_app.conf.timezone) == "UTC"
    assert celery_app.conf.beat_schedule == {
        "purge": {"task": purge.name, "schedule": crontab(hour=3, minute=0)}
    }


def test_worker_concurrency() -> None:
    """Test the worker runs as many processes as configured, not one per CPU."""
    assert celery_app.conf.worker_concurrency == settings.CELERY_WORKER_CONCURRENCY


def test_setup_logging(mocker: MockerFixture) -> None:
    """Test Celery leaves the logging configuration to the app."""
    configure_logging = mocker.patch("app.jobs.worker.configure_logging")
    signals.setup_logging.send(sender=None, loglevel="INFO")
    configure_logging.assert_called_once_with(settings)
