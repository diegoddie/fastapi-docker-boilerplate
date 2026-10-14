# 0004. One error envelope with machine-readable codes

- Status: Accepted
- Date: 2026-10-08

## Context

By default FastAPI answers errors in several shapes: `{"detail": "Not Found"}`
for unknown routes, a list of validation errors that echoes the submitted
values, plain text for unexpected errors. Clients end up parsing messages, and
validation errors can send passwords back.

## Decision

Every error answers:

```json
{"detail": {"message": "…", "errorCode": "TODO_NOT_FOUND"}}
```

- Application errors raise subclasses of `BaseHTTPException` with a specific
  `error_code`.
- Handlers wrap framework errors (404, 405), validation errors (an `errors`
  list with `field`, `message`, `type`, without the input) and unexpected
  errors (500).
- Database integrity errors become `409` (unique) or `422` (foreign key, not
  null) with a generic message; only the constraint name is logged.

## Consequences

- Clients branch on `errorCode`, a stable contract, instead of on messages.
- No personal data or database structure leaks through error responses.
- Uniqueness is enforced by the database only: services just commit.

## Alternatives considered

- **FastAPI defaults**: inconsistent shapes and echoed input.
- **RFC 9457 problem details** (`application/problem+json`): a standard, but
  heavier than needed; it can be adopted later behind the same handlers.
