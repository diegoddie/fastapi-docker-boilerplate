# 0003. Tests on a real PostgreSQL database, rolled back after each test

- Status: Accepted
- Date: 2026-10-09

## Context

Much of the behavior lives in the database: unique constraints, foreign keys,
Postgres enums, `timestamptz`, arrays, case-insensitive search. SQLite or mocks
would not test it. Recreating the schema for every test is slow.

## Decision

- The suite creates a `<database>-test` database (one per xdist worker), builds
  the schema once, and drops the database at the end.
- Each test opens a connection, begins a transaction and binds the session with
  `join_transaction_mode="create_savepoint"`: services commit as in production,
  and everything is rolled back when the test ends.
- The API client depends on that session, so no request can reach the
  development database.
- Every test gets a fresh app from `create_app()`; external services are
  replaced through dependency overrides and never called.
- Data comes from polyfactory factories and named personas with fixed ids.

## Consequences

- Tests catch constraint, type and query errors that mocks would hide.
- A running PostgreSQL is needed (`docker compose up -d postgres`, or the CI
  container).
- The suite stays fast (about 160 tests in under 30 seconds, less with xdist).
- Code that opens its own connections (e.g. CLI commands) is tested through the
  functions it calls, or by patching its session.

## Alternatives considered

- **SQLite in memory**: fast, but a different database.
- **`create_all` and `DELETE` for every test**: simple, but much slower.
- **Testcontainers per test session**: clean, but slower to start than the
  compose database already running.
