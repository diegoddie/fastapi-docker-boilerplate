"""The commons package exports tests."""

import csv
from io import StringIO

import pytest
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.commons.exports import csv_chunks
from app.todos.models import Todo
from app.todos.schemas import TodoCSVSchema
from app.users.models import User
from tests.factories.todos import TodoFactory


@pytest.mark.asyncio(loop_scope="function")
async def test_csv_chunks_batches(
    async_db_session: AsyncSession,
    todo_factory: type[TodoFactory],
    bob_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the header comes first, then the rows in batches read one at a time."""
    monkeypatch.setattr("app.commons.exports.CSV_BATCH_SIZE", 2)
    todos = await todo_factory.create_batch_async(5, owner_id=bob_member_user.id)
    query = select(Todo).order_by(col(Todo.datetime_created), col(Todo.id))
    chunks = [
        chunk async for chunk in csv_chunks(async_db_session, query, TodoCSVSchema)
    ]
    assert [len(list(csv.reader(StringIO(chunk)))) for chunk in chunks] == [
        1,
        2,
        2,
        1,
    ]
    rows = list(csv.DictReader(StringIO("".join(chunks))))
    assert [row["Title"] for row in rows] == [todo.title for todo in todos]
