# 0017. Product analytics and feature flags with PostHog, as an option

- Status: Accepted
- Date: 2026-10-27

## Context

Product teams want to know what users do (who signs up, who comes back, which
features are used) and to turn features on for some users first. Most of it
happens in the frontend, but the moments that matter most happen in the
backend: an event sent by the browser can be blocked or lost, one sent by the
server cannot. Feature flags must be checked where the feature runs.

## Decision

- Generating a project asks `posthog` (no by default). The module lives in
  `app/analytics/`; without `FASTAPI_POSTHOG_API_KEY` nothing is sent and every
  flag is off.
- The services record events through the `Analytics` protocol, which the
  route passes in like the email sender (ADR 0012): `PostHogAnalytics`,
  `DisabledAnalytics`, and `FakeAnalytics` in the tests. The template records
  `user_signed_up` (password or Google), `email_verified` and `todo_created`,
  after the commit.
- Users are identified by their id, the PostHog distinct id the frontend uses
  too after the login; events carry no personal data and no text users wrote.
- The client is PostHog's async one: `capture` puts the event in a queue that
  a background task sends in batches, so a request never waits for PostHog;
  the queue is flushed at shutdown.
- `require_feature_flag(flag)` hides a route from the users without the flag
  with a `404`. It asks PostHog on every request, with a short timeout
  (`POSTHOG_FEATURE_FLAGS_TIMEOUT_SECONDS`, 1 s); a timeout or an error turns
  the flag off, so an outage never turns a feature on.

## Consequences

- The events are explicit: each one is a line in a service, reviewed and
  tested like the rest; adding one is a constant and a `capture`.
- A route behind a flag pays a call to PostHog on every request. The async
  client has no local evaluation; a project with many flagged routes may cache
  the flags per user, or use the sync client's local evaluation in a thread.
- The async client is bound to the event loop that creates it: the analytics
  belong to the API, not to Celery tasks, which run in a loop of their own.
- Shutting down while PostHog is unreachable waits a few seconds for the
  retries of the last batch.

## Alternatives considered

- **Events from the logs** (a structlog processor forwarding chosen events):
  no new parameter in the services, but analytics would depend on the log
  level and on the wording of log events.
- **Capturing in the routes**: simpler signatures, but the routes stay thin and
  a route does not always know what the service did (e.g. a first Google
  sign-in that creates the user).
- **Segment, Mixpanel, Amplitude**: similar for events, but PostHog also gives
  feature flags, experiments and an EU cloud in one tool, and can be
  self-hosted.
