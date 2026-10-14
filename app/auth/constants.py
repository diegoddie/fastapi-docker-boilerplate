"""The auth package constants."""

GOOGLE_PROVIDER = "google"
# Why: fixed by Google and security-relevant, so not configurable: a token from any
# other issuer must be rejected.
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

# The names of the rate limits, part of their counter keys.
AUTH_REQUESTS_RATE_LIMIT = "auth_requests"
REGISTRATIONS_RATE_LIMIT = "registrations"
PASSWORD_ATTEMPTS_RATE_LIMIT = "password_attempts"  # noqa: S105  # nosec B105
