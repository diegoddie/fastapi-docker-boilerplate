# 0010. External accounts are linked explicitly, never by email

- Status: Accepted
- Date: 2026-10-14
- Amends: [0007](0007-google-sign-in-with-id-tokens.md)

## Context

0007 linked a Google account to the existing user with the same email, when
Google said the email was verified. The email does not prove that the person
signing in owns *this* account:

- **Account pre-hijacking.** Registration does not verify emails, so anyone can
  register `mario@gmail.com` with a password of their own. When Mario later signs
  in with Google, his Google account is linked to that account, and the attacker,
  who still knows the password, shares it with him.
- **Addresses that change hands.** Google reports `email_verified` for any
  address it once verified, but it is authoritative only for Gmail and Google
  Workspace addresses. A Google account created with a work address stays
  "verified" after its owner leaves the company.

## Decision

- The first Google sign-in still creates a member, if the email is verified and
  no user has it.
- If a user with that email exists, the sign-in answers `409 ACCOUNT_EXISTS`:
  nothing is linked.
- An authenticated user links a Google account with
  `POST /api/v1/auth/google/link/`, sending the ID token **and their password**:
  a stolen access token alone cannot add a way into the account. An external
  account linked to someone else answers `409 EXTERNAL_ACCOUNT_IN_USE`; linking
  the same one twice changes nothing.

## Consequences

- Neither an attacker who registered the address first nor a former owner of
  the address can reach an account through Google.
- A user who registered with a password and then tries Google sees an error
  first; the frontend asks for the password and calls the link endpoint with
  the ID token it already has (valid for about an hour).
- Users without a password (created through Google) cannot link another
  external account until they can set one.

## Alternatives considered

- **Link only addresses Google is authoritative for** (Gmail, Workspace):
  closes the changed-hands case, not pre-hijacking.
- **Link automatically, then drop the password and end the other sessions**:
  removes the attacker, but also the password of a legitimate user.
- **Verify emails at registration**: closes pre-hijacking too, but needs an
  email service; it can be added later, and linking stays explicit anyway.
