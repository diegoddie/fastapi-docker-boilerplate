# CLAUDE.md

FastAPI backend: async SQLModel on PostgreSQL, Python 3.14, uv, just, Docker.
`app/todos/` is the reference implementation: when adding or changing a feature,
mirror it. Architecture and the reasons behind it: `docs/ARCHITECTURE.md`,
`docs/adr/`. To add a domain, use the `new-domain-app` skill.

## Commands

```bash
docker compose up -d postgres && just migrate-forward   # database for tests and server
just fix                  # format, auto-fix lint, mypy strict: run after every change
just test                 # check + alembic check + tests, 100% branch coverage required
just pytest tests/todos -k create   # a subset, with output
just forge "add invoice table"      # migration from the models, then review it
just audit                # known vulnerabilities in the locked dependencies
just manage users createsuperuser
docker compose run --rm backend just test               # same, inside Docker
```

## Layout

- `app/core/`: settings, database session, exceptions, exception handlers, model registry
- `app/commons/`: base model, column types, base schemas, pagination, CSV export
- `app/filters/`: `FilterBase` for list filters, search and ordering
- `app/auth/`: login, tokens, Google sign-in, `AuthenticatedUser`, `require_any_permissions`
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
  Register every table model in `app/core/models.py`.
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
- `# pragma: no cover` only for `TYPE_CHECKING` blocks, CLI wrappers and
  optional imports.

## Definition of done

`just fix` clean, `just test` green with 100% coverage, migration created and
reviewed (`just forge`), README / docs updated when behavior or configuration
changes. Branches `feat/<x>` or `fix/<x>`, conventional commits, PR to `main`
with a green CI.
