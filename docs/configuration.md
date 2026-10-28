# Configuration

Settings are read from environment variables prefixed with `FASTAPI_` (see `app/core/config.py`).

| Variable | Default | Description |
|---|---|---|
| `FASTAPI_DATABASE_URL` | — (required) | PostgreSQL URL, e.g. `postgresql+psycopg://user:password@host:5432/db` |
| `FASTAPI_ENVIRONMENT` | `remote` | `local` or `remote` |
| `FASTAPI_DEBUG` | `false` | Debug mode (tracebacks in error responses) and SQL echo |
| `FASTAPI_VERSION` | from `pyproject.toml` | Version shown in the OpenAPI schema |
| `FASTAPI_CORS_ALLOWED_ORIGINS` | `[]` | JSON list of allowed origins, e.g. `["http://localhost:3000"]` |
| `FASTAPI_API_ROOT` | `/api` | Prefix of every route |
| `FASTAPI_DOCS_ENABLED` | `true` only when `FASTAPI_ENVIRONMENT=local` | Serve the Swagger UI and the OpenAPI schema |
| `FASTAPI_DOCS_PATH` | `docs` | Swagger UI path |
| `FASTAPI_OPENAPI_PATH` | `openapi.json` | OpenAPI schema path |
| `FASTAPI_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` |
| `FASTAPI_LOG_FORMAT` | `console` when `FASTAPI_ENVIRONMENT=local`, `json` otherwise | How log lines are rendered |
| `FASTAPI_DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `FASTAPI_DATABASE_MAX_OVERFLOW` | `10` | Extra connections allowed above the pool size |
| `FASTAPI_SECRET_KEY` | — (required, at least 32 characters) | Signs the access tokens; generate one with `openssl rand -hex 32` |
| `FASTAPI_JWT_ALGORITHM` | `HS256` | `HS256`, `HS384` or `HS512` |
| `FASTAPI_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `FASTAPI_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `FASTAPI_REFRESH_TOKEN_REUSE_GRACE_SECONDS` | `30` | How long a rotated refresh token still works (concurrent refreshes); `0` disables it |
| `FASTAPI_PASSWORD_HASH_CONCURRENCY` | `2` | Password hashes running at once per worker (64 MiB each); the others wait |
| `FASTAPI_FRONTEND_URL` | `http://localhost:3000` | Base URL of the links in the emails (`/verify-email`, `/reset-password`) |
| `FASTAPI_EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | `24` | Lifetime of a verification link |
| `FASTAPI_PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `30` | Lifetime of a password reset link |
| `FASTAPI_RATE_LIMIT_EMAILS_PER_HOUR` | `5` | Emails sent to the same address, whatever the IP |
| `FASTAPI_EMAIL_BACKEND` | `console` when `FASTAPI_ENVIRONMENT=local`, `smtp` otherwise | `console` writes the emails, links included, to the logs: never use it where logs are kept |
| `FASTAPI_EMAIL_FROM` | `no-reply@example.com` | Sender of the emails |
| `FASTAPI_SMTP_HOST` / `FASTAPI_SMTP_PORT` | `localhost` / `587` | SMTP server |
| `FASTAPI_SMTP_SECURITY` | `starttls` | `starttls`, `ssl` (port 465) or `none` |
| `FASTAPI_SMTP_USERNAME` / `FASTAPI_SMTP_PASSWORD` | — | SMTP credentials |
| `FASTAPI_SMTP_TIMEOUT_SECONDS` | `10` | SMTP connection timeout |
| `FASTAPI_RATE_LIMIT_PASSWORD_ATTEMPTS_PER_MINUTE` | `5` | Login and linking attempts per account and IP |
| `FASTAPI_RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` | `30` | Authentication requests per IP (registration, login, Google) |
| `FASTAPI_RATE_LIMIT_REGISTRATIONS_PER_HOUR` | `10` | Registrations per IP |
| `FASTAPI_GOOGLE_CLIENT_ID` | — | OAuth client id that enables Sign in with Google |
| `FASTAPI_GOOGLE_CERTS_URL` | Google's public keys URL | Where Google's signing keys are fetched from |
| `SENTRY_DSN` | — | Enables Sentry in the `remote` image <!-- copier:sentry --> |
| `SENTRY_ENVIRONMENT` | — | Environment name shown in Sentry (e.g. `production`) <!-- copier:sentry --> |
| `FASTAPI_SENTRY_TRACES_SAMPLE_RATE` | `0` | Share of requests traced for Sentry performance monitoring (`0` to `1`) <!-- copier:sentry --> |
| `FASTAPI_POLAR_ACCESS_TOKEN` | — | Polar organization access token (scopes `checkouts:write`, `customer_sessions:write`) <!-- copier:payments --> |
| `FASTAPI_POLAR_WEBHOOK_SECRET` | — | Secret of the Polar webhook endpoint <!-- copier:payments --> |
| `FASTAPI_POLAR_ENVIRONMENT` | `sandbox` | `sandbox` or `production` <!-- copier:payments --> |
| `FASTAPI_POLAR_PRODUCT_IDS` | `[]` | JSON list of the ids of the products users may buy <!-- copier:payments --> |
| `FASTAPI_POLAR_TIMEOUT_SECONDS` | `10` | Timeout of the calls to Polar <!-- copier:payments --> |
| `FASTAPI_RATE_LIMIT_PAYMENTS_REQUESTS_PER_HOUR` | `20` | Checkouts and portal sessions per user <!-- copier:payments --> |
| `FASTAPI_POSTHOG_API_KEY` | — | PostHog project API key (`phc_...`): enables the events and the flags <!-- copier:posthog --> |
| `FASTAPI_POSTHOG_HOST` | `https://eu.i.posthog.com` | PostHog region of the project (`https://us.i.posthog.com` for the US) <!-- copier:posthog --> |
| `FASTAPI_POSTHOG_FEATURE_FLAGS_TIMEOUT_SECONDS` | `1` | How long a route behind a flag waits for PostHog before treating the flag as off <!-- copier:posthog --> |
| `FASTAPI_ANTHROPIC_API_KEY` | — | Enables the AI features (use a workspace with a spend limit) <!-- copier:ai --> |
| `FASTAPI_AI_MODEL` | `claude-opus-5-5` | Claude model of the AI features <!-- copier:ai --> |
| `FASTAPI_AI_TIMEOUT_SECONDS` / `FASTAPI_AI_MAX_RETRIES` | `60` / `1` | Timeout of a call to the model, and retries on timeouts, rate limits and overloads <!-- copier:ai --> |
| `FASTAPI_RATE_LIMIT_AI_REQUESTS_PER_HOUR` | `20` | AI requests per user <!-- copier:ai --> |
| `FASTAPI_LANGFUSE_PUBLIC_KEY` / `FASTAPI_LANGFUSE_SECRET_KEY` | — | Enable the Langfuse tracing of the AI calls <!-- copier:ai --> |
| `FASTAPI_LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Langfuse server (e.g. `https://us.cloud.langfuse.com`, or your own) <!-- copier:ai --> |
| `FASTAPI_LANGFUSE_CAPTURE_CONTENT` | `false` | Also send the prompts and the answers to Langfuse; they can hold personal data <!-- copier:ai --> |
| `FASTAPI_CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL of the Celery broker (in Compose, the `redis` service) <!-- copier:celery --> |
| `FASTAPI_CELERY_WORKER_CONCURRENCY` | `2` | Processes of a Celery worker (~75 MiB each) <!-- copier:celery --> |
| `WEB_CONCURRENCY` | `2` | Number of gunicorn workers |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1,::1` | Proxies trusted to set `X-Forwarded-For` (read by uvicorn and gunicorn). Behind a load balancer, set its addresses (or `*` if only the proxy can reach the app); otherwise every client has the proxy's address and they share the rate limits |

Docker Compose also reads `BACKEND_BUILD_TARGET` (`remote` by default), `BACKEND_PORT` and `POSTGRES_PORT`.
It also reads `REDIS_PORT`, and `CELERY_BROKER_URL` to point the containers to another Redis. <!-- copier:celery -->

> **Database URL in Docker vs on your machine.** `FASTAPI_DATABASE_URL` in `.env` points to `localhost`, for the commands you run on your machine. Inside Docker Compose the backend reaches the database through the `postgres` service instead: compose sets the container's `FASTAPI_DATABASE_URL` from `DATABASE_URL`, which defaults to the compose database. Set `DATABASE_URL` only to point the container to another database.
