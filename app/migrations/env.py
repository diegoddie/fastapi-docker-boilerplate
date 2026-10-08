"""The migrations configuration."""

from logging.config import fileConfig
from typing import Any, Literal

import alembic_postgresql_enum
from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import engine_from_config, pool, text
from sqlmodel import SQLModel

import app.core.models  # noqa: F401  # side-effect: register models and naming convention
from app.commons.types import UTCDateTime
from app.core.config import settings

# Why: every container runs the migrations on start; when several replicas start
# together, this Postgres advisory lock lets only one of them migrate at a time.
MIGRATIONS_LOCK = text("SELECT pg_advisory_lock(hashtext('alembic_migrations'))")
MIGRATIONS_UNLOCK = text("SELECT pg_advisory_unlock(hashtext('alembic_migrations'))")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

alembic_postgresql_enum.set_configuration(
    alembic_postgresql_enum.Config(add_type_ignore=True)
)

target_metadata = SQLModel.metadata


def get_database_url() -> str:
    """Return the database url."""
    return str(settings.DATABASE_URL)


def render_item(
    type_: str, obj: Any, autogen_context: AutogenContext
) -> str | Literal[False]:
    """
    Render ``UTCDateTime`` as the plain SQLAlchemy type it compiles to.

    Why: ``UTCDateTime`` adds no DDL of its own, so migrations must not import it.
    """
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return f"sa.{obj.impl!r}"
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
        literal_binds=True,
        render_item=render_item,
        target_metadata=target_metadata,
        url=get_database_url(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        {
            **config.get_section(config.config_ini_section, {}),
            "sqlalchemy.url": get_database_url(),
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Why: the lock is session-level, so it survives the commit that closes
        # this implicit transaction and lets Alembic open its own.
        connection.execute(MIGRATIONS_LOCK)
        connection.commit()
        try:
            context.configure(
                compare_type=True,
                connection=connection,
                render_item=render_item,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(MIGRATIONS_UNLOCK)
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
