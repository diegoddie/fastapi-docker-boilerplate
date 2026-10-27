"""
The payments package: subscriptions sold with Polar.

A user subscribes through a checkout of the provider; the provider's webhooks
keep a copy of the subscription in the ``subscription`` table, the source of
truth for access: an active subscription puts the user in the ``pro`` group,
whose permissions are the paid features. ``PaymentProvider`` keeps the
provider swappable. Without the Polar token and webhook secret the payment
routes answer 404.
"""
