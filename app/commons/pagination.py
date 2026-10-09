"""
Typed pagination wrapper around ``fastapi_pagination.ext.sqlmodel.apaginate``.

Why: the library stubs force a ``cast(Any, query)`` at every call site under mypy
strict; centralizing it here keeps ``Any`` out of routers and services.
"""

from typing import Any, cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlalchemy import Select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

type Query[T] = Select[tuple[T, ...]] | SelectOfScalar[T]


async def paginate[T](session: AsyncSession, query: Query[T]) -> Page[T]:
    """Paginate a query into ``Page[T]`` using the request's page and size."""
    return cast(Page[T], await apaginate(session, cast(Any, query)))
