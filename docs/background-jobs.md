# Background jobs with Celery

Background jobs run on [Celery](https://docs.celeryq.dev/): beat sends the scheduled tasks to Redis (the Valkey image), and the worker runs them. `docker compose up` starts all three.

- `app/jobs/worker.py` holds the Celery app and the schedule: `purge` (expired tokens and rate limit counters) runs every day at 03:00 UTC.
- `app/jobs/tasks.py` holds the tasks. A task is a plain function that opens its own database session with `run_with_session`; send one from an endpoint with `task.delay(...)`, after the commit of what it reads.
- A task is acknowledged when it finishes, so one interrupted by a worker that dies runs again: write tasks that do no harm when they run twice.
- Every log line of a task carries its `task_id` and `task_name`.
- A worker runs `FASTAPI_CELERY_WORKER_CONCURRENCY` processes (2, ~75 MiB each): Celery would otherwise start one per CPU of the host.

Run a task by hand with `docker compose run --rm backend celery --app app.jobs.worker call app.jobs.tasks.purge`.
