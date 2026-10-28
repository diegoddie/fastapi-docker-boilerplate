# FastAPI Docker Boilerplate

[![CI](https://github.com/diegoddie/fastapi-docker-boilerplate/actions/workflows/ci.yml/badge.svg)](https://github.com/diegoddie/fastapi-docker-boilerplate/actions/workflows/ci.yml) <!-- copier:template -->
![Python 3.14](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Coverage 100%](https://img.shields.io/badge/coverage-100%25-brightgreen)
![mypy strict](https://img.shields.io/badge/mypy-strict-2A6DB2)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A production-ready starting point for FastAPI backends: async SQLModel on PostgreSQL, strict quality gates, and a Docker setup that runs the same way on your laptop, in CI and in production.

<!-- copier:template:start -->
It distills the conventions I use on real-world FastAPI projects into a template: [generate a project](#generate-a-project) with Copier and start building on it in minutes.

> Looking for the original version? It is available at the [`v1.0.0`](https://github.com/diegoddie/fastapi-docker-boilerplate/tree/v1.0.0) tag.
<!-- copier:template:end -->

## Features

- **Async all the way**: FastAPI and SQLModel on PostgreSQL (SQLAlchemy 2 async, psycopg 3), migrations with Alembic
- **Authentication**: registration with email verification, password login and reset, Sign in with Google (accounts linked explicitly, never by email), short-lived JWTs and rotating refresh tokens stored hashed, with reuse detection
- **Hardened**: rate limits shared by every worker, password hashing off the event loop and capped in memory, a database connection never held while waiting on a slow call
- **Permissions**: users belong to groups, groups grant permissions, routes declare the one they need; resources of others answer `404`
- **Example domain (`todos`)**: CRUD, ownership, filters, search, ordering, pagination, soft delete and a streamed CSV export: the reference to copy
- **Consistent errors**: one shape with a machine-readable `errorCode` for every error, database integrity errors included
- **Structured logs**: JSON in production, a request id on every line and in `500` responses
- **Subscriptions with Polar**: checkout, customer portal and signed webhooks applied once and in order; an active subscription grants the `pro` group <!-- copier:payments -->
- **Product analytics with PostHog**: events from the services with the user id only, routes behind feature flags <!-- copier:posthog -->
- **AI features with Claude**: LangChain, answers validated against a schema, clear errors, a per-user limit, token counts in the logs, Langfuse tracing without the text <!-- copier:ai -->
- **Background jobs with Celery**: a worker and beat on Redis, a database session per task <!-- copier:celery -->
- **Error reporting with Sentry**, tagged with the request id, without personal data <!-- copier:sentry -->
- **Quality gates**: ruff, mypy strict, bandit, **100% branch coverage**, warnings as errors, tests in parallel on a real PostgreSQL rolled back after each test
- **One Docker image, three targets** (`remote`, `test`, `local`), CI on GitHub Actions with the same image, `pip-audit` and Dependabot
- **Documented**: architecture with diagrams, decision records, and a `CLAUDE.md` plus a skill so that Claude Code follows the conventions

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
| Logging | structlog |
| Monitoring | Sentry (production only) <!-- copier:sentry --> |
| Background jobs | Celery, Redis (Valkey) <!-- copier:celery --> |
| AI | LangChain, Claude (Anthropic), Langfuse <!-- copier:ai --> |
| Payments | Polar (polar-sdk) <!-- copier:payments --> |
| Product analytics | PostHog <!-- copier:posthog --> |

## Quickstart

Requirements: [Docker](https://docs.docker.com/get-docker/) with Docker Compose.

<!-- copier:template:start -->
To try the template itself (to start a project, [generate it](#generate-a-project) instead):

```bash
git clone https://github.com/diegoddie/fastapi-docker-boilerplate.git
cd fastapi-docker-boilerplate
```
<!-- copier:template:end -->

```bash
cp .env_template .env
docker compose up --build
```

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health/
- Readiness check: http://localhost:8000/api/ready/

The `.env` file selects the `local` image target and mounts the source code, so the server reloads on every change. The API docs are served only in the `local` environment unless `FASTAPI_DOCS_ENABLED` says otherwise.

Compose also starts the Celery worker (restarted on every change too), beat and Redis: see [Background jobs](docs/background-jobs.md). <!-- copier:celery -->

Create the first administrator, then log in from the docs with the **Authorize** button (the username is the email):

```bash
docker compose run --rm backend just manage users createsuperuser
```

Or fill the database with demo users (Alice admin, Bob member, Carol viewer, with the password you choose) and their todos:

```bash
docker compose run --rm backend just manage seed
```

<!-- copier:template:start -->
## Generate a project

The repository is a [Copier](https://copier.readthedocs.io/) template: it asks a few questions and writes a project with your name, your author and the modules you chose, ready to commit. Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/) and git.

```bash
uvx copier copy --trust gh:diegoddie/fastapi-docker-boilerplate my-api
```

Until `v2.0.0` is released, add `--vcs-ref main`: Copier otherwise picks the latest release, `v1.0.0`, which is not a Copier template.

`--trust` lets Copier run `.copier/prune.py`, which removes the code of the modules you left out, writes your name and author, and re-locks the dependencies with uv. How it works: [ADR 0013](docs/adr/0013-the-template-prunes-a-working-app.md).

| Question | Used for |
|---|---|
| `project_name`, `project_slug` | the title, and the names of the package, the Docker image and the database (the slug derives from the name) |
| `project_description`, `author_name`, `author_email`, `copyright_year` | `pyproject.toml`, the README, the license |

Then come the options, below.

<!-- copier:template:end -->
## Updates and options

The answers are saved in `.copier-answers.yml`: commit it, and bring in the template's improvements later with:

```bash
uvx copier update --trust
```

Copier merges the changes with yours; review them with `git diff` (and any `.rej` file) before committing. The same command turns a module on or off, with `--data <option>=<value>`:

| Option | Default | Module |
|---|---|---|
| `background_jobs` | `cron` | `cron`: `purge` is a command for your scheduler; `celery`: a Celery worker and beat on Redis |
| `sentry` | `true` | error reporting with Sentry in the `remote` image |
| `payments` | `none` | `polar`: subscriptions with Polar |
| `posthog` | `false` | product analytics and feature flags with PostHog |
| `ai` | `false` | AI features with Claude, traced in Langfuse |

A module with tables keeps its migrations in a branch of its own ([ADR 0014](docs/adr/0014-migrations-in-branches.md)): before turning payments off, drop its tables with `just migrate-backward payments@base`.

The template's CI checks these promises on every change: it generates six projects, whose options meet every value of every other option, and runs each project's own CI; it updates a project generated from the previous version, with changes of its own, and runs its CI again. Every Monday it generates all 32 combinations. <!-- copier:template -->

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

Background jobs: `docker compose up -d redis`, then `just worker` and `just beat` in other terminals. <!-- copier:celery -->

The tests run against a real PostgreSQL database: the suite creates a `<database>-test` database (one per xdist worker) and rolls back every change at the end of each test. `just test` runs them in parallel, one worker per CPU (`just test -n 0` for a single process; `just pytest` is always single-process, for debugging), and also runs `alembic check`, so the database must be migrated to the latest revision first.

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
| `just forge-module <module> "message"` | Create a new migration in the branch of an optional module |
| `just migrate-forward` | Apply all pending migrations (every branch) |
| `just migrate-backward <revision>` | Roll back to a revision (e.g. `main@-1`) |
| `just migrate-merge` | Merge migration branches that diverged into one head |
| `just manage users createsuperuser` | Create an administrator |
| `just manage seed` | Fill a local database with demo users and todos |
| `just manage shell` | IPython with the settings, a database session and the models loaded (top-level `await`) |
| `just manage purge` | Delete the expired refresh tokens and rate limit counters |
| `just worker` | Run a Celery worker (restart it after changing the code) <!-- copier:celery --> |
| `just beat` | Run Celery beat, which sends the scheduled tasks <!-- copier:celery --> |
| `just audit` | Check the locked dependencies for known vulnerabilities |
| `just upgrade` | Upgrade the dependencies within the pinned ranges |

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
├── jobs/                # Celery app, beat schedule and tasks  # copier:celery
├── ai/                  # Claude through LangChain: chat model, prompts, Langfuse tracing  # copier:ai
├── analytics/           # PostHog: events and feature flags  # copier:posthog
├── payments/            # Polar subscriptions: checkout, portal, webhooks, pro group  # copier:payments
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

- [Using the API](docs/api.md): the routes, Google sign-in, email verification and password reset, groups and permissions, list filters
- [Configuration](docs/configuration.md): every environment variable
- [Deploying to production](docs/deployment.md): the checklist
- [Subscriptions with Polar](docs/payments.md) <!-- copier:payments -->
- [Product analytics and feature flags](docs/analytics.md) <!-- copier:posthog -->
- [AI features](docs/ai.md) <!-- copier:ai -->
- [Background jobs with Celery](docs/background-jobs.md) <!-- copier:celery -->
- [Scheduled jobs](docs/scheduled-jobs.md) <!-- copier:!celery -->
- [Architecture](docs/ARCHITECTURE.md): layers, request lifecycle, authentication, data, errors, testing, runtime
- [Design decisions](docs/design-decisions.md), and the [decision records](docs/adr/README.md) behind them
- [CLAUDE.md](CLAUDE.md): the conventions in a form Claude Code follows; the [`new-domain-app`](.claude/skills/new-domain-app/SKILL.md) skill adds a domain step by step
- [Changelog](CHANGELOG.md) <!-- copier:template -->

## License

[MIT](LICENSE)
