#!/usr/bin/env bash
# Check that a Celery worker runs a job end to end: the job goes through the
# broker, the worker runs it on the database and logs that it finished (CI).

set -euo pipefail

docker compose up --detach worker
docker compose run --rm backend celery --app app.jobs.worker call app.jobs.tasks.purge
if ! timeout 120 sh -c 'until docker compose logs worker | grep -q purge_finished; do sleep 2; done'; then
    docker compose logs worker
    exit 1
fi
docker compose logs worker | grep purge_finished
