---
name: new-domain-app
description: Add a new domain package (a resource with its model, migration, API routes, permissions and tests) to this FastAPI project, mirroring the app/todos reference implementation. Use when asked to add a feature, an entity, a resource or a CRUD API.
---

# Add a domain package

`app/todos/` and `tests/todos/` are the reference: open the matching todos file
before writing each new one, and keep the same structure, names and style.
Below, `<domain>` is the plural package name (`invoices`), `<resource>` the
singular (`invoice`), `<Model>` the class (`Invoice`).

## 1. Clarify

Ask only what the request leaves open: the fields and their types, who may do
what (which groups get which permissions), whether users see only their own
records (like todos) or all of them, which list filters and sort fields are
needed, whether a CSV export is useful.

## 2. Application code

1. `app/<domain>/__init__.py` with a docstring.
2. `constants.py`: field lengths and permissions
   `CAN_CREATE_<RESOURCE>`, `CAN_VIEW_...`, `CAN_EDIT_...`, `CAN_DELETE_...`
   (+ `CAN_MANAGE_ALL_<DOMAIN>` if records belong to their creator).
3. `enums.py`: `StrEnum`s with lowercase values.
4. `models.py`: `Base<Model>(SQLModel)` with the shared fields, then
   `<Model>(Base<Model>, BaseSQLModel, table=True)` with
   `id: UUID = Field(default_factory=uuid7, primary_key=True)`, foreign keys
   (`ondelete`, `index=True`), enums via `sa_column=Column(pg_enum(...), nullable=False)`.
   **Unique fields and soft delete**: a deleted row stays in the table, so with
   `unique=True` its value stays taken and creating it again is a `409`. When a
   value must be reusable after a delete (a slug, a code), make it unique among
   the active rows only, with a partial index instead of `unique=True`:

   ```python
   __table_args__ = (
       Index(
           "uq_<resource>_<field>_active",
           "<field>",
           unique=True,
           postgresql_where=text("datetime_disabled IS NULL"),
       ),
   )
   ```

   A clash is still a `UniqueViolation`, so the API still answers `409`. Ask
   which behavior is wanted; users are the exception on purpose (a disabled
   user can be reactivated, so the email stays taken).
5. `schemas.py`: `<Model>PublicSchemaCreate`, `<Model>PublicSchemaUpdate` (all
   optional, `reject_null` for non-nullable columns), `<Model>PublicSchemaResponse`,
   `<Model>CSVSchema` (field titles = CSV headers), `<Model>Filter(FilterBase)`.
6. `services.py`: `<Model>Service` with static methods `get_where_clause(user)`,
   `get_by_id`, `list_query`, `create`, `update`, `delete` (soft).
7. `router.py`: `create_<resource>_route`, `list_<domain>_route`,
   `download_<domain>_route`, `detail_<resource>_route`, `update_<resource>_route`,
   `delete_<resource>_route`, paths `/<resource>/` and `/<resource>/{<resource>_id:uuid}/`.
8. Register the model in `app/core/models.py` and the router in
   `app/api/v1/router.py` (`prefix="/<domains-in-kebab-case>"`, `tags=["<domain>"]`).
9. Grant the permissions to the groups in `GROUPS` (`app/users/constants.py`).

## 3. Migration

Run `just migrate-forward`, then `just forge "add <resource> table"`, and read
the generated file: enum types, foreign keys with `ondelete`, constraint names,
`postgresql_where` on partial indexes.
Check that `just migrate-backward -1` and `just migrate-forward` both work.

## 4. Tests

1. `tests/factories/<domain>.py`: `<Model>Factory(BaseFactory[<Model>])` with
   `@classmethod` generators using `cls.__faker__`.
2. `tests/pytest_plugins/<domain>.py`: the factory fixture (depending on
   `seed_factories`) and named records with fixed uuid7 ids, owned by the
   personas (Alice admin, Bob member, Carol viewer, Dave disabled); register the
   plugin in `tests/conftest.py`.
3. `tests/<domain>/test_router.py`: parametrized `test_route_401` and
   `test_route_403`; then one test per route and status code
   (`test_create_<resource>_route_201`, `..._422`, `test_detail_<resource>_route_404_other_owner`...),
   filters and ordering, the CSV export. URLs written in full; whole responses
   with `snapshot()`; after writes, `expunge_all()` and read the row back.
4. Update `tests/users/test_models.py` if the groups' permissions changed.

## 5. Finish

`just fix`, then `just test` (100% coverage, `alembic check` included). Update
the README API overview and the groups table. Open a PR from `feat/<domain>`.
