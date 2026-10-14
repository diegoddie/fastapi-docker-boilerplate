"""The todos package router tests."""

import csv
from datetime import date
from io import StringIO
from typing import Any

import pytest
from dirty_equals import IsDatetime, IsUUID
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel.ext.asyncio.session import AsyncSession

from app.todos.enums import TodoPriority, TodoStatus
from app.todos.models import Todo
from app.users.models import User
from tests.factories.todos import TodoFactory
from tests.utils import AsyncClient

DUMMY_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/v1/todos/todo/"),
        ("get", "/api/v1/todos/todo/"),
        ("get", "/api/v1/todos/todo/download/"),
        ("get", f"/api/v1/todos/todo/{DUMMY_UUID}/"),
        ("patch", f"/api/v1/todos/todo/{DUMMY_UUID}/"),
        ("delete", f"/api/v1/todos/todo/{DUMMY_UUID}/"),
    ],
    ids=[
        "create_todo",
        "list_todos",
        "download_todos",
        "detail_todo",
        "update_todo",
        "delete_todo",
    ],
)
async def test_route_401(async_client: AsyncClient, method: str, url: str) -> None:
    """Test that unauthenticated requests return 401."""
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/v1/todos/todo/"),
        ("patch", f"/api/v1/todos/todo/{DUMMY_UUID}/"),
        ("delete", f"/api/v1/todos/todo/{DUMMY_UUID}/"),
    ],
    ids=["create_todo", "update_todo", "delete_todo"],
)
async def test_route_403(
    async_client: AsyncClient, carol_viewer_user: User, method: str, url: str
) -> None:
    """Test that viewers can read todos but not write them."""
    async_client.login(carol_viewer_user)
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["errorCode"] == "FORBIDDEN"


@pytest.mark.asyncio(loop_scope="function")
async def test_create_todo_route_201(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the create todo route 201: the todo belongs to its creator."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/todos/todo/",
        json={"title": "  Call mom  ", "priority": "high", "dueDate": "2026-11-01"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data == snapshot(
        {
            "title": "Call mom",
            "description": "",
            "status": "todo",
            "priority": "high",
            "dueDate": "2026-11-01",
            "id": IsUUID,
            "ownerId": "0194f8a0-2000-7000-8000-000000000002",
            "datetimeCreated": IsDatetime(iso_string=True),
            "datetimeUpdated": IsDatetime(iso_string=True),
        }
    )
    async_db_session.expunge_all()
    todo = await async_db_session.get(Todo, data["id"])
    assert todo is not None
    assert (todo.owner_id, todo.status, todo.priority) == (
        bob_member_user.id,
        TodoStatus.TODO,
        TodoPriority.HIGH,
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_create_todo_route_422(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the create todo route 422 for a blank title and an unknown status."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/todos/todo/", json={"title": "   ", "status": "someday"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["errors"] == snapshot(
        [
            {
                "field": "body.title",
                "message": "String should have at least 1 character",
                "type": "string_too_short",
            },
            {
                "field": "body.status",
                "message": "Input should be 'todo', 'in_progress' or 'done'",
                "type": "enum",
            },
        ]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_200(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_milk_todo: Todo,
    bob_report_todo: Todo,
    bob_flight_todo: Todo,
    alice_review_todo: Todo,
) -> None:
    """Test the list todos route 200: own todos only, newest first."""
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/todos/todo/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [todo["title"] for todo in data["items"]] == snapshot(
        ["Book the flight", "Write the quarterly report", "Buy milk"]
    )
    assert (data["total"], data["page"], data["size"]) == (3, 1, 50)


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_200_admin(
    async_client: AsyncClient,
    alice_admin_user: User,
    bob_milk_todo: Todo,
    alice_review_todo: Todo,
) -> None:
    """Test the list todos route 200: administrators see everyone's todos."""
    async_client.login(alice_admin_user)
    response = await async_client.get("/api/v1/todos/todo/")
    assert response.status_code == status.HTTP_200_OK
    assert [todo["title"] for todo in response.json()["items"]] == snapshot(
        ["Review pull requests", "Buy milk"]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_200_viewer(
    async_client: AsyncClient, carol_viewer_user: User, bob_milk_todo: Todo
) -> None:
    """Test the list todos route 200: viewers see only their own (none here)."""
    async_client.login(carol_viewer_user)
    response = await async_client.get("/api/v1/todos/todo/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == []


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("params", "titles"),
    [
        ({"status": "done"}, ["Book the flight"]),
        ({"priority__in": ["high", "low"]}, ["Book the flight", "Buy milk"]),
        ({"due_date__gte": "2026-10-16"}, ["Buy milk"]),
        ({"due_date__lte": "2026-10-16"}, ["Write the quarterly report"]),
        ({"due_date__is_null": True}, ["Book the flight"]),
        (
            {"due_date__is_null": False},
            ["Write the quarterly report", "Buy milk"],
        ),
        ({"search": "QUARTERLY"}, ["Write the quarterly report"]),
        ({"search": "q3"}, ["Write the quarterly report"]),
        (
            {"order_by": "title"},
            ["Book the flight", "Buy milk", "Write the quarterly report"],
        ),
        (
            {"order_by": "-priority,title"},
            ["Buy milk", "Write the quarterly report", "Book the flight"],
        ),
        (
            {"order_by": "dueDate"},
            ["Write the quarterly report", "Buy milk", "Book the flight"],
        ),
    ],
    ids=[
        "status",
        "priority_in",
        "due_date_gte",
        "due_date_lte",
        "without_due_date",
        "with_due_date",
        "search_title",
        "search_description",
        "order_by_title",
        "order_by_priority_desc",
        "order_by_due_date_nulls_last",
    ],
)
async def test_list_todos_route_200_filters(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_milk_todo: Todo,
    bob_report_todo: Todo,
    bob_flight_todo: Todo,
    params: dict[str, Any],
    titles: list[str],
) -> None:
    """Test the list todos route 200 with filters, search and ordering."""
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/todos/todo/", params=params)
    assert response.status_code == status.HTTP_200_OK
    assert [todo["title"] for todo in response.json()["items"]] == titles


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_200_search_wildcards(
    async_client: AsyncClient,
    todo_factory: type[TodoFactory],
    bob_member_user: User,
    bob_milk_todo: Todo,
) -> None:
    """Test the search matches % and _ literally, not as wildcards."""
    await todo_factory.create_async(
        owner_id=bob_member_user.id, title="Reach 100% coverage", description=""
    )
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/todos/todo/", params={"search": "%"})
    assert [todo["title"] for todo in response.json()["items"]] == [
        "Reach 100% coverage"
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_200_pagination(
    async_client: AsyncClient,
    todo_factory: type[TodoFactory],
    bob_member_user: User,
) -> None:
    """Test the list todos route 200 is paginated."""
    await todo_factory.create_batch_async(5, owner_id=bob_member_user.id)
    async_client.login(bob_member_user)
    response = await async_client.get(
        "/api/v1/todos/todo/", params={"size": 2, "page": 3}
    )
    data = response.json()
    assert len(data["items"]) == 1
    assert (data["total"], data["page"], data["size"], data["pages"]) == (5, 3, 2, 3)


@pytest.mark.asyncio(loop_scope="function")
async def test_list_todos_route_422(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the list todos route 422 for a field that cannot be sorted."""
    async_client.login(bob_member_user)
    response = await async_client.get(
        "/api/v1/todos/todo/", params={"order_by": "title,ownerId"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["errors"] == snapshot(
        [
            {
                "field": "query.order_by",
                "message": (
                    "Value error, Cannot order by 'ownerId', "
                    "allowed: title, priority, dueDate, datetimeCreated"
                ),
                "type": "value_error",
            }
        ]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_detail_todo_route_200(
    async_client: AsyncClient, bob_member_user: User, bob_report_todo: Todo
) -> None:
    """Test the detail todo route 200."""
    async_client.login(bob_member_user)
    response = await async_client.get(f"/api/v1/todos/todo/{bob_report_todo.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == snapshot(
        {
            "title": "Write the quarterly report",
            "description": "Numbers for Q3",
            "status": "in_progress",
            "priority": "medium",
            "dueDate": "2026-10-15",
            "id": "0194f8a0-2000-7000-8000-000000000102",
            "ownerId": "0194f8a0-2000-7000-8000-000000000002",
            "datetimeCreated": IsDatetime(iso_string=True),
            "datetimeUpdated": IsDatetime(iso_string=True),
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_detail_todo_route_200_admin(
    async_client: AsyncClient, alice_admin_user: User, bob_milk_todo: Todo
) -> None:
    """Test the detail todo route 200: administrators reach everyone's todos."""
    async_client.login(alice_admin_user)
    response = await async_client.get(f"/api/v1/todos/todo/{bob_milk_todo.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Buy milk"


@pytest.mark.asyncio(loop_scope="function")
async def test_detail_todo_route_404_other_owner(
    async_client: AsyncClient, bob_member_user: User, alice_review_todo: Todo
) -> None:
    """Test the detail todo route 404: someone else's todo does not exist for you."""
    async_client.login(bob_member_user)
    response = await async_client.get(f"/api/v1/todos/todo/{alice_review_todo.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == snapshot(
        {
            "detail": {
                "message": (
                    "Todo with id 0194f8a0-2000-7000-8000-000000000104 not found"
                ),
                "errorCode": "TODO_NOT_FOUND",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_update_todo_route_204(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    bob_milk_todo: Todo,
) -> None:
    """Test the update todo route 204 changes only the fields sent."""
    # Why: the API shares the test session, so this object is updated in place.
    datetime_updated = bob_milk_todo.datetime_updated
    async_client.login(bob_member_user)
    response = await async_client.patch(
        f"/api/v1/todos/todo/{bob_milk_todo.id}/",
        json={"status": "done", "description": "Two liters", "dueDate": None},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    async_db_session.expunge_all()
    todo = await async_db_session.get(Todo, bob_milk_todo.id)
    assert todo is not None
    assert (todo.title, todo.description, todo.status, todo.due_date) == (
        "Buy milk",
        "Two liters",
        TodoStatus.DONE,
        None,
    )
    assert todo.priority == TodoPriority.HIGH
    assert todo.datetime_updated > datetime_updated


@pytest.mark.asyncio(loop_scope="function")
async def test_update_todo_route_404_other_owner(
    async_client: AsyncClient, bob_member_user: User, alice_review_todo: Todo
) -> None:
    """Test the update todo route 404 for someone else's todo."""
    async_client.login(bob_member_user)
    response = await async_client.patch(
        f"/api/v1/todos/todo/{alice_review_todo.id}/", json={"status": "done"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"]["errorCode"] == "TODO_NOT_FOUND"


@pytest.mark.asyncio(loop_scope="function")
async def test_update_todo_route_422(
    async_client: AsyncClient, bob_member_user: User, bob_milk_todo: Todo
) -> None:
    """Test the update todo route 422 for an explicit null title."""
    async_client.login(bob_member_user)
    response = await async_client.patch(
        f"/api/v1/todos/todo/{bob_milk_todo.id}/", json={"title": None}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["errors"] == snapshot(
        [
            {
                "field": "body.title",
                "message": "Value error, Field cannot be null",
                "type": "value_error",
            }
        ]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_todo_route_204(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    bob_milk_todo: Todo,
) -> None:
    """Test the delete todo route 204: the todo is kept, but gone for the API."""
    async_client.login(bob_member_user)
    response = await async_client.delete(f"/api/v1/todos/todo/{bob_milk_todo.id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    todo = await async_db_session.get(Todo, bob_milk_todo.id)
    assert todo is not None
    assert todo.datetime_disabled == IsDatetime
    response = await async_client.get(f"/api/v1/todos/todo/{bob_milk_todo.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = await async_client.get("/api/v1/todos/todo/")
    assert response.json()["items"] == []


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_todo_route_404_other_owner(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    alice_review_todo: Todo,
) -> None:
    """Test the delete todo route 404 for someone else's todo, left untouched."""
    async_client.login(bob_member_user)
    response = await async_client.delete(f"/api/v1/todos/todo/{alice_review_todo.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    async_db_session.expunge_all()
    todo = await async_db_session.get(Todo, alice_review_todo.id)
    assert todo is not None
    assert todo.is_active is True


@pytest.mark.asyncio(loop_scope="function")
async def test_download_todos_route_200(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_milk_todo: Todo,
    bob_report_todo: Todo,
    bob_flight_todo: Todo,
    alice_review_todo: Todo,
) -> None:
    """Test the download todos route 200: a CSV of the filtered todos."""
    async_client.login(bob_member_user)
    response = await async_client.get(
        "/api/v1/todos/todo/download/", params={"status": "todo"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="todos.csv"'
    )
    assert list(csv.DictReader(StringIO(response.text))) == snapshot(
        [
            {
                "Title": "Buy milk",
                "Description": "",
                "Status": "todo",
                "Priority": "high",
                "Due date": "2026-10-20",
                "Created at": IsDatetime(iso_string=True),
            }
        ]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_download_todos_route_200_formulas(
    async_client: AsyncClient,
    todo_factory: type[TodoFactory],
    bob_member_user: User,
) -> None:
    """Test the export neutralizes spreadsheet formulas (CSV injection)."""
    await todo_factory.create_async(
        owner_id=bob_member_user.id,
        title='=HYPERLINK("https://evil.example", "Click")',
        description="+1 for the team",
        due_date=date(2026, 10, 20),
    )
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/todos/todo/download/")
    (row,) = csv.DictReader(StringIO(response.text))
    assert row["Title"] == '\'=HYPERLINK("https://evil.example", "Click")'
    assert row["Description"] == "'+1 for the team"
    assert row["Due date"] == "2026-10-20"
