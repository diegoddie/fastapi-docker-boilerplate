# Architecture decision records

Each record explains one decision: the context, what was decided, its
consequences and the alternatives that were discarded. Records are not edited
once accepted; a new record supersedes an old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-domain-packages-and-static-services.md) | Domain packages with thin routers and static-method services | Accepted |
| [0002](0002-refresh-tokens-in-the-database.md) | Refresh tokens stored in the database, with rotation | Accepted |
| [0003](0003-tests-on-a-real-database.md) | Tests on a real PostgreSQL database, rolled back after each test | Accepted |
| [0004](0004-uniform-error-envelope.md) | One error envelope with machine-readable codes | Accepted |
| [0005](0005-unreachable-resources-are-not-found.md) | Unreachable resources answer 404, deletes are soft | Accepted |
| [0006](0006-settings-and-constants.md) | Settings for what varies by environment, constants for the rest | Accepted |
| [0007](0007-google-sign-in-with-id-tokens.md) | Google sign-in with ID tokens verified by the backend | Accepted |
| [0008](0008-structured-logs-with-request-id.md) | Structured logs with a request id | Accepted |

To add one, copy the structure of an existing record, give it the next number
and add it to this table.
