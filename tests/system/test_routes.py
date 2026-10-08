"""The API system routes tests."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
async def test_health_route_200(async_client: AsyncClient) -> None:
    """Test the health route 200 for GET and HEAD."""
    response = await async_client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True
    response = await async_client.head("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b""
