# 0008. Structured logs with a request id

- Status: Accepted
- Date: 2026-10-14

## Context

In production, the lines of many concurrent requests are interleaved, and each
library logs in its own format (uvicorn, gunicorn, Alembic, SQLAlchemy). When a
user reports an error, finding the lines of that request, and the traceback
behind a generic `500`, means guessing from timestamps. Log platforms
(CloudWatch, Datadog, Grafana Loki…) can filter and aggregate by field, but only
if every line is machine-readable.

## Decision

- Every log line goes through **structlog**: the application logs events with
  key-value fields (`logger.info("todo_created", todo_id=...)`), and a
  `ProcessorFormatter` on the root handler renders the standard library lines of
  uvicorn, gunicorn, Alembic and SQLAlchemy the same way.
- Lines are **JSON objects** in remote environments and colored key-value lines
  locally (`FASTAPI_LOG_FORMAT` overrides it); `FASTAPI_LOG_LEVEL` sets the level.
- `RequestContextMiddleware` gives every request an **id**: the `X-Request-ID`
  header sent by a proxy or another service when it is safe (letters, digits,
  `.`, `_`, `-`, up to 128 characters), a new one otherwise. The id is bound to
  every line of the request, returned in the `X-Request-ID` header (exposed to
  browsers through CORS), included in the body of `500` responses and attached
  to Sentry events as a tag. Authentication binds the `user_id` too.
- The middleware writes **one line per request** (method, path, status,
  duration, request id, user id), replacing the access logs of uvicorn and
  gunicorn; health checks are logged at debug level.
- Each entry point configures logging once: the app (`app.main`), the CLI, the
  Alembic environment and gunicorn's master process.

## Consequences

- A request id from a bug report, a frontend or Sentry leads to all the lines of
  that request, traceback included.
- The request line carries no body, query string, header or IP address: its
  only personal data is the user id.
- The logging context is a set of context variables: a value bound while
  handling a request (e.g. in a dependency) appears on the following lines of
  that request only.
- Tests read the logged events through pytest's `caplog` (`log_events` fixture),
  since structlog hands them to the standard library as dicts.

## Alternatives considered

- **Standard library logging with a JSON formatter** (`python-json-logger`):
  fewer moving parts, but no bound context, so every call would pass the request
  id by hand.
- **`asgi-correlation-id`**: does the request id part only, and still needs the
  logging setup; the middleware is short enough to own.
- **OpenTelemetry tracing**: the complete solution for distributed systems, but
  it needs a collector and a backend; a request id covers a single service and
  can coexist with tracing later.
