# 0018. Subscriptions with Polar, as an option

- Status: Accepted
- Date: 2026-10-27

## Context

Many products sell a subscription: a checkout, a page to manage it, and
access that follows the payments. The hard parts are in the webhooks: they
arrive late, twice or out of order, they must be authentic, and a lost one
must not leave a user with access they did not pay for (or without the access
they paid for).

## Decision

- Generating a project asks `payments`: `none` (the default) or `polar`. The
  module lives in `app/payments/`; without the Polar token and webhook secret
  its routes answer `404` (`PAYMENTS_DISABLED`).
- Polar is the merchant of record: it handles the payment, the invoices, the
  taxes and the customer portal. It sits behind the `PaymentProvider` protocol
  (checkout, portal session, verified webhook event), so another provider can
  replace it without touching the services.
- The Polar customer is created by the checkout with the user id as its
  external id: webhooks name the user without a mapping table. A checkout
  needs a verified email and a product listed in `POLAR_PRODUCT_IDS`.
- Webhooks are verified by the SDK (Standard Webhooks), but only the fields
  the app uses are read, so a change in the rest of Polar's payloads cannot
  break them. Each one is applied in one transaction: its `webhook-id` is
  recorded (a retry finds it and stops), the subscription snapshot is upserted
  only if it is newer than the saved one by Polar's modification time (so the
  order of arrival does not matter), and the `pro` group is recomputed.
- The `subscription` table is the source of truth; the `pro` group in
  `user.groups` is its copy, so permissions keep being computed from the groups
  alone. Access lasts while the subscription is active, on trial, or past due
  (Polar retries the payment and revokes the subscription if it fails); a
  subscription canceled at the end of the period stays active until then.
  Administrators cannot set the `pro` group by hand.
- The tables live in the `payments` migration branch (ADR 0014); the records
  of webhooks are purged after 30 days.

## Consequences

- Access follows the webhooks: if they stop (a wrong secret, an endpoint
  down), access stops changing; Polar retries for days, and its dashboard
  shows the failed deliveries.
- A user can hold one subscription at a time through the API.
- The pages `/billing` and `/billing/success` of the frontend receive the
  customers back from Polar.

## Alternatives considered

- **Stripe**: the most common, but the app would have to handle taxes and
  invoices itself, or add Stripe Tax and Billing; Polar does it as merchant of
  record. `PaymentProvider` leaves room for it.
- **Lemon Squeezy**: also a merchant of record, but with a less active API and
  SDK.
- **Asking Polar for the state at every request**: always fresh, but slow, and
  every request would depend on Polar being up.
- **Deserializing the full payloads with the SDK's models**: typed, but any
  change Polar makes to an unrelated field would break the webhooks.
