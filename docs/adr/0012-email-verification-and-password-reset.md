# 0012. Email verification and password reset

- Status: Accepted
- Date: 2026-10-16
- Amends: [0010](0010-external-accounts-are-linked-explicitly.md)

## Context

Registration did not check that the person owns the address. After 0010,
someone who registered `mario@gmail.com` with a password of their own could no
longer get into Mario's account through Google, but Mario could not get in
either: Google sign-in answered `409 ACCOUNT_EXISTS`, he did not know the
password, and there was no way to reset it. Users created through Google had no
password at all, and nobody could recover a forgotten one.

## Decision

- **Verified addresses.** `user.datetime_email_verified` is set when a person
  proves they own the address: they open a link sent to it, or sign in with a
  provider authoritative for it (Google, for Gmail addresses and the domain of a
  Workspace account). Unverified users can still log in.
- **Single-use tokens.** Random, stored as SHA-256 hashes in `onetimetoken` with
  a purpose and an expiry (24 hours to verify, 30 minutes to reset), deleted when
  used; a new one replaces the user's previous ones. The links point to the
  frontend (`FRONTEND_URL`), with the token in the fragment (`#token=`), which
  browsers never send to servers.
- **Endpoints.** Registration sends a verification link;
  `POST /auth/email/verification/` sends a new one; `POST /auth/email/verify/`
  checks it. `POST /auth/password/forgot/` always answers `202`, whether the
  email exists or not; `POST /auth/password/reset/` sets the new password and
  ends every session.
- **The owner of an address wins over an unverified account.** When the address
  is proven for the first time (a password reset on an unverified account, or a
  Google sign-in authoritative for it), every way in set up before is removed:
  sessions and linked external accounts (and, for Google, the password). A
  verified account still answers `409 ACCOUNT_EXISTS` to Google, as in 0010, and
  an unverified one cannot link external accounts.
- **Emails leave after the response.** Services depend on an `EmailSender`; the
  request gets one that queues the email as a background task, delivered by SMTP
  (any provider) or written to the logs locally. A failed delivery is logged
  without the recipient or the text.
- **Rate limits.** `RATE_LIMIT_EMAILS_PER_HOUR` (5) per recipient, whatever the
  IP, so nobody can flood someone's inbox; the per-IP limit of 0011 applies too.

## Consequences

- Squatting an address no longer locks its owner out: "forgot password" or
  Google gives the account back, and the squatter loses every way in.
- The SMTP server's latency or downtime never reaches the client; a lost email
  is visible in the logs, and the user can ask for a new one.
- A user who registered, linked nothing and never opened the verification link
  loses the password if they later sign in with an authoritative Google account:
  they proved the address only then.
- A disabled user receives no reset link, and a link issued before the account
  was disabled does not work.
- `just manage purge` also deletes the expired single-use tokens.
- The answer of "forgot password" does not reveal registered emails; the time it
  takes may differ slightly, since only existing users get a token.

## Alternatives considered

- **Block unverified users until they verify**: safer for the data of a fresh
  account, but every typo in an address locks the user out; apps that need it
  can check `is_email_verified` where it matters.
- **Signed, stateless tokens (e.g. a JWT in the link)**: no table, but they
  cannot be used only once or revoked when a new one is sent.
- **Send emails inline**: simpler, but the request waits for the SMTP server and
  fails when it is down.
- **A task queue (Celery)** for emails: retries and isolation, but a broker to
  run; background tasks are enough until the project adds one.
