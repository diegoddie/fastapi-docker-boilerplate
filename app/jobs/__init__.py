"""
The jobs package: background jobs, run by Celery workers.

Beat sends the scheduled tasks to the broker (Redis) and the workers run them::

    celery --app app.jobs.worker worker   # runs the tasks
    celery --app app.jobs.worker beat     # sends the scheduled ones

A task is a plain function that opens its own database session with
``run_with_session``; send one from the API with ``task.delay()``, after the
commit of what it reads.
"""
