"""The base factory module."""

from typing import TypeVar

from polyfactory import Ignore
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

T = TypeVar("T")


class BaseFactory(SQLAlchemyFactory[T]):
    """Base factory for table models."""

    __is_base_factory__ = True
    # Why: related rows are passed by foreign key (``user_id=bob.id``), never
    # invented by the factory.
    __set_relationships__ = False

    # Why: let the model defaults win, so ids are uuid7 and timestamps are real.
    id = Ignore()
    datetime_created = Ignore()
    datetime_updated = Ignore()
