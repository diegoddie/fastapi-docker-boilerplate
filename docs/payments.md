# Subscriptions with Polar

With `FASTAPI_POLAR_ACCESS_TOKEN` and `FASTAPI_POLAR_WEBHOOK_SECRET` set, users subscribe through [Polar](https://polar.sh), which handles the payment, the invoices and the taxes as merchant of record. Without them, the payment routes answer `404` (`PAYMENTS_DISABLED`).

1. The frontend calls `POST /api/v1/payments/checkout/` with a product id listed in `FASTAPI_POLAR_PRODUCT_IDS`, and sends the user to the returned URL. The user must have verified their email; the Polar customer is created with the user id as its external id.
2. Polar calls `POST /api/v1/payments/webhook/` at every change of the subscription. The signature is verified, an event that arrives twice is applied once, and an event older than the saved state is ignored, so the order of arrival does not matter.
3. The `subscription` table is the source of truth: while a subscription is active (or on trial, or a failed payment is being retried), the user is in the `pro` group, and gets its permissions. A subscription canceled at the end of the period keeps access until then.
4. `POST /api/v1/payments/portal-session/` opens the Polar customer portal, where the user changes the payment method, downloads the invoices or cancels.

Put a paid feature behind `require_any_permissions([CAN_USE_PRO_FEATURES])`, or add your own permissions to `GROUPS[Group.PRO]` (`app/users/constants.py`).

To try it: create an organization on the [Polar sandbox](https://sandbox.polar.sh) with a recurring product, an access token with the `checkouts:write` and `customer_sessions:write` scopes, and a webhook pointing to `/api/v1/payments/webhook/` for the `subscription.*` events (locally, through a tunnel); its secret goes in `FASTAPI_POLAR_WEBHOOK_SECRET`. Tests never call Polar: they sign webhooks the way Polar does.
