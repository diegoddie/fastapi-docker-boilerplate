# Using the API

## API overview

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | public | Register a new user (group `member`) |
| `POST` | `/api/v1/auth/login/` | public | Log in (OAuth2 password form) and get a token pair |
| `POST` | `/api/v1/auth/refresh/` | public | Exchange a refresh token for a new pair (rotation) |
| `POST` | `/api/v1/auth/logout/` | public | Revoke the session of a refresh token |
| `POST` | `/api/v1/auth/google/` | public | Sign in with a Google ID token and get a token pair |
| `POST` | `/api/v1/auth/google/link/` | authenticated | Link a Google account to your user (password and verified email required) |
| `POST` | `/api/v1/auth/email/verification/` | authenticated | Email a new link to verify your address |
| `POST` | `/api/v1/auth/email/verify/` | public | Verify an address with the token of the link |
| `POST` | `/api/v1/auth/password/forgot/` | public | Email a link to choose a new password (always `202`) |
| `POST` | `/api/v1/auth/password/reset/` | public | Choose a new password with the token of the link; ends every session |
| `GET` / `PATCH` | `/api/v1/users/user/me/` | authenticated | Read or update your own profile |
| `GET` | `/api/v1/users/user/` | `can_view_user` | List users (paginated) |
| `GET` | `/api/v1/users/user/{id}/` | `can_view_user` | User detail |
| `PATCH` | `/api/v1/users/user/{id}/` | `can_edit_user` | Change names, groups, or (re)activate a user |
| `DELETE` | `/api/v1/users/user/{id}/` | `can_disable_user` | Disable a user and end all their sessions |
| `POST` | `/api/v1/todos/todo/` | `can_create_todo` | Create a todo (owned by you) |
| `GET` | `/api/v1/todos/todo/` | `can_view_todo` | List todos (paginated, with filters) |
| `GET` | `/api/v1/todos/todo/download/` | `can_view_todo` | Download the filtered todos as CSV |
| `GET` | `/api/v1/todos/todo/{id}/` | `can_view_todo` | Todo detail |
| `PATCH` | `/api/v1/todos/todo/{id}/` | `can_edit_todo` | Update a todo |
| `DELETE` | `/api/v1/todos/todo/{id}/` | `can_delete_todo` | Delete a todo (soft delete) |
| `POST` | `/api/v1/payments/checkout/` | authenticated | Start a Polar checkout for a product; returns the URL to send the user to <!-- copier:payments --> |
| `POST` | `/api/v1/payments/portal-session/` | authenticated | Open the Polar customer portal (invoices, payment method, cancellation) <!-- copier:payments --> |
| `GET` | `/api/v1/payments/subscription/` | authenticated | List your subscriptions <!-- copier:payments --> |
| `POST` | `/api/v1/payments/webhook/` | Polar (signed) | Receive Polar's webhooks <!-- copier:payments --> |
| `POST` | `/api/v1/todos/todo/{id}/subtask-suggestions/` | `can_suggest_todo_subtasks` | Ask Claude to split a todo into subtasks, ready to create <!-- copier:ai --> |
| `GET` / `HEAD` | `/api/health/`, `/api/ready/` | public | Liveness and readiness checks |

## Sign in with Google

The frontend shows Google's "Sign in with Google" button, receives an **ID token** from Google and sends it to `POST /api/v1/auth/google/` as `{"id_token": "..."}`. The backend verifies the token (Google's signature, issuer, audience, expiry) and answers with the same token pair as the password login:

- the first sign-in creates a `member` without a password, if Google verified the email; the address counts as verified when Google is authoritative for it (Gmail, or the domain of a Workspace account);
- if an account with the same email already exists, the sign-in answers `409` with `errorCode: ACCOUNT_EXISTS` and links nothing, because the email does not prove that the person owns that account (someone may have registered the address first, or the address may have changed hands). The user signs in with the password, and the frontend links the Google account with `POST /api/v1/auth/google/link/`, sending `{"id_token": "...", "password": "..."}`. The exception is an account whose address nobody ever verified: when Google is authoritative for the address, the person signing in owns it and takes the account over (its password, sessions and other linked accounts are removed);
- the next sign-ins find the user through the Google account id, even if the email changes.

To enable it:

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project and configure the consent screen (*Google Auth Platform*); while the app is in testing, add your account as a test user.
2. Create an OAuth client of type **Web application**, with `http://localhost:8000` and `http://localhost` as authorized JavaScript origins (no redirect URI is needed).
3. Set `FASTAPI_GOOGLE_CLIENT_ID` in `.env` and restart the backend. The client secret is not needed.
4. Open http://localhost:8000/api/v1/auth/google/test-page/: a local page (served only when the docs are) with the Google button, which shows the tokens returned by the backend.

Without a client id, Google sign-in answers `404` with `errorCode: GOOGLE_SIGN_IN_DISABLED`.

## Email verification and password reset

Registration sends a link to verify the address; "forgot password" sends a link to choose a new one. The links open two pages of your frontend, which send the token to the API:

| Page | Link | The page calls |
|---|---|---|
| Verify the email | `{FRONTEND_URL}/verify-email#token=...` | `POST /api/v1/auth/email/verify/` with `{"token": "..."}` |
| Reset the password | `{FRONTEND_URL}/reset-password#token=...` | `POST /api/v1/auth/password/reset/` with `{"token": "...", "password": "..."}` |

- The token is in the fragment (`#`), which browsers never send to servers. It works once and expires (24 hours to verify, 30 minutes to reset); a new link replaces the previous one.
- "Forgot password" answers `202` whether the email exists or not, so it does not reveal who is registered. A reset ends every session of the user.
- Unverified users can log in; `isEmailVerified` in `GET /api/v1/users/user/me/` tells the frontend to show a reminder, and `POST /api/v1/auth/email/verification/` sends a new link.
- Whoever proves an address first wins: a reset on an account nobody verified also removes the external accounts linked to it, so a person who registered someone else's address keeps no way in.
- Emails are sent after the response. Locally they are written to the logs (open the link from the terminal); remotely they go through SMTP (`FASTAPI_SMTP_*`), any provider works.

## Groups and permissions

Users belong to groups; each group grants a set of permissions (`GROUPS` in `app/users/constants.py`); each route declares the permission it needs.

| Group | Permissions |
|---|---|
| `admin` | every permission, including `can_manage_all_todos`: sees and changes everyone's todos |
| `member` (default on registration) | create, view, edit and delete **their own** todos |
| `viewer` | view their own todos (read-only) |
| `pro` | the paid features (`can_use_pro_features`), while a subscription is active; set by the payments, never by hand <!-- copier:payments --> |

A todo owned by someone else answers `404`, not `403`: the API never reveals that it exists.

Members and administrators can also ask for the subtasks of their todos (`can_suggest_todo_subtasks`). <!-- copier:ai -->

## Lists: filters, search, ordering

List endpoints take their filters as query parameters, declared once in a `FilterBase` subclass (see `TodoFilter` in `app/todos/schemas.py`) and reused by the CSV export:

| Parameter | Example | Meaning |
|---|---|---|
| `<field>` | `?status=done` | equal to |
| `<field>__in` | `?priority__in=high&priority__in=low` | one of |
| `<field>__gte` / `<field>__lte` | `?due_date__lte=2026-12-31` | greater / less than or equal to |
| `<field>__is_null` | `?due_date__is_null=true` | missing (or present, with `false`) |
| `search` | `?search=report` | case-insensitive match on the search fields (`%` and `_` match literally) |
| `order_by` | `?order_by=-priority,title` | sortable fields, `-` for descending; anything else is a `422` |
| `page`, `size` | `?page=2&size=20` | pagination (size up to 100) |
