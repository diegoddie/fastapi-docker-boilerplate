# 0015. Background jobs with Celery, as an option

- Status: Accepted
- Date: 2026-10-21

## Context

The app has one scheduled job, `purge`, and projects soon need more: reports,
imports, calls to slow services, emails retried until they go out. Running
them takes a scheduler, and something that runs the code outside the requests.
Many projects need no more than a command run once a day; others need a queue.

## Decision

- Generating a project asks `background_jobs`: `cron` (the default) or
  `celery`.
- With `cron`, a job is a management command (`python -m app.cli.main purge`)
  that the platform schedules (crontab, Kubernetes CronJob); there is no other
  service to run.
- With `celery`:
  - `app/jobs/worker.py` holds the Celery app; beat sends the scheduled tasks
    (`purge` at 03:00 UTC) to Redis (the Valkey image), and workers run them.
    There is no result backend: nothing waits for a task's return value.
  - A task is a plain function that runs its logic with `run_with_session`,
    which creates an engine without a pool for each run and disposes it before
    the run's event loop closes: connections cannot be shared across the event
    loops of successive tasks.
  - Tasks are acknowledged once done, and given back to the queue when a worker
    dies, so they must be safe to run twice.
  - Celery logs through structlog (the `setup_logging` signal), and every line
    of a task carries its `task_id` and `task_name`.
  - A worker runs `CELERY_WORKER_CONCURRENCY` processes (2), not one per CPU of
    the host: each one takes ~75 MiB, and 20 of them took 1.5 GiB.
  - Compose runs `worker`, `beat` and `redis` next to the backend, from its
    image; the CI sends a job through a real worker.

## Consequences

- With `cron`: nothing more to run or monitor, but no queue, no retries, and
  every run pays the start of a process.
- With `celery`: Redis and two more processes to run and monitor; the API can
  hand slow work to the workers (`task.delay()`, after the commit), and tasks can
  retry. Beat must run as a single instance, or every scheduled task is sent
  twice.
- `run_with_session` serves the commands and the tasks alike.

## Alternatives considered

- **arq, taskiq, Dramatiq**: async-native or lighter, but Celery is the one most
  teams know, with beat, retries, monitoring (Flower) and a Sentry integration.
- **APScheduler inside the web process**: no other service, but every gunicorn
  worker and every replica would run the job, and a long job competes with the
  requests.
- **FastAPI's `BackgroundTasks`**: used for the emails (ADR 0012), right for short
  work after a response, but with no schedule, no retry, and lost on a restart.
- **Celery only**: a broker and two services for one daily job is too much for
  many projects, so it stays an option.
