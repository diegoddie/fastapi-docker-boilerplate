"""The commons package models."""

from sqlmodel import SQLModel

# Why: constraint and index names must be deterministic and identical whether the
# schema is built by the Alembic migrations or by `create_all` in the tests, so the
# convention is set here, in the module every table model depends on.
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
