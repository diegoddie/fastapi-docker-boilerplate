"""Gunicorn configuration file."""

import os

from app.core.config import settings
from app.core.logs import logging_config

# Logging
# https://docs.gunicorn.org/en/stable/settings.html#logging

# Why: the master process (workers starting, timeouts) logs in the same format as
# the app; requests are logged by the app's middleware, not by gunicorn.
logconfig_dict = logging_config(settings)

# Server Socket
# https://docs.gunicorn.org/en/stable/settings.html#server-socket

bind = "0.0.0.0:" + os.getenv("INTERNAL_SERVICE_PORT", "8000")

# Worker Processes
# https://docs.gunicorn.org/en/stable/settings.html#worker-processes

worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))

# Temporary Directory
# https://docs.gunicorn.org/en/stable/settings.html#worker-tmp-dir

worker_tmp_dir = "/dev/shm"  # noqa: S108  # nosec B108
