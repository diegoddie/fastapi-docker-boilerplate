# 0002. Refresh tokens stored in the database, with rotation

- Status: Accepted, amended by [0009](0009-refresh-token-reuse-grace-period.md)
- Date: 2026-10-09

## Context

Access tokens must be short-lived, so clients need a long-lived credential to
get new ones. A purely stateless refresh token (a JWT nobody stores) cannot be
revoked: logout does nothing and a stolen token works until it expires.

## Decision

- Access tokens are JWTs valid for 15 minutes, carrying only the user id.
- Refresh tokens are random strings valid for 30 days, stored as SHA-256 hashes
  in the `refreshtoken` table, grouped by `family_id` (one family per login).
- Every refresh revokes the presented token and issues a new one in the same
  family (rotation).
- Presenting a revoked token revokes the whole family: either the client or an
  attacker is replaying a stolen token, and both copies stop working.
- Logout revokes the family of the given refresh token.
- Every request loads the user, so disabled users are rejected immediately.

## Consequences

- Logout and account disabling really end the sessions.
- A database lookup per refresh and a user lookup per request: negligible
  compared to the safety gained.
- The plain refresh token is never stored, so a database leak does not expose
  usable tokens.
- Two concurrent refreshes with the same token end the session (the second one
  looks like a replay); clients must serialize refreshes.

## Alternatives considered

- **Stateless refresh JWTs**: no revocation.
- **A token blacklist**: grows with every logout and still needs a lookup.
- **Server-side sessions with cookies**: simpler for a browser-only API, less
  suited to mobile and third-party clients.
