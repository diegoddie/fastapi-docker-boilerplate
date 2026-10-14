# 0006. Settings for what varies by environment, constants for the rest

- Status: Accepted
- Date: 2026-10-13

## Context

Values used by the code fall in two groups: some must change between
development, CI and production (database URL, secret key, URLs of external
services, timeouts), others are facts of the code (permission names, column
lengths, issuers of Google tokens). Mixing them makes configuration risky (a
fact turned into a setting can be misconfigured) and code hard to read (magic
values inline).

## Decision

- Environment-dependent values live in `app/core/config.py` (pydantic-settings,
  `FASTAPI_` prefix), with safe defaults or none for secrets.
- Code facts live in the `constants.py` of the package that owns them and are
  imported where needed; no magic values inline.
- Security-relevant facts (e.g. the accepted token issuers) are never settings.

## Consequences

- Deployments only touch environment variables documented in the README.
- A value stored in the database (e.g. the provider name `google`) cannot drift
  between environments.
- A column length is declared once and reused by the model and the schemas.

## Alternatives considered

- **Everything in settings**: flexible, but facts become misconfigurable and
  the settings grow with domain data.
- **Constants inline in each module**: duplicated values, harder to find.
