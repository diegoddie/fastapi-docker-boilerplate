"""The ratelimit package models."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.commons.types import UTCDateTime


class RateLimitCounter(SQLModel, table=True):
    """
    The requests counted for a key in one time window.

    Why: the key is stored as a hash, so the table holds no emails or IP
    addresses, and every key has the same length.
    """

    key_hash: str = Field(primary_key=True, max_length=64)
    count: int
    datetime_expires: datetime = Field(sa_type=UTCDateTime, index=True)
