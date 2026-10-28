# Changelog

The changes of the template, newest first. Versions follow [Semantic Versioning](https://semver.org/): a new major version changes what a generated project gets, or how it updates.

## [2.0.0] - Unreleased

A rewrite. The boilerplate is now a [Copier](https://copier.readthedocs.io/) template: a project generated from it keeps receiving the template's improvements with `copier update`, and the optional modules can be turned on or off at any time.

### Template

- Generation with your project's name, description and author; the template is a working app, and generating a project removes the modules left out ([ADR 0013](docs/adr/0013-the-template-prunes-a-working-app.md)).
- Options: `background_jobs` (cron or Celery), `sentry`, `payments` (Polar), `posthog`, `ai`.
- Migrations in branches, one per module with tables, so every combination of modules has a valid history ([ADR 0014](docs/adr/0014-migrations-in-branches.md)).
- A CI of its own: six projects whose options meet every value of every other option, each running its own CI; a project generated from the previous version, changed and updated; every combination of the options every week.

### Application

- **Authentication**: registration with email verification, password login and reset, Sign in with Google with accounts linked explicitly, short-lived JWTs and rotating refresh tokens stored hashed, with reuse detection and a grace period for concurrent refreshes, and the takeover of an unverified account by whoever proves the address.
- **Hardening**: rate limits counted in PostgreSQL and shared by every worker, password hashing off the event loop and capped in memory, no database connection held while waiting on a slow call, a CSV export streamed with a server-side cursor.
- **Permissions** by group, checked on every request; resources of others answer `404`.
- **Example domain** (`todos`): CRUD, ownership, filters, search, ordering, pagination, soft delete, CSV export safe from formula injection.
- **Errors** in one shape with a machine-readable code; database integrity errors become `409` and `422`.
- **Structured logs** with a request id, in JSON in production.
- **Management CLI**: `createsuperuser`, `seed`, `shell`, `purge`.
- **Modules**: error reporting with Sentry; background jobs with Celery and Redis; AI features with Claude through LangChain, traced in Langfuse; product analytics and feature flags with PostHog; subscriptions with Polar.
- **Quality**: 100% branch coverage, mypy strict, ruff, bandit, warnings as errors, tests on a real PostgreSQL in parallel, `pip-audit` and Dependabot.
- **Documentation**: an architecture overview, 18 decision records, and a `CLAUDE.md` with a skill for Claude Code.
- Python 3.14, FastAPI 0.143, SQLAlchemy 2.1, PostgreSQL 18, uv and just.

### Upgrading from 1.0.0

Version 1.0.0 is not a Copier template, so a project started from it cannot be updated: generate a new project and move your domain code into it.

## [1.0.0] - 2025-07-16

A FastAPI CRUD API for todos on PostgreSQL, with Docker, Alembic and uv.

[2.0.0]: https://github.com/diegoddie/fastapi-docker-boilerplate/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/diegoddie/fastapi-docker-boilerplate/releases/tag/v1.0.0
