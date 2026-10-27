"""The payments package constants."""

from app.payments.enums import SubscriptionStatus

# The paid features: the permissions of the pro group.
CAN_USE_PRO_FEATURES = "can_use_pro_features"

# Why: a subscription gives access while it is paid for, and while the provider
# retries a failed payment (past due); a subscription canceled at the end of
# the period stays active until then, and is canceled when the access ends.
ACCESS_STATUSES = frozenset(
    {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
        SubscriptionStatus.PAST_DUE,
    }
)

PAYMENTS_REQUESTS_RATE_LIMIT = "payments_requests"

# Why: the ids of the processed webhooks are kept long enough to recognize the
# provider's retries, which last days, then purged.
WEBHOOK_EVENT_RETENTION_DAYS = 30

# The pages of the frontend the customers come back to.
BILLING_PATH = "/billing"
# Why: Polar replaces {CHECKOUT_ID} with the id of the checkout.
CHECKOUT_SUCCESS_PATH = "/billing/success?checkout_id={CHECKOUT_ID}"
