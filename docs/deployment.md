# Deploying to production

The `remote` image runs gunicorn with uvicorn workers as a non-root user and applies the migrations when it starts. Before going live:

- [ ] **Secrets**: a random `FASTAPI_SECRET_KEY` (`openssl rand -hex 32`), never the one in `.env_template`; `FASTAPI_DATABASE_URL` pointing to the production database.
- [ ] **Environment**: `FASTAPI_ENVIRONMENT=remote` (the default): API docs off, JSON logs.
- [ ] **CORS**: `FASTAPI_CORS_ALLOWED_ORIGINS` lists the frontend origins.
- [ ] **Behind a load balancer or reverse proxy**: set `FORWARDED_ALLOW_IPS` to its addresses (or `*` if only the proxy can reach the app). If it is missing, nothing fails: every user simply gets the proxy's address and the whole site shares the per-IP rate limits (30 logins per minute, 10 registrations per hour).
- [ ] **Memory**: each worker takes ~80 MiB, plus 64 MiB for each password hash running (`FASTAPI_PASSWORD_HASH_CONCURRENCY`). With the defaults (2 workers, 2 hashes each) the container idles at ~250 MiB and peaks at ~500 MiB during a burst of logins: give it at least 768 MiB, and recompute when you change `WEB_CONCURRENCY`.
- [ ] **Database connections**: each worker opens up to `FASTAPI_DATABASE_POOL_SIZE` + `FASTAPI_DATABASE_MAX_OVERFLOW` connections (15), and a CSV download holds one for its whole duration. Containers × workers × 15 must stay below the database's `max_connections` (100 by default on PostgreSQL), or put a pooler (PgBouncer) in between.
- [ ] **Scheduled job**: `python -m app.cli.main purge` once a day (see [Scheduled jobs](scheduled-jobs.md)). <!-- copier:!celery -->
- [ ] **Payments** (if used): `FASTAPI_POLAR_ENVIRONMENT=production` with a production token and product ids, and a webhook on the production URL for the `subscription.*` events. The pages `/billing` and `/billing/success` of the frontend receive the customers back from Polar. <!-- copier:payments -->
- [ ] **PostHog** (if used): `FASTAPI_POSTHOG_API_KEY` and the `FASTAPI_POSTHOG_HOST` of the project's region; list the events in your privacy policy. <!-- copier:posthog -->
- [ ] **AI** (if used): an Anthropic API key from a workspace with a spend limit, and a look at `FASTAPI_RATE_LIMIT_AI_REQUESTS_PER_HOUR`. LangChain and the Anthropic SDK add ~90 MiB to each worker and a few seconds to its start: size the memory for it. Turn on `FASTAPI_LANGFUSE_CAPTURE_CONTENT` only if the users' data may leave for Langfuse. <!-- copier:ai -->
- [ ] **Background jobs**: from the backend image, run the workers (`celery --app app.jobs.worker worker`) and **exactly one** beat (`celery --app app.jobs.worker beat`: two would send every scheduled task twice), with `FASTAPI_CELERY_BROKER_URL` pointing to Redis. On stop, a worker finishes its running tasks: give it a grace period longer than the longest task. <!-- copier:celery -->
- [ ] **Monitoring**: probes on `/api/health/` (liveness) and `/api/ready/` (readiness).
- [ ] **Sentry**: `SENTRY_DSN` and `SENTRY_ENVIRONMENT`. <!-- copier:sentry -->
- [ ] **Emails**: `FASTAPI_SMTP_*` and `FASTAPI_EMAIL_FROM` for your provider (a domain with SPF and DKIM, or the emails land in spam), and `FASTAPI_FRONTEND_URL` pointing to the frontend that serves `/verify-email` and `/reset-password`. A failed delivery shows up in the logs as `email_not_sent`.
- [ ] **Google sign-in** (if used): the production origins in the OAuth client, and `FASTAPI_GOOGLE_CLIENT_ID`.
