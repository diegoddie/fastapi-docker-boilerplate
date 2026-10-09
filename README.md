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
- **Authentication**: open registration, email + password login (argon2), short-lived JWT access tokens and **rotating refresh tokens stored in the database** (hashed), with reuse detection and real logout; the Swagger UI "Authorize" button works out of the box
- **Permissions**: users belong to groups, groups grant permissions, and routes declare the permission they need (`require_any_permissions`)
- **Users API**: profile (`me`), and paginated user management for administrators
- **Typed configuration** with pydantic-settings, all variables prefixed with `FASTAPI_`
- **Consistent errors**: every error (including 404, 405, validation errors and unexpected 500s) has the same shape with a machine-readable `errorCode`; database integrity errors become `409` / `422` responses automatically, without leaking database details
- **UTC-only datetimes**: a custom column type rejects naive datetimes at the database boundary
- **Alembic migrations** with a constraint naming convention and date-prefixed revisions, applied automatically when the container starts and safe with several replicas (advisory lock)
- **Health checks**: `/api/health/` for liveness and `/api/ready/` for readiness (database reachable)
- **One Docker image, three targets**: `remote` (gunicorn + uvicorn workers, non-root), `test` (CI) and `local` (hot reload)
- **Quality gates**: ruff with an extended rule set, mypy in strict mode, bandit, and **100% branch coverage** enforced
- **Realistic tests**: a real PostgreSQL database where every test is rolled back, factories, named personas, full-response snapshots, and a guard test that fails if a route is left without authentication
- **CI on GitHub Actions** running the very same test image, Dependabot for dependency updates
- **Developer experience**: `uv` for dependencies, `just` for every task, pre-commit hooks pinned to `uv.lock`, a Typer management CLI

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
| Testing | pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-xdist, polyfactory, inline-snapshot, dirty-equals |
| Tooling | uv, just, Docker, Docker Compose, GitHub Actions, Dependabot |
| Monitoring | Sentry (optional, production only) |

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

## API overview

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | public | Register a new user (group `member`) |
| `POST` | `/api/v1/auth/login/` | public | Log in (OAuth2 password form) and get a token pair |
| `POST` | `/api/v1/auth/refresh/` | public | Exchange a refresh token for a new pair (rotation) |
| `POST` | `/api/v1/auth/logout/` | public | Revoke the session of a refresh token |
| `GET` / `PATCH` | `/api/v1/users/user/me/` | authenticated | Read or update your own profile |
| `GET` | `/api/v1/users/user/` | `can_view_user` | List users (paginated) |
| `GET` | `/api/v1/users/user/{id}/` | `can_view_user` | User detail |
| `PATCH` | `/api/v1/users/user/{id}/` | `can_edit_user` | Change names, groups, or (re)activate a user |
| `DELETE` | `/api/v1/users/user/{id}/` | `can_disable_user` | Disable a user and end all their sessions |
| `GET` | `/api/health/`, `/api/ready/` | public | Liveness and readiness checks |

Groups and the permissions they grant are defined in `app/users/constants.py`: `admin` has every user permission, `member` and `viewer` will get the permissions of the example domain.

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
| `just upgrade` | Upgrade the dependencies within the pinned ranges |

## Project structure

```
app/
├── main.py              # create_app() factory: lifespan, CORS, routers, exception handlers
├── api/
│   ├── router.py        # /api: health and readiness checks + versioned routers
│   └── v1/router.py     # /api/v1: aggregates the domain routers
├── core/                # infrastructure: settings, database, exceptions, handlers
├── commons/             # shared building blocks: base model, UTCDateTime, pagination
├── auth/                # login, tokens, security primitives, auth dependencies
├── users/               # users domain: models, schemas, services, router, commands
├── cli/                 # Typer management CLI
└── migrations/          # Alembic environment and revisions
tests/
├── conftest.py          # app, client and database fixtures (rolled back after each test)
├── factories/           # polyfactory factories
├── pytest_plugins/      # fixtures grouped by domain, including the personas
└── ...                  # one folder per app package
scripts/                 # entrypoint, check, test and coverage scripts
```

New features live in their own **domain package** (`app/<domain>/` with `models.py`, `schemas.py`, `services.py` and `router.py`). Their routers are mounted in `app/api/v1/router.py`, and their tests go in `tests/<domain>/`.

## Design decisions

- **The database is the source of truth for integrity.** Uniqueness and foreign keys are database constraints. Services simply commit, and a single exception handler turns violations into `409 Conflict` or `422 Unprocessable Content`.
- **Errors are meant for machines too.** Every error response looks like `{"detail": {"message": "...", "errorCode": "NOT_FOUND"}}`, so clients can branch on a stable code instead of parsing messages. Validation errors add an `errors` list (`field`, `message`, `type`) and never echo the submitted values, which may contain passwords or personal data.
- **One app factory.** `create_app()` builds the application for production and for the tests alike, so what is tested is what runs.
- **Refresh tokens live in the database.** Access tokens are short-lived JWTs (15 minutes) carrying only the user id. Refresh tokens are random strings stored as SHA-256 hashes: every refresh revokes the token and issues a new one in the same family, presenting a revoked token ends the whole family (stolen token detection), and logout really ends the session.
- **Every request reads the user.** Disabling a user takes effect immediately, even while their access token is still valid; permissions are computed from the groups on every request, so changing a group needs no new login.
- **Security primitives behind interfaces.** Services depend on the `PasswordHasher` and `AccessTokenCodec` protocols, not on argon2 or JWT, so implementations can be swapped and faked in tests.
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
| `FASTAPI_DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `FASTAPI_DATABASE_MAX_OVERFLOW` | `10` | Extra connections allowed above the pool size |
| `FASTAPI_SECRET_KEY` | — (required, at least 32 characters) | Signs the access tokens; generate one with `openssl rand -hex 32` |
| `FASTAPI_JWT_ALGORITHM` | `HS256` | `HS256`, `HS384` or `HS512` |
| `FASTAPI_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `FASTAPI_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `SENTRY_DSN` | — | Enables Sentry in the `remote` image |
| `WEB_CONCURRENCY` | `2` | Number of gunicorn workers |

Docker Compose also reads `BACKEND_BUILD_TARGET` (`remote` by default), `BACKEND_PORT` and `POSTGRES_PORT`.

> **Database URL in Docker vs on your machine.** `FASTAPI_DATABASE_URL` in `.env` points to `localhost`, for the commands you run on your machine. Inside Docker Compose the backend reaches the database through the `postgres` service instead: compose sets the container's `FASTAPI_DATABASE_URL` from `DATABASE_URL`, which defaults to the compose database. Set `DATABASE_URL` only to point the container to another database.

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
- [ ] Sign in with Google
- [ ] Example `todos` domain: permissions, ownership, filtering, search, pagination, soft delete, CSV export
- [ ] JSON logs with request id, more management commands
- [ ] Architecture documentation and ADRs

## License

[MIT](LICENSE)
