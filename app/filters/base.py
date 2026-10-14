"""The filters package base: declarative filtering, search and sorting."""

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel, field_validator
from pydantic.alias_generators import to_snake
from sqlalchemy import ColumnElement
from sqlmodel import SQLModel, col, or_
from sqlmodel.sql.expression import SelectOfScalar

from app.filters.constants import LIKE_ESCAPE, LOOKUP_SEPARATOR

OPERATORS: dict[str, Callable[[Any, Any], ColumnElement[bool]]] = {
    "": lambda column, value: column == value,
    "in": lambda column, value: column.in_(value),
    "gte": lambda column, value: column >= value,
    "lte": lambda column, value: column <= value,
    "is_null": lambda column, value: column.is_(None) if value else column.is_not(None),
}


def split_lookup(name: str) -> tuple[str, str]:
    """Split a filter name like ``due_date__lte`` into column and operator."""
    column, _, operator = name.partition(LOOKUP_SEPARATOR)
    return column, operator


def escape_like(value: str) -> str:
    """Escape the LIKE wildcards in user input, so they match literally."""
    return (
        value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


class FilterBase(BaseModel):
    """
    The query parameters of a list endpoint: filters, search and ordering.

    Subclasses declare the model, the searchable columns, the sortable fields (as
    the API names them) and one field per filter, named ``<column>`` for equality
    or ``<column>__<operator>`` (``in``, ``gte``, ``lte``, ``is_null``).
    """

    model: ClassVar[type[SQLModel]]
    search_fields: ClassVar[tuple[str, ...]] = ()
    sortable_fields: ClassVar[tuple[str, ...]] = ()
    default_order_by: ClassVar[str] = ""

    search: str | None = None
    order_by: str | None = None

    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, value: str) -> str:
        """Accept only the sortable fields, each optionally prefixed by ``-``."""
        for part in value.split(","):
            name = part.strip().removeprefix("-")
            if name not in cls.sortable_fields:
                allowed = ", ".join(cls.sortable_fields)
                raise ValueError(f"Cannot order by {name!r}, allowed: {allowed}")
        return value

    def apply[T: SQLModel](self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Return the query filtered, searched and ordered."""
        for name in type(self).model_fields:
            value = getattr(self, name)
            if name in FilterBase.model_fields or value is None:
                continue
            column, operator = split_lookup(name)
            query = query.where(OPERATORS[operator](self._column(column), value))
        if self.search and self.search_fields:
            pattern = f"%{escape_like(self.search)}%"
            query = query.where(
                or_(
                    *(
                        self._column(field).ilike(pattern, escape=LIKE_ESCAPE)
                        for field in self.search_fields
                    )
                )
            )
        order_by = (self.order_by or self.default_order_by).split(",")
        for name in filter(None, map(str.strip, order_by)):
            column = self._column(to_snake(name.removeprefix("-")))
            query = query.order_by(
                column.desc() if name.startswith("-") else column.asc()
            )
        return query

    def _column(self, name: str) -> Any:
        """Return a column of the model."""
        return col(getattr(self.model, name))
