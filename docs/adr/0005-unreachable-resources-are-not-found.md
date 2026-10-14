# 0005. Unreachable resources answer 404, deletes are soft

- Status: Accepted
- Date: 2026-10-14

## Context

Users must only reach their own records (unless they have a "manage all"
permission). Answering `403` for someone else's record confirms that it exists.
Access rules repeated in every query drift apart over time. Deleted records are
sometimes needed later (audit, mistakes).

## Decision

- Each service defines `get_where_clause(user)` once; every query of the
  service (list, detail, update, delete, export) applies it.
- A record outside that clause answers `404`, exactly like a missing one.
- `403` is reserved for a missing permission on the action itself
  (e.g. a viewer creating a todo).
- `DELETE` sets `datetime_disabled`; the clause excludes disabled records, so
  they disappear from the API but stay in the database.

## Consequences

- The API never reveals which ids exist for other users.
- List, detail and write endpoints cannot disagree on what a user may reach.
- Disabled rows stay in the tables: unique constraints should account for them
  (e.g. partial indexes) when a value must be reusable after a delete.

## Alternatives considered

- **`403` for others' records**: leaks existence.
- **Hard delete**: simpler, but data is lost; it can still be added for
  specific resources.
