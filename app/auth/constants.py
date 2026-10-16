"""The auth package constants."""

GOOGLE_PROVIDER = "google"
# Why: fixed by Google and security-relevant, so not configurable: a token from any
# other issuer must be rejected.
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GMAIL_DOMAIN = "gmail.com"

# The pages of the frontend opened by the links in the emails.
# Why: the token goes in the fragment (#), which browsers never send to servers,
# so it cannot end up in access logs or Referer headers.
VERIFY_EMAIL_PATH = "/verify-email"
RESET_PASSWORD_PATH = "/reset-password"  # noqa: S105  # nosec B105

# The names of the rate limits, part of their counter keys.
AUTH_REQUESTS_RATE_LIMIT = "auth_requests"
EMAILS_RATE_LIMIT = "emails"
REGISTRATIONS_RATE_LIMIT = "registrations"
PASSWORD_ATTEMPTS_RATE_LIMIT = "password_attempts"  # noqa: S105  # nosec B105
