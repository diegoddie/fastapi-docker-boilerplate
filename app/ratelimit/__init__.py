"""
The ratelimit package: at most N requests per period, counted per key.

The counters live in PostgreSQL, so every worker and every container share
them; ``RateLimiter`` keeps the storage swappable (e.g. Redis).
"""
