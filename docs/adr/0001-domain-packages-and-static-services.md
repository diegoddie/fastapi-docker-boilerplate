# 0001. Domain packages with thin routers and static-method services

- Status: Accepted
- Date: 2026-10-08

## Context

The boilerplate must be easy to extend with new features and easy to read for
someone new to it. FastAPI does not impose a structure; common choices are
"one folder per technical layer" (`models/`, `routes/`, `schemas/`) or "one
folder per business domain".

## Decision

- One package per business domain (`app/users`, `app/todos`), each with the
  same files: `constants.py`, `enums.py`, `models.py`, `schemas.py`,
  `services.py`, `router.py`.
- **Routers** only describe the HTTP contract and call one service method.
- **Services** are classes of `@staticmethod`s that receive the session, the
  current user and their collaborators as arguments, and own the transaction.
- Interfaces (`Protocol`) only where an implementation must be replaceable:
  password hashing, access tokens, external identity providers.
- `app/todos` is kept as the reference implementation to copy.

## Consequences

- A feature lives in one folder; adding one means copying `todos` (the
  `new-domain-app` skill and the README describe the steps).
- Services are plain functions grouped by domain: easy to call from routes,
  commands or tests, with no container to configure.
- The ORM models are used directly by services: there is no repository layer.
  Swapping SQLModel would be a larger change, a deliberate trade-off for less code.

## Alternatives considered

- **Layer folders** (`models/`, `routes/`): a feature is spread over many folders.
- **Full hexagonal architecture** (domain entities separate from ORM models,
  repositories, use cases): more isolation, but several extra files per feature
  and against the SQLModel idea of sharing fields between tables and schemas.
