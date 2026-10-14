"""The core constants."""

REQUEST_ID_HEADER = "X-Request-ID"
# Why: an id received from a client ends up in every log line of its request, so
# only short ids made of safe characters are accepted (no spaces or newlines).
REQUEST_ID_PATTERN = r"[A-Za-z0-9._-]{1,128}"
