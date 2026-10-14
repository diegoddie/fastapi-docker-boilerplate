# 0007. Google sign-in with ID tokens verified by the backend

- Status: Accepted
- Date: 2026-10-13

## Context

Users should be able to sign in with Google. The API serves web and mobile
frontends, so the backend should not depend on browser redirects or cookies.

## Decision

- The frontend uses Google's sign-in button and receives an **ID token**; it
  sends it to `POST /api/v1/auth/google/`.
- The backend verifies the token with Google's public keys (signature, issuer,
  audience = our client id, expiry) and answers with the same token pair as the
  password login (see [0002](0002-refresh-tokens-in-the-database.md)).
- External accounts live in their own table (`provider`, `subject`, `user_id`):
  the first sign-in creates a member without a password, or links the account
  with the same email **only if Google verified it**; next sign-ins use the
  Google account id, even if the email changed.
- Providers implement the `IdentityProvider` protocol; the feature is disabled
  until `FASTAPI_GOOGLE_CLIENT_ID` is set. No client secret is needed.

## Consequences

- One endpoint, no redirects, state or cookies: the same flow serves web and
  mobile clients.
- Adding another provider (GitHub, Apple) means adding a class and a route.
- An unverified email can neither create a duplicate of an existing account nor
  take it over.
- Google's keys are fetched over the network (cached); if Google is unreachable
  the endpoint answers `503`, not `401`.

## Alternatives considered

- **Authorization code flow handled by the backend**: works without a frontend,
  but needs redirects, `state`, PKCE and a way to hand the tokens back.
- **A hosted identity provider** (Zitadel, Keycloak, Auth0): more features
  (MFA, admin console), one more service to run; a good fit for larger projects,
  the `IdentityProvider` protocol keeps the door open.
