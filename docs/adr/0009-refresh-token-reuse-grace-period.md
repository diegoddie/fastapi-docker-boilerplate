# 0009. A grace period for refresh token reuse

- Status: Accepted
- Date: 2026-10-14
- Amends: [0002](0002-refresh-tokens-in-the-database.md)

## Context

With rotation (0002), presenting a revoked refresh token ends the whole session,
because it means a token was stolen and replayed. But the same thing happens
without any attacker: two browser tabs sharing the token, or two requests sent
together when the access token expires, refresh with the same token at the same
moment. The first one rotates it, the second one looks like a replay, and the
user is logged out at random. Asking every client to serialize its refreshes
moves a server problem into each frontend.

## Decision

- A token rotated less than `FASTAPI_REFRESH_TOKEN_REUSE_GRACE_SECONDS` ago
  (30 by default, `0` disables it) still gets a new pair in the same family,
  **as long as the family has an active token**: after a logout, a disabled
  account or a detected replay, the family has none and the request fails.
- The grace period starts at the first rotation and is never extended.
- After the grace period, reuse ends the session as before.
- Expired tokens are deleted by `just manage auth purge-tokens`; revoked tokens
  are kept until they expire, because they are what detects a replay.

## Consequences

- Concurrent refreshes no longer log users out; clients need no coordination.
- An attacker replaying a stolen token within the grace period gets a pair
  too, where before the session would have ended. The window is short, and a
  replay after it still ends every branch of the family.
- A family can briefly have more than one active token.

## Alternatives considered

- **Answer `401` without ending the session**: no logout, but the second tab
  still gets an error, and most clients log the user out on a failed refresh.
- **Return the token already issued by the rotation**: the plain token is never
  stored (only its hash), so it cannot be returned again.
- **Clients serialize refreshes** (the previous consequence of 0002): fragile,
  and impossible across tabs without extra browser machinery.
