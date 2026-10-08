"""Gunicorn configuration file."""

import os

# Logging
# https://docs.gunicorn.org/en/stable/settings.html#logging

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
accesslog = "-"
errorlog = "-"
loglevel = "info"

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
