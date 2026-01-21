"""Integration tests for sprint API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.main import app
from app.api.deps import get_db_session


@pytest.fixture
async def client_with_db(db_session):
    """Client with real database session."""
    app.dependency_overrides[get_db_session] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_sprint_integration(client_with_db: AsyncClient, db_session):
    """Test creating a sprint via API with real database."""
    # 1. Create Sprint
    response = await client_with_db.post(
        f"{settings.API_V1_STR}/sprints",
        json={
            "name": "Integration API Sprint",
            "goal": "Test API integration",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Integration API Sprint"
    assert data["status"] == "planned"
    assert "id" in data
