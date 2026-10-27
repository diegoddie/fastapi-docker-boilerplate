"""
The analytics package: product analytics and feature flags with PostHog.

Services record the moments that matter to the product through ``Analytics``
(``analytics.capture(USER_SIGNED_UP, user.id, ...)``), and routes can be
behind a feature flag (``require_feature_flag("new-export")``). Users are
identified by their id only. Without ``FASTAPI_POSTHOG_API_KEY`` nothing is
sent and every flag is off.
"""
