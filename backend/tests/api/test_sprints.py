"""Tests for sprint routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.db.models.sprint import SprintItemStatus, SprintStatus
from app.main import app


class MockSprintItem:
    """Mock sprint item."""

    def __init__(
        self,
        id=None,
        sprint_id=None,
        title="Sample item",
        description=None,
        status=SprintItemStatus.TODO,
        priority=2,
        estimate_points=None,
    ):
        self.id = id or uuid4()
        self.sprint_id = sprint_id or uuid4()
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.estimate_points = estimate_points
        self.created_at = datetime.now(UTC)
        self.updated_at = None


class MockSprint:
    """Mock sprint."""

    def __init__(
        self,
        id=None,
        name="Sprint Alpha",
        goal=None,
        status=SprintStatus.PLANNED,
        start_date=None,
        end_date=None,
        items=None,
    ):
        self.id = id or uuid4()
        self.name = name
        self.goal = goal
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.items = items or []
        self.created_at = datetime.now(UTC)
        self.updated_at = None


@pytest.fixture
def mock_sprint_item() -> MockSprintItem:
    """Create a mock sprint item."""
    return MockSprintItem()


@pytest.fixture
def mock_sprint(mock_sprint_item: MockSprintItem) -> MockSprint:
    """Create a mock sprint."""
    mock_sprint_item.sprint_id = uuid4()
    return MockSprint(id=mock_sprint_item.sprint_id, items=[mock_sprint_item])


@pytest.fixture
def mock_sprint_service(mock_sprint: MockSprint, mock_sprint_item: MockSprintItem) -> MagicMock:
    """Create a mock sprint service."""
    service = MagicMock()
    service.get_with_items = AsyncMock(return_value=mock_sprint)
    service.create = AsyncMock(return_value=mock_sprint)
    service.update = AsyncMock(return_value=mock_sprint)
    service.delete = AsyncMock(return_value=mock_sprint)
    service.list_items = AsyncMock(return_value=[mock_sprint_item])
    service.create_item = AsyncMock(return_value=mock_sprint_item)
    service.update_item = AsyncMock(return_value=mock_sprint_item)
    service.delete_item = AsyncMock(return_value=mock_sprint_item)
    return service


@pytest.fixture
async def client_with_mock_service(
    mock_sprint_service: MagicMock,
    mock_db_session,
) -> AsyncClient:
    """Client with mocked sprint service."""
    from httpx import ASGITransport

    from app.api.deps import get_sprint_service
    from app.db.session import get_db_session

    app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_sprint_success(client_with_mock_service: AsyncClient):
    """Test sprint creation."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/sprints",
        json={"name": "Sprint Alpha", "goal": "Ship sprint board"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Sprint Alpha"


@pytest.mark.anyio
async def test_get_sprint_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
):
    """Test sprint retrieval."""
    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mock_sprint.id)
    assert data["items"]


@pytest.mark.anyio
async def test_get_sprint_not_found(
    client_with_mock_service: AsyncClient,
    mock_sprint_service: MagicMock,
):
    """Test sprint retrieval when not found."""
    from app.core.exceptions import NotFoundError

    mock_sprint_service.get_with_items = AsyncMock(
        side_effect=NotFoundError(message="Sprint not found")
    )
    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/sprints/{uuid4()}",
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_sprint_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
):
    """Test sprint update."""
    response = await client_with_mock_service.patch(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}",
        json={"status": "active"},
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_delete_sprint_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
):
    """Test sprint deletion."""
    response = await client_with_mock_service.delete(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}",
    )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_create_sprint_item_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
):
    """Test sprint item creation."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items",
        json={"title": "Wire sprint view", "priority": 1},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_update_sprint_item_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
    mock_sprint_item: MockSprintItem,
):
    """Test sprint item update."""
    response = await client_with_mock_service.patch(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items/{mock_sprint_item.id}",
        json={"status": "done"},
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_delete_sprint_item_success(
    client_with_mock_service: AsyncClient,
    mock_sprint: MockSprint,
    mock_sprint_item: MockSprintItem,
):
    """Test sprint item deletion."""
    response = await client_with_mock_service.delete(
        f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items/{mock_sprint_item.id}",
    )
    assert response.status_code == 204
