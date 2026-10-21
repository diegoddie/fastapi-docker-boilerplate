# 0014. Migrations in branches, one per optional module

- Status: Accepted
- Date: 2026-10-21

## Context

Alembic migrations form a chain: each revision names the one before it. A
project generated without an optional module (e.g. payments) must not create
that module's tables, but a module's revision in the middle of the chain cannot
be removed without breaking it. The template must also keep working for
databases already migrated with the current, linear history.

## Decision

- The existing revisions form the **main** branch: the first one carries the
  label `main`. Labels are not stored in the database, so migrated databases
  are unaffected.
- An optional module with tables has **its own branch**, in its own folder of
  `app/migrations/versions/` listed in `version_locations`: its first revision
  has no parent, a label with the module's name, and `depends_on` the revision
  that creates `user`. Leaving the module out removes the folder, and its
  branch with it. `version_locations` lists one folder per line, so that a
  module's line sits between the template's markers like any other.
- Every branch is applied: the entrypoint and `just migrate-forward` run
  `alembic upgrade heads`, in one run, so the advisory lock still serializes
  replicas. `alembic check` compares the models with all the heads.
- `just forge` adds to `main@head`, `just forge-module <module>` to a module's
  branch; `just migrate-merge` merges heads that diverged, e.g. when a template
  update brings migrations next to the project's own.

## Consequences

- Every combination of modules has a valid history, from the same files.
- A database can carry several heads; `alembic current` lists one per branch,
  and downgrades name the branch (`main@-1`, `payments@base`).
- Turning a module off in an existing project removes its code, not its tables:
  run `alembic downgrade <module>@base` first.

## Alternatives considered

- **One linear history with every module's tables**: tables of modules a
  project does not use, and a model registry that no longer matches them.
- **Squashing the history into a new initial revision per variant**: breaks
  existing databases, and the variants would no longer share revisions.
- **Generating the initial migration at generation time**: needs a database
  while Copier runs, and every template update would conflict with it.
