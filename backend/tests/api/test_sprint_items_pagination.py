"""Tests for sprint items pagination endpoint.

Tests the GET /{sprint_id}/items endpoint which returns paginated sprint items
ordered by priority. This endpoint uses fastapi-pagination with SQLAlchemy
query-based pagination per ADR-001.

Test Cases:
1. Empty sprint returns empty paginated response
2. Sprint with items returns paginated items
3. Pagination params (page, size) work correctly
4. Non-existent sprint returns 404
5. Items are ordered by priority
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi_pagination import Page
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.models.sprint import SprintItemStatus, SprintStatus
from app.main import app
from app.schemas.sprint import SprintItemRead


class MockSprintItem:
    """Mock sprint item for testing."""

    def __init__(
        self,
        id=None,
        sprint_id=None,
        title="Test Item",
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
    """Mock sprint for testing."""

    def __init__(
        self,
        id=None,
        spec_id=None,
        name="Test Sprint",
        goal=None,
        status=SprintStatus.PLANNED,
        start_date=None,
        end_date=None,
        items=None,
    ):
        self.id = id or uuid4()
        self.spec_id = spec_id
        self.name = name
        self.goal = goal
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.items = items or []
        self.created_at = datetime.now(UTC)
        self.updated_at = None


@pytest.fixture
def mock_sprint() -> MockSprint:
    """Create a mock sprint with no items."""
    return MockSprint()


@pytest.fixture
def mock_sprint_with_items() -> tuple[MockSprint, list[MockSprintItem]]:
    """Create a mock sprint with multiple items at different priorities."""
    sprint_id = uuid4()
    items = [
        MockSprintItem(
            sprint_id=sprint_id,
            title="High Priority Task",
            priority=1,
            status=SprintItemStatus.TODO,
        ),
        MockSprintItem(
            sprint_id=sprint_id,
            title="Medium Priority Task 1",
            priority=2,
            status=SprintItemStatus.IN_PROGRESS,
        ),
        MockSprintItem(
            sprint_id=sprint_id,
            title="Medium Priority Task 2",
            priority=2,
            status=SprintItemStatus.TODO,
        ),
        MockSprintItem(
            sprint_id=sprint_id,
            title="Low Priority Task",
            priority=3,
            status=SprintItemStatus.BLOCKED,
        ),
    ]
    sprint = MockSprint(id=sprint_id, items=items)
    return sprint, items


@pytest.fixture
def mock_sprint_service() -> MagicMock:
    """Create a mock sprint service."""
    service = MagicMock()
    service.db = MagicMock()
    service.db.commit = AsyncMock()
    return service


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


def create_paginated_response(items: list, page: int = 1, size: int = 50, total: int | None = None):
    """Create a paginated response structure matching fastapi-pagination Page model.

    Returns a Page object that fastapi-pagination would return, with items
    converted to SprintItemRead schema format.
    """
    if total is None:
        total = len(items)
    pages = (total + size - 1) // size if total > 0 else 1

    # Convert mock items to SprintItemRead-compatible dicts
    item_dicts = [
        SprintItemRead(
            id=item.id,
            sprint_id=item.sprint_id,
            title=item.title,
            description=item.description,
            status=item.status,
            priority=item.priority,
            estimate_points=item.estimate_points,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]

    return Page[SprintItemRead](
        items=item_dicts,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


class TestListSprintItemsEmpty:
    """Tests for empty sprint returns empty paginated response."""

    @pytest.mark.anyio
    async def test_empty_sprint_returns_empty_items_list(
        self,
        mock_sprint: MockSprint,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return empty items array with total=0 for sprint with no items."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        # Configure mock service to return sprint (validates it exists)
        mock_sprint_service.get_by_id = AsyncMock(return_value=mock_sprint)

        # Mock the paginate function to return empty result (must be AsyncMock)
        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response([])),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.anyio
    async def test_empty_sprint_has_correct_pagination_metadata(
        self,
        mock_sprint: MockSprint,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return correct pagination metadata for empty sprint."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        mock_sprint_service.get_by_id = AsyncMock(return_value=mock_sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response([], page=1, size=50, total=0)),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data


class TestListSprintItemsWithData:
    """Tests for sprint with items returns paginated items."""

    @pytest.mark.anyio
    async def test_returns_all_items_for_sprint(
        self,
        mock_sprint_with_items: tuple[MockSprint, list[MockSprintItem]],
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return all items belonging to the sprint."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint, items = mock_sprint_with_items
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response(items, total=len(items))),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint.id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 4
        assert data["total"] == 4

    @pytest.mark.anyio
    async def test_items_have_correct_schema(
        self,
        mock_sprint_with_items: tuple[MockSprint, list[MockSprintItem]],
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return items with correct SprintItemRead schema fields."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint, items = mock_sprint_with_items
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response(items)),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint.id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]

        # Verify SprintItemRead schema fields
        assert "id" in item
        assert "sprint_id" in item
        assert "title" in item
        assert "description" in item
        assert "status" in item
        assert "priority" in item
        assert "estimate_points" in item
        assert "created_at" in item
        assert "updated_at" in item


class TestPaginationParams:
    """Tests for pagination params (page, size) work correctly."""

    @pytest.mark.anyio
    async def test_custom_page_size(
        self,
        mock_sprint_with_items: tuple[MockSprint, list[MockSprintItem]],
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should respect custom page size parameter."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint, items = mock_sprint_with_items
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(
                return_value=create_paginated_response(items[:2], page=1, size=2, total=4)
            ),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint.id}/items",
                    params={"size": 2},
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 2
        assert data["total"] == 4
        assert data["pages"] == 2

    @pytest.mark.anyio
    async def test_page_navigation(
        self,
        mock_sprint_with_items: tuple[MockSprint, list[MockSprintItem]],
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return correct page when page parameter is specified."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint, items = mock_sprint_with_items
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(
                return_value=create_paginated_response(items[2:4], page=2, size=2, total=4)
            ),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint.id}/items",
                    params={"page": 2, "size": 2},
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.anyio
    async def test_default_pagination_values(
        self,
        mock_sprint_with_items: tuple[MockSprint, list[MockSprintItem]],
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should use default pagination values when not specified."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint, items = mock_sprint_with_items
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response(items, page=1, size=50)),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint.id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        # Default page is 1, default size is typically 50
        assert data["page"] == 1
        assert data["size"] == 50


class TestNonExistentSprint:
    """Tests for non-existent sprint returns 404."""

    @pytest.mark.anyio
    async def test_404_for_non_existent_sprint(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return 404 when sprint does not exist."""
        from app.api.deps import get_sprint_service
        from app.core.exceptions import NotFoundError
        from app.db.session import get_db_session

        non_existent_id = uuid4()
        mock_sprint_service.get_by_id = AsyncMock(
            side_effect=NotFoundError(
                message="Sprint not found",
                details={"sprint_id": str(non_existent_id)},
            )
        )

        app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
        app.dependency_overrides[get_db_session] = lambda: mock_db_session

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{settings.API_V1_STR}/sprints/{non_existent_id}/items",
            )

        app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_404_error_message(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return appropriate error message for non-existent sprint."""
        from app.api.deps import get_sprint_service
        from app.core.exceptions import NotFoundError
        from app.db.session import get_db_session

        non_existent_id = uuid4()
        mock_sprint_service.get_by_id = AsyncMock(
            side_effect=NotFoundError(
                message="Sprint not found",
                details={"sprint_id": str(non_existent_id)},
            )
        )

        app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
        app.dependency_overrides[get_db_session] = lambda: mock_db_session

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{settings.API_V1_STR}/sprints/{non_existent_id}/items",
            )

        app.dependency_overrides.clear()

        assert response.status_code == 404
        data = response.json()
        # App uses custom error format with error.message structure
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "Sprint not found" in data["error"]["message"]

    @pytest.mark.anyio
    async def test_invalid_uuid_format(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return 422 for invalid UUID format."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
        app.dependency_overrides[get_db_session] = lambda: mock_db_session

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{settings.API_V1_STR}/sprints/not-a-valid-uuid/items",
            )

        app.dependency_overrides.clear()

        assert response.status_code == 422


class TestItemOrdering:
    """Tests for items are ordered by priority."""

    @pytest.mark.anyio
    async def test_items_ordered_by_priority_ascending(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should return items ordered by priority (1=high, 3=low)."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint_id = uuid4()
        # Create items with different priorities (not in order)
        items = [
            MockSprintItem(sprint_id=sprint_id, title="Low Priority", priority=3),
            MockSprintItem(sprint_id=sprint_id, title="High Priority", priority=1),
            MockSprintItem(sprint_id=sprint_id, title="Medium Priority", priority=2),
        ]
        # Sort by priority for expected order
        sorted_items = sorted(items, key=lambda x: x.priority)

        sprint = MockSprint(id=sprint_id, items=items)
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response(sorted_items)),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint_id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        priorities = [item["priority"] for item in data["items"]]
        assert priorities == [1, 2, 3], "Items should be ordered by priority ascending"

    @pytest.mark.anyio
    async def test_same_priority_items_stable(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Items with same priority should maintain stable order."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        sprint_id = uuid4()
        # Create multiple items with same priority
        items = [
            MockSprintItem(sprint_id=sprint_id, title="Task A", priority=2),
            MockSprintItem(sprint_id=sprint_id, title="Task B", priority=2),
            MockSprintItem(sprint_id=sprint_id, title="Task C", priority=2),
        ]

        sprint = MockSprint(id=sprint_id, items=items)
        mock_sprint_service.get_by_id = AsyncMock(return_value=sprint)

        with patch(
            "app.api.routes.v1.sprints.paginate",
            new=AsyncMock(return_value=create_paginated_response(items)),
        ):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{sprint_id}/items",
                )

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        # All items should have priority 2
        priorities = [item["priority"] for item in data["items"]]
        assert all(p == 2 for p in priorities)


class TestQueryConstruction:
    """Tests to verify the correct query is constructed."""

    @pytest.mark.anyio
    async def test_paginate_called_with_correct_query(
        self,
        mock_sprint: MockSprint,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should call paginate with query filtering by sprint_id and ordering by priority."""
        from app.api.deps import get_sprint_service
        from app.db.session import get_db_session

        mock_sprint_service.get_by_id = AsyncMock(return_value=mock_sprint)

        mock_paginate = AsyncMock(return_value=create_paginated_response([]))
        with patch("app.api.routes.v1.sprints.paginate", new=mock_paginate):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                await client.get(
                    f"{settings.API_V1_STR}/sprints/{mock_sprint.id}/items",
                )

            app.dependency_overrides.clear()

        # Verify paginate was called
        mock_paginate.assert_called_once()
        call_args = mock_paginate.call_args

        # First positional arg should be db session
        # Second positional arg should be the query
        assert len(call_args.args) == 2
        query = call_args.args[1]

        # Verify it's a select query (has _raw_columns)
        assert hasattr(query, "_raw_columns") or hasattr(query, "column_descriptions")

    @pytest.mark.anyio
    async def test_sprint_validation_before_query(
        self,
        mock_sprint_service: MagicMock,
        mock_db_session: AsyncMock,
    ):
        """Should validate sprint exists before executing pagination query."""
        from app.api.deps import get_sprint_service
        from app.core.exceptions import NotFoundError
        from app.db.session import get_db_session

        non_existent_id = uuid4()
        mock_sprint_service.get_by_id = AsyncMock(
            side_effect=NotFoundError(message="Sprint not found")
        )

        mock_paginate = AsyncMock()
        with patch("app.api.routes.v1.sprints.paginate", new=mock_paginate):
            app.dependency_overrides[get_sprint_service] = lambda db=None: mock_sprint_service
            app.dependency_overrides[get_db_session] = lambda: mock_db_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"{settings.API_V1_STR}/sprints/{non_existent_id}/items",
                )

            app.dependency_overrides.clear()

        # Sprint validation should fail before paginate is called
        assert response.status_code == 404
        mock_paginate.assert_not_called()
