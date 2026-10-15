# 0011. Rate limits on the authentication endpoints, counted in PostgreSQL

- Status: Accepted
- Date: 2026-10-14

## Context

Nothing limited the login attempts: anyone could guess passwords forever, and
since each attempt costs ~150 ms of argon2, flooding the login also loaded the
CPU. In production the app runs as several gunicorn workers, possibly in
several containers, each with its own memory: a counter kept in memory would
multiply the limit by the number of processes.

## Decision

- Fixed-window counters (one row per key and window) in a `ratelimitcounter`
  table, incremented with an atomic `INSERT … ON CONFLICT DO UPDATE … RETURNING`
  and committed at once, so a failing request still counts. Keys are stored as
  SHA-256 hashes: the table holds no emails or IP addresses.
- Three limits, all settings:
  - `RATE_LIMIT_PASSWORD_ATTEMPTS_PER_MINUTE` (5), per account **and** IP, on
    login and on Google linking (they share the counter);
  - `RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` (30), per IP, on registration, login,
    Google sign-in and linking;
  - `RATE_LIMIT_REGISTRATIONS_PER_HOUR` (10), per IP.
- Over a limit: `429 TOO_MANY_REQUESTS` with a `Retry-After` header.
- The limits are FastAPI dependencies on the routes; the storage is behind the
  `RateLimiter` protocol, so Redis can replace PostgreSQL without touching them.
- The client IP is the connection's, or the one in `X-Forwarded-For` when the
  proxy is trusted through `FORWARDED_ALLOW_IPS`, which uvicorn and gunicorn
  read.
- `just manage purge` deletes the counters of past windows together with the
  expired refresh tokens; it replaces `auth purge-tokens` (0009).

## Consequences

- One counter for every worker and container, with no extra service.
- A write per limited request: negligible next to an argon2 hash.
- Counting per account and IP, a stranger cannot lock a user out of their
  account, but a distributed attack (many IPs on one account) is only slowed by
  the per-IP limit: that needs edge protection (WAF, CAPTCHA).
- Behind a load balancer that is not trusted, every client has its address and
  they share the per-IP limits: `FORWARDED_ALLOW_IPS` must be set.
- Fixed windows allow up to twice the limit across a window boundary.
- Tests of the limits stop the clock at the start of a window (`time-machine`),
  so their counters never reset halfway.

## Alternatives considered

- **In-memory counters** (e.g. `slowapi` without a backend): wrong as soon as
  there are two workers.
- **Redis**: the usual store for counters, with expiring keys; one more service
  to run, worth it when the project already has Redis (e.g. for Celery).
- **Limits at the edge only** (nginx, API gateway, Cloudflare): good in addition,
  but the edge does not know which account a login targets.
- **Sliding windows or token buckets**: smoother, more state per key; fixed
  windows are enough for authentication endpoints.
