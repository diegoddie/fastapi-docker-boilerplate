"""The auth package constants."""

GOOGLE_PROVIDER = "google"
# Why: fixed by Google and security-relevant, so not configurable: a token from any
# other issuer must be rejected.
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
