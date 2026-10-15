# FastAPI Docker Boilerplate

[![CI](https://github.com/diegoddie/fastapi-docker-boilerplate/actions/workflows/ci.yml/badge.svg)](https://github.com/diegoddie/fastapi-docker-boilerplate/actions/workflows/ci.yml)
![Python 3.14](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Coverage 100%](https://img.shields.io/badge/coverage-100%25-brightgreen)
![mypy strict](https://img.shields.io/badge/mypy-strict-2A6DB2)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A production-ready starting point for FastAPI backends: async SQLModel on PostgreSQL, strict quality gates, and a Docker setup that runs the same way on your laptop, in CI and in production.

It distills the conventions I use on real-world FastAPI projects into a template you can clone and start building on in minutes.

> Looking for the original version? It is available at the [`v1.0.0`](https://github.com/diegoddie/fastapi-docker-boilerplate/tree/v1.0.0) tag.

## Features

- **Async all the way**: FastAPI + SQLModel/SQLAlchemy 2 async sessions on PostgreSQL (psycopg 3)
- **Authentication**: open registration, email + password login (argon2, hashed off the event loop), **Sign in with Google** with accounts linked explicitly (never by email), short-lived JWT access tokens and **rotating refresh tokens stored in the database** (hashed), with reuse detection that tolerates concurrent refreshes, real logout and a purge command; **rate limits** on login, registration and Google sign-in, shared by every worker; the Swagger UI "Authorize" button works out of the box
- **Permissions**: users belong to groups, groups grant permissions, and routes declare the permission they need (`require_any_permissions`)
- **Users API**: profile (`me`), and paginated user management for administrators
- **Example domain (`todos`)**: the reference to copy for new features, with CRUD, permissions per action, per-owner visibility, filters, search, ordering, pagination, soft delete and a streamed CSV export safe from formula injection
- **Typed configuration** with pydantic-settings, all variables prefixed with `FASTAPI_`
- **Consistent errors**: every error (including 404, 405, validation errors and unexpected 500s) has the same shape with a machine-readable `errorCode`; database integrity errors become `409` / `422` responses automatically, without leaking database details
- **UTC-only datetimes**: a custom column type rejects naive datetimes at the database boundary
- **Alembic migrations** with a constraint naming convention and date-prefixed revisions, applied automatically when the container starts and safe with several replicas (advisory lock)
- **Health checks**: `/api/health/` for liveness and `/api/ready/` for readiness (database reachable)
- **Structured logs with a request id**: JSON lines in production (colored ones locally) from the app, uvicorn, gunicorn and Alembic alike; every request gets an id, returned in `X-Request-ID`, written on each of its lines with the user id, included in `500` responses and attached to Sentry events
- **One Docker image, three targets**: `remote` (gunicorn + uvicorn workers, non-root), `test` (CI) and `local` (hot reload)
- **Quality gates**: ruff with an extended rule set, mypy in strict mode, bandit, and **100% branch coverage** enforced
- **Realistic tests**: a real PostgreSQL database where every test is rolled back, factories, named personas, full-response snapshots, and a guard test that fails if a route is left without authentication
- **CI on GitHub Actions** running the very same test image (with cached Docker layers), a vulnerability scan of every locked dependency (`pip-audit`), Dependabot for updates
- **Documented decisions**: an architecture overview with diagrams, architecture decision records, and a `CLAUDE.md` plus a `new-domain-app` skill so that code generated with Claude Code follows the same conventions
- **Developer experience**: `uv` for dependencies, `just` for every task, pre-commit hooks pinned to `uv.lock`, a Typer management CLI with demo data (`seed`) and an async IPython `shell`

## Tech stack

| Area | Tools |
|---|---|
| Language | Python 3.14 |
| Web framework | FastAPI, uvicorn, gunicorn |
| Database | PostgreSQL 18, SQLModel, SQLAlchemy 2 (async), psycopg 3, Alembic |
| Configuration | pydantic-settings |
| Security | PyJWT, pwdlib (argon2) |
| API | fastapi-pagination |
| CLI | Typer |
| Quality | ruff, mypy (strict), bandit, pre-commit |
| Testing | pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-xdist, polyfactory, inline-snapshot, dirty-equals, time-machine |
| Tooling | uv, just, Docker, Docker Compose, GitHub Actions, Dependabot |
| Logging and monitoring | structlog, Sentry (optional, production only) |

## Quickstart

Requirements: [Docker](https://docs.docker.com/get-docker/) with Docker Compose.

```bash
git clone https://github.com/diegoddie/fastapi-docker-boilerplate.git
cd fastapi-docker-boilerplate
cp .env_template .env
docker compose up --build
```

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health/
- Readiness check: http://localhost:8000/api/ready/

The `.env` file selects the `local` image target and mounts the source code, so the server reloads on every change. The API docs are served only in the `local` environment unless `FASTAPI_DOCS_ENABLED` says otherwise.

Create the first administrator, then log in from the docs with the **Authorize** button (the username is the email):

```bash
docker compose run --rm backend just manage users createsuperuser
```

Or fill the database with demo users (Alice admin, Bob member, Carol viewer, with the password you choose) and their todos:

```bash
docker compose run --rm backend just manage seed
```

## API overview

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | public | Register a new user (group `member`) |
| `POST` | `/api/v1/auth/login/` | public | Log in (OAuth2 password form) and get a token pair |
| `POST` | `/api/v1/auth/refresh/` | public | Exchange a refresh token for a new pair (rotation) |
| `POST` | `/api/v1/auth/logout/` | public | Revoke the session of a refresh token |
| `POST` | `/api/v1/auth/google/` | public | Sign in with a Google ID token and get a token pair |
| `POST` | `/api/v1/auth/google/link/` | authenticated | Link a Google account to your user (password required) |
| `GET` / `PATCH` | `/api/v1/users/user/me/` | authenticated | Read or update your own profile |
| `GET` | `/api/v1/users/user/` | `can_view_user` | List users (paginated) |
| `GET` | `/api/v1/users/user/{id}/` | `can_view_user` | User detail |
| `PATCH` | `/api/v1/users/user/{id}/` | `can_edit_user` | Change names, groups, or (re)activate a user |
| `DELETE` | `/api/v1/users/user/{id}/` | `can_disable_user` | Disable a user and end all their sessions |
| `POST` | `/api/v1/todos/todo/` | `can_create_todo` | Create a todo (owned by you) |
| `GET` | `/api/v1/todos/todo/` | `can_view_todo` | List todos (paginated, with filters) |
| `GET` | `/api/v1/todos/todo/download/` | `can_view_todo` | Download the filtered todos as CSV |
| `GET` | `/api/v1/todos/todo/{id}/` | `can_view_todo` | Todo detail |
| `PATCH` | `/api/v1/todos/todo/{id}/` | `can_edit_todo` | Update a todo |
| `DELETE` | `/api/v1/todos/todo/{id}/` | `can_delete_todo` | Delete a todo (soft delete) |
| `GET` / `HEAD` | `/api/health/`, `/api/ready/` | public | Liveness and readiness checks |

## Sign in with Google

The frontend shows Google's "Sign in with Google" button, receives an **ID token** from Google and sends it to `POST /api/v1/auth/google/` as `{"id_token": "..."}`. The backend verifies the token (Google's signature, issuer, audience, expiry) and answers with the same token pair as the password login:

- the first sign-in creates a `member` without a password, if Google verified the email;
- if an account with the same email already exists, the sign-in answers `409` with `errorCode: ACCOUNT_EXISTS` and links nothing, because the email does not prove that the person owns that account (someone may have registered the address first, or the address may have changed hands). The user signs in with the password, and the frontend links the Google account with `POST /api/v1/auth/google/link/`, sending `{"id_token": "...", "password": "..."}`;
- the next sign-ins find the user through the Google account id, even if the email changes.

To enable it:

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project and configure the consent screen (*Google Auth Platform*); while the app is in testing, add your account as a test user.
2. Create an OAuth client of type **Web application**, with `http://localhost:8000` and `http://localhost` as authorized JavaScript origins (no redirect URI is needed).
3. Set `FASTAPI_GOOGLE_CLIENT_ID` in `.env` and restart the backend. The client secret is not needed.
4. Open http://localhost:8000/api/v1/auth/google/test-page/: a local page (served only when the docs are) with the Google button, which shows the tokens returned by the backend.

Without a client id, Google sign-in answers `404` with `errorCode: GOOGLE_SIGN_IN_DISABLED`.

## Groups and permissions

Users belong to groups; each group grants a set of permissions (`GROUPS` in `app/users/constants.py`); each route declares the permission it needs.

| Group | Permissions |
|---|---|
| `admin` | every permission, including `can_manage_all_todos`: sees and changes everyone's todos |
| `member` (default on registration) | create, view, edit and delete **their own** todos |
| `viewer` | view their own todos (read-only) |

A todo owned by someone else answers `404`, not `403`: the API never reveals that it exists.

## Lists: filters, search, ordering

List endpoints take their filters as query parameters, declared once in a `FilterBase` subclass (see `TodoFilter` in `app/todos/schemas.py`) and reused by the CSV export:

| Parameter | Example | Meaning |
|---|---|---|
| `<field>` | `?status=done` | equal to |
| `<field>__in` | `?priority__in=high&priority__in=low` | one of |
| `<field>__gte` / `<field>__lte` | `?due_date__lte=2026-12-31` | greater / less than or equal to |
| `<field>__is_null` | `?due_date__is_null=true` | missing (or present, with `false`) |
| `search` | `?search=report` | case-insensitive match on the search fields (`%` and `_` match literally) |
| `order_by` | `?order_by=-priority,title` | sortable fields, `-` for descending; anything else is a `422` |
| `page`, `size` | `?page=2&size=20` | pagination (size up to 100) |

## Development

### Inside Docker

Run any `just` command in the backend container:

```bash
docker compose run --rm backend just test
docker compose run --rm backend just forge "add article model"
```

### On your machine

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/) and [just](https://github.com/casey/just#installation).

```bash
docker compose up -d postgres          # database only, exposed on localhost:5432
uv sync --group local --group test     # install the dependencies
just precommit_install                 # install the git hooks
just migrate-forward                   # apply the migrations
just runserver                         # http://localhost:8000/api/docs
```

The tests run against a real PostgreSQL database: the suite creates a `<database>-test` database (one per xdist worker) and rolls back every change at the end of each test. `just test` also runs `alembic check`, so the database must be migrated to the latest revision first.

### Commands

Run `just` to list every command. The most used ones:

| Command | Description |
|---|---|
| `just runserver` | Start the development server with hot reload |
| `just fix` | Format, auto-fix lint issues and type check |
| `just check` | Format check, lint, type check and security scan, without changing files |
| `just test` | `check` + test suite with coverage + coverage report |
| `just pytest` | Run pytest for debugging (no output capture, slowest tests) |
| `just forge "message"` | Create a new migration from the models |
| `just migrate-forward` | Apply all pending migrations |
| `just migrate-backward <revision>` | Roll back to a revision |
| `just manage users createsuperuser` | Create an administrator |
| `just manage seed` | Fill a local database with demo users and todos |
| `just manage shell` | IPython with the settings, a database session and the models loaded (top-level `await`) |
| `just manage purge` | Delete the expired refresh tokens and rate limit counters |
| `just audit` | Check the locked dependencies for known vulnerabilities |
| `just upgrade` | Upgrade the dependencies within the pinned ranges |

In production, schedule `purge` once a day, e.g. as a Kubernetes CronJob or a cron entry. The `remote` image has no `just`, so run the module directly: `docker compose run --rm backend python -m app.cli.main purge`.

## Project structure

```
app/
├── main.py              # create_app() factory: lifespan, middleware, routers, exception handlers
├── api/
│   ├── router.py        # /api: health and readiness checks + versioned routers
│   └── v1/router.py     # /api/v1: aggregates the domain routers
├── core/                # infrastructure: settings, database, exceptions, handlers, logs, middleware
├── commons/             # shared building blocks: base model, UTCDateTime, pagination
├── auth/                # login, tokens, security primitives, auth dependencies
├── users/               # users domain: models, schemas, services, router, commands
├── todos/               # example domain: the reference for new features
├── filters/             # FilterBase: declarative filters, search and ordering
├── ratelimit/           # rate limits with counters in PostgreSQL
├── cli/                 # Typer management CLI: seed, shell
└── migrations/          # Alembic environment and revisions
tests/
├── conftest.py          # app, client and database fixtures (rolled back after each test)
├── factories/           # polyfactory factories
├── pytest_plugins/      # fixtures grouped by domain, including the personas
└── ...                  # one folder per app package
scripts/                 # entrypoint, check, test and coverage scripts
```

## Adding a feature

New features live in their own **domain package**; `app/todos/` is the one to copy:

1. `app/<domain>/`: `constants.py` (permissions, lengths), `enums.py`, `models.py` (a `BaseXxx` shared with the schemas + the table model), `schemas.py` (`XxxPublicSchemaCreate` / `Update` / `Response`, CSV schema, filter), `services.py` (a class of static methods, with the access rules in `get_where_clause`), `router.py` (`<action>_<resource>_route` handlers).
2. Register the model in `app/core/models.py` and the router in `app/api/v1/router.py`.
3. Grant the new permissions to the groups in `app/users/constants.py`.
4. Create the migration with `just forge "add <domain> table"` and review it.
5. Tests: a factory in `tests/factories/`, the fixtures (with fixed ids) in `tests/pytest_plugins/<domain>.py`, and `tests/<domain>/test_router.py` with one test per route and status code (`test_<action>_<resource>_route_<status>`), URLs written in full.

## Documentation

- [Architecture](docs/ARCHITECTURE.md): layers, request lifecycle, authentication and authorization flows, data, errors, testing, runtime
- [Architecture decision records](docs/adr/README.md): why the main choices were made, and what was discarded
- [CLAUDE.md](CLAUDE.md): the conventions in a form Claude Code follows; the [`new-domain-app`](.claude/skills/new-domain-app/SKILL.md) skill adds a domain step by step (ask Claude Code to "add an invoices domain")

## Design decisions

- **The database is the source of truth for integrity.** Uniqueness and foreign keys are database constraints. Services simply commit, and a single exception handler turns violations into `409 Conflict` or `422 Unprocessable Content`.
- **Errors are meant for machines too.** Every error response looks like `{"detail": {"message": "...", "errorCode": "NOT_FOUND"}}`, so clients can branch on a stable code instead of parsing messages. Validation errors add an `errors` list (`field`, `message`, `type`) and never echo the submitted values, which may contain passwords or personal data.
- **One app factory.** `create_app()` builds the application for production and for the tests alike, so what is tested is what runs.
- **Refresh tokens live in the database.** Access tokens are short-lived JWTs (15 minutes) carrying only the user id. Refresh tokens are random strings stored as SHA-256 hashes: every refresh revokes the token and issues a new one in the same family, presenting a revoked token ends the whole family (stolen token detection), and logout really ends the session. A token rotated less than 30 seconds earlier still works while its session is open, so two tabs refreshing together do not log the user out.
- **Every request reads the user.** Disabling a user takes effect immediately, even while their access token is still valid; permissions are computed from the groups on every request, so changing a group needs no new login.
- **Access rules live in one place.** Each service has a `get_where_clause(user)` used by every query, so a list, a detail, an update and a delete can never disagree on what a user may reach.
- **Soft delete.** Deleting sets `datetime_disabled`: the row is kept (audit, recovery) but hidden from the API.
- **Logs are data.** Every line is an event with fields, rendered as JSON in production, whatever library wrote it. A request id ties together the lines of a request, its response and its Sentry event, and the user id says who made it; the request line never contains bodies, query strings or IP addresses.
- **Exports are safe to open, and of any size.** CSV cells starting with `=`, `+`, `-`, `@` are prefixed with a quote, so a spreadsheet never runs them as formulas. Rows are read with a server-side cursor, 1,000 at a time, while the file is sent: memory does not grow with the export.
- **Enums stored by value.** Postgres enums hold the same values as the API (`in_progress`), not the Python member names.
- **Security primitives behind interfaces.** Services depend on the `PasswordHasher`, `AccessTokenCodec` and `IdentityProvider` protocols, not on argon2, JWT or Google, so implementations can be swapped and faked in tests. Adding another sign-in provider means adding a class.
- **External identities in their own table, linked explicitly.** A user can be linked to several external accounts (provider + account id) and still have a password. An external account is never linked by email: linking needs a signed-in user and their password, so neither whoever registered an address first nor a former owner of the address can get into the account.
- **Rate limits that hold with many workers.** Login attempts are limited per account and IP (so a stranger cannot lock you out), all authentication requests per IP. The counters live in PostgreSQL with an atomic upsert, so two gunicorn workers or ten containers share them, and the table stores hashes, not emails or addresses.
- **Slow on purpose, but not blocking.** Argon2 costs ~150 ms of CPU and 64 MiB of memory per password, by design. The password hasher is async and runs it in a worker thread, so logins do not stall the other requests, and at most `FASTAPI_PASSWORD_HASH_CONCURRENCY` hashes run at once per worker: a burst of logins waits in line instead of exhausting the memory (30 hashes at once: ~1.9 GiB without the cap, ~190 MiB with 2).
- **Settings vs constants.** What can change between environments (secrets, URLs of external services, timeouts) lives in the settings; facts of the code (permission names, Google's issuers, column lengths) live in each package's `constants.py`.
- **OAuth 2.0 where it matters.** The token endpoints use the snake_case fields of RFC 6749 (`access_token`, `refresh_token`…), which Swagger UI and OAuth client libraries expect; the rest of the API is camelCase.
- **Tests guard the API surface.** A test reads the OpenAPI schema and fails if any route outside an explicit list of public paths lacks authentication.
- **Timestamps are always UTC.** `UTCDateTime` stores `timestamptz` values and refuses naive datetimes instead of letting the server timezone silently decide.
- **One image, many environments.** The `remote`, `test` and `local` targets share the same base layer, and the uv dependency groups (`remote`, `test`, `local`) mirror them. Migrations run in the entrypoint, so every environment starts from an up-to-date schema; a Postgres advisory lock keeps replicas that start together from migrating in parallel.
- **The CI runs what you run.** GitHub Actions builds the `test` target and runs `docker compose run backend`, the same command you can run locally.
- **Tooling cannot drift.** Pre-commit hooks invoke ruff, mypy and bandit through `uv run`, so they always use the versions locked in `uv.lock`.

## Configuration

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
| `FASTAPI_RATE_LIMIT_PASSWORD_ATTEMPTS_PER_MINUTE` | `5` | Login and linking attempts per account and IP |
| `FASTAPI_RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` | `30` | Authentication requests per IP (registration, login, Google) |
| `FASTAPI_RATE_LIMIT_REGISTRATIONS_PER_HOUR` | `10` | Registrations per IP |
| `FASTAPI_GOOGLE_CLIENT_ID` | — | OAuth client id that enables Sign in with Google |
| `FASTAPI_GOOGLE_CERTS_URL` | Google's public keys URL | Where Google's signing keys are fetched from |
| `SENTRY_DSN` | — | Enables Sentry in the `remote` image |
| `WEB_CONCURRENCY` | `2` | Number of gunicorn workers |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1,::1` | Proxies trusted to set `X-Forwarded-For` (read by uvicorn and gunicorn). Behind a load balancer, set its addresses (or `*` if only the proxy can reach the app); otherwise every client has the proxy's address and they share the rate limits |

Docker Compose also reads `BACKEND_BUILD_TARGET` (`remote` by default), `BACKEND_PORT` and `POSTGRES_PORT`.

> **Database URL in Docker vs on your machine.** `FASTAPI_DATABASE_URL` in `.env` points to `localhost`, for the commands you run on your machine. Inside Docker Compose the backend reaches the database through the `postgres` service instead: compose sets the container's `FASTAPI_DATABASE_URL` from `DATABASE_URL`, which defaults to the compose database. Set `DATABASE_URL` only to point the container to another database.

## Deploying to production

The `remote` image runs gunicorn with uvicorn workers as a non-root user and applies the migrations when it starts. Before going live:

- [ ] **Secrets**: a random `FASTAPI_SECRET_KEY` (`openssl rand -hex 32`), never the one in `.env_template`; `FASTAPI_DATABASE_URL` pointing to the production database.
- [ ] **Environment**: `FASTAPI_ENVIRONMENT=remote` (the default): API docs off, JSON logs.
- [ ] **CORS**: `FASTAPI_CORS_ALLOWED_ORIGINS` lists the frontend origins.
- [ ] **Behind a load balancer or reverse proxy**: set `FORWARDED_ALLOW_IPS` to its addresses (or `*` if only the proxy can reach the app). If it is missing, nothing fails: every user simply gets the proxy's address and the whole site shares the per-IP rate limits (30 logins per minute, 10 registrations per hour).
- [ ] **Memory**: each worker takes ~80 MiB, plus 64 MiB for each password hash running (`FASTAPI_PASSWORD_HASH_CONCURRENCY`). With the defaults (2 workers, 2 hashes each) the container idles at ~250 MiB and peaks at ~500 MiB during a burst of logins: give it at least 768 MiB, and recompute when you change `WEB_CONCURRENCY`.
- [ ] **Scheduled job**: `python -m app.cli.main purge` once a day (expired refresh tokens and rate limit counters).
- [ ] **Monitoring**: `SENTRY_DSN`; probes on `/api/health/` (liveness) and `/api/ready/` (readiness).
- [ ] **Google sign-in** (if used): the production origins in the OAuth client, and `FASTAPI_GOOGLE_CLIENT_ID`.

## Using it as a template

1. Click **Use this template** on GitHub, or clone the repository.
2. Rename the project:
   - `name` and `description` in `pyproject.toml`, then run `uv lock`
   - the `project` labels in the `Dockerfile`
   - the app `title` in `app/main.py`
   - the database and image names (`boilerplate`) in `compose.yaml` and `.env_template`
3. Update the copyright holder in `LICENSE`.
4. Start adding your domain packages under `app/`.

## Roadmap

- [x] Foundations: tooling, core infrastructure, Docker, CI
- [x] Users and JWT authentication: registration, rotating refresh tokens, groups and permissions
- [x] Database-backed tests: transaction rollback per test, factories, personas, snapshots
- [x] Sign in with Google
- [x] Example `todos` domain: permissions, ownership, filtering, search, pagination, soft delete, CSV export
- [x] Architecture documentation, ADRs, Claude Code conventions, CI vulnerability scan and Docker cache
- [x] Structured JSON logs with a request id, `seed` and `shell` management commands
- [ ] Copier template with optional modules (authentication, background jobs, Sentry) and the `v2.0.0` release

## License

[MIT](LICENSE)
