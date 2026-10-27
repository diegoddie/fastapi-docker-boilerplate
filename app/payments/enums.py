"""The payments package enums."""

from enum import StrEnum


class SubscriptionStatus(StrEnum):
    """The status of a subscription, as Polar reports it."""

    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"
