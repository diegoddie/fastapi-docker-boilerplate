"""
The core logs.

Every log line goes through structlog, whether it comes from the application or
from a standard library logger (uvicorn, gunicorn, SQLAlchemy, any library). In
remote environments a line is a JSON object, locally a colored key-value line;
both carry the context bound to the current request (``request_id``,
``user_id``). Log with an event name and keyword arguments::

    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("todo_created", todo_id=str(todo.id))
"""

import logging
import logging.config
from typing import Any, Literal

import structlog
from structlog.typing import Processor

from app.core.config import Settings

# Why: these run for every line, from structlog or from the standard library, so
# all lines have the same fields.
SHARED_PROCESSORS: tuple[Processor, ...] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
)


def build_formatter(
    log_format: Literal["console", "json"],
) -> structlog.stdlib.ProcessorFormatter:
    """Return the formatter that renders every log line."""
    renderers: list[Processor]
    if log_format == "json":
        renderers = [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Why: local variables in tracebacks would print passwords and tokens.
        traceback_formatter = structlog.dev.RichTracebackFormatter(show_locals=False)
        renderers = [
            structlog.dev.ConsoleRenderer(exception_formatter=traceback_formatter)
        ]
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *renderers,
        ],
    )


def logging_config(app_settings: Settings) -> dict[str, Any]:
    """Return the standard library logging configuration (``dictConfig``)."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {"()": build_formatter, "log_format": app_settings.log_format}
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
                "level": app_settings.LOG_LEVEL,
                "stream": "ext://sys.stdout",
            },
            "null": {"class": "logging.NullHandler"},
        },
        "root": {"handlers": ["default"], "level": app_settings.LOG_LEVEL},
        "loggers": {
            # Why: uvicorn and gunicorn attach handlers with their own format;
            # without them, their lines reach the root handler like all others.
            "gunicorn.error": {"handlers": [], "propagate": True},
            "uvicorn": {"handlers": [], "propagate": True},
            "uvicorn.error": {"handlers": [], "propagate": True},
            # Why: RequestContextMiddleware logs a richer line for every request.
            "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": True},
            # Why: SQLAlchemy logs every statement when INFO is enabled; only an
            # engine created with echo=True (the app's one, in DEBUG) should.
            "sqlalchemy.engine": {"level": "WARNING"},
            # Why: an engine with echo=True adds a handler of its own here unless
            # one exists, and every statement would be written twice.
            "sqlalchemy.engine.Engine": {"handlers": ["null"], "propagate": True},
        },
    }


def configure_logging(app_settings: Settings) -> None:
    """Send every log line through structlog; each entry point calls it once."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *SHARED_PROCESSORS,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.config.dictConfig(logging_config(app_settings))


def get_request_id() -> str | None:
    """Return the id of the request being handled, if any."""
    request_id: str | None = structlog.contextvars.get_contextvars().get("request_id")
    return request_id
