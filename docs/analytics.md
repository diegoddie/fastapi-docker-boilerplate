# Product analytics and feature flags

With `FASTAPI_POSTHOG_API_KEY` set (the project API key, `phc_...`), the backend sends events to [PostHog](https://posthog.com); without it nothing is sent and every flag is off.

- **Events** come from the services, after the commit, through `Analytics` (`app/analytics/`): `user_signed_up` (with `method`: `password` or `google`), `email_verified` and `todo_created` (with the priority and whether it has a due date, never the title). The service gets `analytics` from the route (`AnalyticsDep`), like the email sender; `capture` only queues the event, and a background task sends the queue in batches.
- **Users** are identified by their id only: never an email or a name. In the frontend, call `posthog.identify(user.id)` after the login (the id comes from `GET /api/v1/users/user/me/`), so its events and the backend's belong to the same person.
- **Feature flags**: put a route behind one with `dependencies=[Depends(require_feature_flag("new-export"))]`; users without the flag get `404`, as if the route did not exist. Every check asks PostHog (`FASTAPI_POSTHOG_FEATURE_FLAGS_TIMEOUT_SECONDS`, 1 s); when it does not answer, the flag is off.
- No test sends anything to PostHog: the `fake_analytics` fixture records the events and turns on the flags a test lists.
