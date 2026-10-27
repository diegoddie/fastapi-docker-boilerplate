# CLAUDE.md

FastAPI backend: async SQLModel on PostgreSQL, Python 3.14, uv, just, Docker.
`app/todos/` is the reference implementation: when adding or changing a feature,
mirror it. Architecture and the reasons behind it: `docs/ARCHITECTURE.md`,
`docs/adr/`. To add a domain, use the `new-domain-app` skill.

## Commands

```bash
docker compose up -d postgres && just migrate-forward   # database for tests and server
just fix                  # format, auto-fix lint, mypy strict: run after every change
just test                 # check + alembic check + tests in parallel, 100% branch coverage required
just pytest tests/todos -k create   # a subset, with output
just forge "add invoice table"      # migration from the models (main branch), then review it
just audit                # known vulnerabilities in the locked dependencies
just manage users createsuperuser
just manage seed          # demo users (Alice admin, Bob member, Carol viewer) and todos, local only
just manage shell         # IPython with settings, session, models; top-level await
just manage purge         # delete expired refresh tokens and rate limit counters (daily cron)
just worker               # Celery worker (needs Redis: docker compose up -d redis)  # copier:celery
just beat                 # Celery beat: sends the scheduled tasks  # copier:celery
docker compose run --rm backend just test               # same, inside Docker
```

## Layout

- `app/core/`: settings, database session, exceptions, exception handlers, logging (`logs.py`), request id middleware, model registry
- `app/commons/`: base model, column types, base schemas, pagination, CSV export
- `app/filters/`: `FilterBase` for list filters, search and ordering
- `app/ratelimit/`: `RateLimiter` (PostgreSQL counters), `ClientIP`, `RateLimiterDep`
- `app/emails/`: `EmailSender`, `EmailSenderDep` (sends after the response; console locally, SMTP remotely)
- `app/auth/`: login, tokens, Google sign-in, `AuthenticatedUser`, `require_any_permissions`
- `app/cli/`: the Typer root (`main.py`), cross-domain commands (`seed`, `shell`), helpers (`utils.py`)
- `app/payments/`: `PaymentProvider` and its Polar implementation, checkout, portal, webhooks, the `pro` group (`services.py`), migrations in `app/migrations/versions/payments/` <!-- copier:payments -->
- `app/analytics/`: `Analytics` (PostHog, disabled, fake), `AnalyticsDep`, `require_feature_flag`, the event names (`constants.py`) <!-- copier:posthog -->
- `app/ai/`: the chat model (`dependencies.py`), `generate` and the AI features (`services.py`), prompts, answer schemas, Langfuse tracing <!-- copier:ai -->
- `app/jobs/`: the Celery app and the beat schedule (`worker.py`), the tasks (`tasks.py`) <!-- copier:celery -->
- `app/<domain>/`: `constants.py`, `enums.py`, `models.py`, `schemas.py`, `services.py`, `router.py` (+ `commands/`)
- `tests/<domain>/` mirrors `app/`; fixtures in `tests/pytest_plugins/`, factories in `tests/factories/`

## Code conventions

- **Routes are thin**: one service call, no queries. Handlers are named
  `<action>_<resource>_route` (`create`, `list`, `detail`, `update`, `delete`,
  `download`), docstring `"""Create todo route."""`. Every decorator sets
  `summary`, `status_code=status.HTTP_...`, `response_model` and the permission:
  `dependencies=[Depends(require_any_permissions([CAN_CREATE_TODO]))]`.
- **URLs**: `/api/v1/<domains>/<resource>/{<resource>_id:uuid}/`, kebab-case,
  trailing slash. POST → 201 with the body, PATCH → 204 (partial, no PUT),
  DELETE → 204 (soft delete), GET → 200.
- **Services**: a `<Model>Service` class of `@staticmethod`s, arguments
  `(id, payload, session, user)`. Access rules only in `get_where_clause(user)`,
  used by every query; a resource the user cannot reach is a 404, never a 403.
  List methods return the query (`list_query`), the route paginates it.
- **Models**: `Base<Model>(SQLModel)` with the fields shared with the schemas,
  then `<Model>(Base<Model>, BaseSQLModel, table=True)` with `id = uuid7`, foreign
  keys and indexes. Datetimes: `datetime.now(UTC)`, columns `sa_type=UTCDateTime`.
  Enums: `StrEnum` + `sa_column=Column(pg_enum(MyEnum), nullable=False)`.
  Register every table model in `app/core/models.py`. Deletes are soft, so a
  value that must be reusable after a delete is unique among the active rows
  only: `Index(..., unique=True, postgresql_where=text("datetime_disabled IS NULL"))`
  instead of `unique=True` (see the `new-domain-app` skill).
- **Schemas**: `<Model>PublicSchemaCreate` / `Update` / `Response` (camelCase via
  `BasePublicSchema`), `<Model>CSVSchema`, `<Model>Filter`. Update schemas have
  every field optional and use `reject_null` for non-nullable columns.
- **Errors**: raise the subclasses in `app/core/exceptions.py` with a specific
  `error_code` (`TODO_NOT_FOUND`); never return database messages. Uniqueness
  and foreign keys are database constraints: let `IntegrityError` reach the
  handler (409 / 422).
- **Permissions**: `CAN_<ACTION>_<RESOURCE> = "can_<action>_<resource>"` in the
  domain `constants.py`, granted to groups in `GROUPS` (`app/users/constants.py`).
- **Settings vs constants**: what changes between environments (secrets, URLs of
  external services, timeouts) goes in `app/core/config.py` with the `FASTAPI_`
  prefix; code facts (permission names, lengths, fixed values) go in the
  package's `constants.py`. No magic values inline.
- **Style**: module docstring `"""The <package> package <module>."""`, a
  docstring on every function, `# Why:` comments for non-obvious decisions,
  mypy strict (`# type: ignore[<code>]` only with the code), line length 88.
- **External services** go behind a `Protocol` and a FastAPI dependency, so tests
  replace them (see `app/auth/identity.py`).
- **Logging**: `logger = structlog.get_logger(__name__)`, then an event name in
  snake_case with fields: `logger.info("todo_created", todo_id=str(todo.id))`.
  `request_id` and `user_id` are added automatically; never log passwords,
  tokens, request bodies or personal data. No `print` (ruff `T20`).
- **Management commands**: logic in a service method or in
  `async def execute_<command>(..., session)`, tested against the test
  database; the Typer function is a thin wrapper marked `# pragma: no cover`
  that calls `run_with_session` (`app/core/database.py`) and prints with
  `typer.secho`. Local-only commands call `require_local_environment()`.
  Register them in `app/cli/main.py`.
<!-- copier:payments:start -->
- **Payments**: the services talk to `PaymentProvider`, never to Polar's SDK.
  The `pro` group is a copy of the `subscription` table, recomputed by the
  webhooks; never set it elsewhere. Paid features are permissions of
  `GROUPS[Group.PRO]`. Payments migrations go in their branch:
  `just forge-module payments "..."`.
<!-- copier:payments:end -->
<!-- copier:posthog:start -->
- **Analytics**: a service that records an event takes `analytics: Analytics`
  (the route injects `AnalyticsDep`) and calls `analytics.capture(EVENT,
  user.id, {...})` after the commit; event names live in
  `app/analytics/constants.py`. Properties never hold personal data or text
  users wrote. A route behind a flag adds
  `Depends(require_feature_flag("<flag>"))`.
<!-- copier:posthog:end -->
<!-- copier:ai:start -->
- **AI features**: a service method takes `ChatModelDep` and
  `TracingCallbacksDep` from the route, commits its reads, then calls
  `generate(chat_model, messages, Schema, name=..., user=..., callbacks=...)`.
  Prompts live in `app/ai/prompts.py` and the answer schema in `schemas.py`
  (its docstring and field descriptions are part of the prompt). Never set
  `temperature`, `top_p` or `top_k`, nor force a tool: the current models
  reject them. Routes add `Depends(get_chat_model)` then
  `Depends(limit_ai_requests)`.
<!-- copier:ai:end -->
<!-- copier:celery:start -->
- **Background jobs**: a task in `app/jobs/tasks.py` is a thin sync function
  that runs its logic (an `execute_<job>` coroutine or a service method) with
  `run_with_session`, and must be safe to run twice (late acknowledgement).
  Send it with `task.delay(...)` after the commit of what it reads; schedule it
  in `beat_schedule` (`app/jobs/worker.py`). Test the task with `task.apply()`
  and its logic against the test database.
<!-- copier:celery:end -->
- **Emails**: a service takes an `EmailSender` (the route injects
  `EmailSenderDep`) and awaits `sender.send(EmailMessage(...))`; the texts live
  in the domain's `emails.py` (see `app/auth/emails.py`). Never put secrets or
  tokens anywhere but the link, and never log the text.
- **Rate limits**: a public route that checks a password, sends emails or is
  costly gets a limit dependency (see `limit_login_attempts` in
  `app/auth/dependencies.py`); the numbers are settings.
- **Slow or blocking calls** (password hashing, sync SDKs, file I/O) never run
  on the event loop: `await run_in_threadpool(...)` inside an async method.
  Work that is heavy on CPU or memory also gets a `CapacityLimiter` of its own,
  so a burst of requests waits in line (see `Argon2PasswordHasher`).
- **Never wait holding a transaction**: before awaiting slow work (a password
  hash, an external service), end the reads with `await session.commit()`, so
  the connection goes back to the pool (see `AuthService.authenticate`).

## Test conventions

- One test per route and status code: `test_<action>_<resource>_route_<status>`,
  plus a suffix for scenarios (`_404_other_owner`); docstring
  `"""Test the create todo route 201."""`.
- Per module, a parametrized `test_route_401` and `test_route_403` over the routes.
- Write URLs in full in each request; no module-level constants or test data in
  test files (only `DUMMY_UUID`, needed by `parametrize`).
- Fixtures (personas with fixed uuid7 ids, fakes of external services) live in
  `tests/pytest_plugins/<domain>.py`, registered in `tests/conftest.py`;
  factories in `tests/factories/`; request helpers on `AsyncClient` in
  `tests/utils.py`. Authenticate with `async_client.login(user)`.
- Assert whole responses with `snapshot()` + dirty-equals (`IsUUID`,
  `IsDatetime(iso_string=True)`); after a write, `async_db_session.expunge_all()`
  and read the row back.
- Tests use a real PostgreSQL database, rolled back after each test; they never
  call external services. Warnings are errors.
- Tests of rate limits use the `start_of_minute` fixture (frozen clock), so a
  window never ends halfway through the test.
- No test sends emails (the console backend is forced); read the emails a test
  triggers with the `email_outbox` fixture, and the token of their link with
  `email_token(message)` from `tests/utils.py`.
- Tests of payments use `polar_provider` (the real provider on a fake API),
  `polar_webhook` (signs like Polar) and `polar_subscription` (event payloads);
  no test calls Polar. <!-- copier:payments -->
- Tests of events and flags use the `fake_analytics` fixture (`events`,
  `enabled_flags`); no test sends anything to PostHog. <!-- copier:posthog -->
- Tests of AI features use the `fake_chat_model` fixture: `answer(...)` and
  `fail(...)` prepare what the model does; no test calls Anthropic or Langfuse. <!-- copier:ai -->
- Assert logs with the `log_events` fixture: `log_events("http_request")` returns
  the structlog events with that name, as dicts.
- `# pragma: no cover` only for `TYPE_CHECKING` blocks, CLI wrappers and
  optional imports.

<!-- copier:template:start -->
## Template maintenance

This repository is also a Copier template ([ADR 0013](docs/adr/0013-the-template-prunes-a-working-app.md)):
`main` is the full app, and generating a project removes what its answers
leave out.

- Module code lives in its own package and files; in shared files (settings,
  routers, model registry, `pyproject.toml`, compose, docs) wrap a module's
  lines in `# copier:<module>:start` / `# copier:<module>:end`, or end a single
  line with `# copier:<module>` (HTML comments in Markdown, at the end of a
  table row). `!<module>` keeps lines only when the module is off;
  `template` marks what only the template needs.
- Module code is an addition, never an alternative: an import, an item of a
  multi-line list (with a trailing comma), a settings block, a router include.
- A line marker only goes on a statement that fits on one line: the formatter
  may split a longer one, leaving the marker on its last line alone. Use a
  block instead; `prune.py check` compiles every Python file with each module
  off and reports what would break.
- A new module needs its question in `copier.yml`, its paths in `_exclude`,
  its name in `MODULES` (`.copier/prune.py`), answer sets in
  `.copier/answers/`, and an ADR.
- A module with tables starts its own migration branch
  ([ADR 0014](docs/adr/0014-migrations-in-branches.md)): add
  `%(here)s/versions/<module>` to `version_locations` in `alembic.ini`, between
  block markers, then `uv run alembic revision --autogenerate --head base
  --branch-label <module> --depends-on 57fac5921361
  --version-path "$PWD/app/migrations/versions/<module>" -m "..."`; later
  migrations come from `just forge-module <module> "..."`.
- Check with `uv run --group template python .copier/prune.py check`,
  `just template-render .copier/answers/acme.yml /tmp/acme` (renders the
  working tree) and the template CI.

<!-- copier:template:end -->
## Definition of done

`just fix` clean, `just test` green with 100% coverage, migration created and
reviewed (`just forge`), README / docs updated when behavior or configuration
changes. Branches `feat/<x>` or `fix/<x>`, conventional commits, PR to `main`
with a green CI.
